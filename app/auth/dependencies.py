import secrets
from typing import Optional

from fastapi import Depends, Form, Request
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.member import Member

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class NotAuthenticated(Exception):
    """로그인하지 않은 사용자가 보호된 경로에 접근했을 때 발생시킨다."""


class CSRFError(Exception):
    """폼에 실린 csrf_token이 없거나 세션의 값과 일치하지 않을 때 발생시킨다."""


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_current_member(request: Request, db: Session = Depends(get_db)) -> Optional[Member]:
    """세션 쿠키(request.session)에 저장된 member_id로 로그인 사용자를 조회한다. 없으면 None."""
    member_id = request.session.get("member_id")
    if member_id is None:
        return None
    return db.get(Member, member_id)


def require_login(current_member: Optional[Member] = Depends(get_current_member)) -> Member:
    """보호 라우터의 의존성으로 사용한다.

    비로그인 상태면 NotAuthenticated를 발생시키고, main.py에 등록된
    전역 예외 핸들러가 이를 잡아 /login으로 리다이렉트한다.
    라우터 함수 본문은 "이미 로그인된 사용자"만 신경 쓰면 되므로
    인가 로직이 라우터 코드에서 완전히 분리된다.
    """
    if current_member is None:
        raise NotAuthenticated()
    return current_member


def get_or_create_csrf_token(request: Request) -> str:
    """세션에 CSRF 토큰이 없으면 새로 만들어 저장하고, 있으면 그대로 재사용한다.

    Jinja 템플릿 전역 함수로 등록해 폼 렌더링 시 `{{ csrf_token(request) }}`로 쓴다
    (synchronizer token pattern).
    """
    token = request.session.get("csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def verify_csrf(request: Request, csrf_token: str = Form(...)) -> None:
    """상태를 변경하는 POST 라우트(rent/return/logout)에 Depends로 건다.

    세션 쿠키만으로 요청을 신뢰하면 CSRF에 노출되므로, 폼에 실려온 토큰이 세션에 저장된
    값과 일치하는지 확인한다. 일치하지 않으면(다른 사이트에서 자동 제출된 폼 등) CSRFError.
    """
    expected = request.session.get("csrf_token")
    if not expected or not secrets.compare_digest(csrf_token, expected):
        raise CSRFError()
