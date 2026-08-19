from typing import List

from sqlalchemy.orm import Session

from app.errors import DomainNotFound
from app.models.rental import Rental


def get_by_member(db: Session, member_id: int) -> List[Rental]:
    return db.query(Rental).filter(Rental.member_id == member_id).order_by(Rental.id.desc()).all()


def get_or_404(db: Session, rental_id: int) -> Rental:
    rental = db.get(Rental, rental_id)
    if rental is None:
        raise DomainNotFound(f"대여 기록(id={rental_id})을 찾을 수 없습니다.")
    return rental
