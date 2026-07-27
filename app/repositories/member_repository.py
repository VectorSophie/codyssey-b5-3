from sqlalchemy.orm import Session

from app.models.member import Member


def get_by_username(db: Session, username: str):
    return db.query(Member).filter(Member.username == username).first()
