from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_member, get_or_create_csrf_token, verify_csrf
from app.database import get_db
from app.models.member import Member
from app.services.auth_service import authenticate

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["csrf_token"] = get_or_create_csrf_token


@router.get("/")
def home(request: Request, current_member: Optional[Member] = Depends(get_current_member)):
    """공개 페이지. 로그인 여부에 따라 안내 문구/링크가 달라진다."""
    return templates.TemplateResponse("home.html", {"request": request, "member": current_member})


@router.get("/login")
def login_form(request: Request):
    """require_login이 세션에 남긴 1회성 플래시 메시지를 꺼내 보여주고 즉시 지운다."""
    flash = request.session.pop("flash", None)
    return templates.TemplateResponse("login.html", {"request": request, "error": flash})


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    member = authenticate(db, username, password)
    if member is None:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "아이디 또는 비밀번호가 올바르지 않습니다."},
            status_code=401,
        )
    request.session["member_id"] = member.id
    return RedirectResponse(url="/books", status_code=303)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)
