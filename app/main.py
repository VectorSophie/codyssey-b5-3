import os

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth.dependencies import NotAuthenticated, hash_password
from app.database import Base, SessionLocal, engine
from app.errors import DomainNotFound
from app.models import Book, Member
from app.routers import books, pages, rentals

# ponytail: 데모용 기본값. 실서비스라면 반드시 환경변수로만 주입해야 한다.
SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "dev-secret-change-in-production")

app = FastAPI(title="도서 대여 서비스")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

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
    """require_login이 던진 예외를 잡아 로그인 페이지로 보낸다 (인가 실패 처리 지점)."""
    return RedirectResponse(url="/login", status_code=303)


@app.exception_handler(DomainNotFound)
async def handle_not_found(request: Request, exc: DomainNotFound):
    return templates.TemplateResponse(
        "error.html", {"request": request, "message": str(exc)}, status_code=404
    )
