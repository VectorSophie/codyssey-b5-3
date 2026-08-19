import os
import warnings

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth.dependencies import CSRFError, NotAuthenticated, hash_password
from app.database import Base, SessionLocal, engine
from app.errors import DomainNotFound
from app.models import Book, Member
from app.routers import books, pages, rentals

# ponytail: 데모용 기본값. 실서비스라면 반드시 환경변수로만 주입해야 한다.
DEFAULT_SECRET_KEY = "dev-secret-change-in-production"
SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", DEFAULT_SECRET_KEY)
if SECRET_KEY == DEFAULT_SECRET_KEY:
    warnings.warn(
        "SESSION_SECRET_KEY가 설정되지 않아 데모용 기본값을 쓰고 있습니다. "
        "배포 환경에서는 반드시 환경변수로 별도 값을 지정하세요(세션 쿠키 위조 방지).",
        RuntimeWarning,
        stacklevel=1,
    )

app = FastAPI(title="도서 대여 서비스")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=int(os.environ.get("SESSION_MAX_AGE", 60 * 60 * 2)),  # 기본 2시간 후 만료
    https_only=os.environ.get("SESSION_HTTPS_ONLY", "false").lower() == "true",
    same_site="lax",
)

Base.metadata.create_all(bind=engine)


def seed() -> None:
    """최초 실행 시 테스트 계정과 샘플 도서를 채워 넣는다(이미 있으면 건너뜀)."""
    db = SessionLocal()
    try:
        if db.query(Member).count() == 0:
            db.add(Member(username="tester", password_hash=hash_password("test1234"), name="테스터"))
        if db.query(Book).count() == 0:
            db.add_all(
                [
                    Book(title="채식주의자", author="한강", total_copies=3, available_copies=3),
                    Book(title="어린 왕자", author="생텍쥐페리", total_copies=2, available_copies=2),
                    Book(title="1984", author="조지 오웰", total_copies=1, available_copies=1),
                ]
            )
        db.commit()
    finally:
        db.close()


seed()

app.include_router(pages.router)
app.include_router(books.router)
app.include_router(rentals.router)

templates = Jinja2Templates(directory="app/templates")


@app.exception_handler(NotAuthenticated)
async def handle_not_authenticated(request: Request, exc: NotAuthenticated):
    """require_login이 던진 예외를 잡아 로그인 페이지로 보낸다 (인가 실패 처리 지점).

    리다이렉트 사유를 세션에 1회성 플래시 메시지로 실어 보내고,
    로그인 화면(pages.login_form)이 이를 꺼내 보여준 뒤 지운다.
    """
    request.session["flash"] = "로그인이 필요한 기능입니다."
    return RedirectResponse(url="/login", status_code=303)


@app.exception_handler(DomainNotFound)
async def handle_not_found(request: Request, exc: DomainNotFound):
    return templates.TemplateResponse(
        "error.html", {"request": request, "message": str(exc)}, status_code=404
    )


@app.exception_handler(CSRFError)
async def handle_csrf_error(request: Request, exc: CSRFError):
    """verify_csrf가 던진 예외를 잡아 403으로 응답한다."""
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "message": "요청이 유효하지 않습니다. 새로고침 후 다시 시도해주세요."},
        status_code=403,
    )
