from typing import Optional

from sqlalchemy.orm import Session

from app.auth.dependencies import verify_password
from app.models.member import Member
from app.repositories import member_repository


def authenticate(db: Session, username: str, password: str) -> Optional[Member]:
    """아이디/비밀번호가 맞으면 Member를, 아니면 None을 반환한다."""
    member = member_repository.get_by_username(db, username)
    if member is None or not verify_password(password, member.password_hash):
        return None
    return member
