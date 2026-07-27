from typing import Optional

from fastapi import Depends, Request
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.member import Member

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class NotAuthenticated(Exception):
    """로그인하지 않은 사용자가 보호된 경로에 접근했을 때 발생시킨다."""


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
