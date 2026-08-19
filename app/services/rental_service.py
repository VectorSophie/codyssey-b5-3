from datetime import datetime

from sqlalchemy.orm import Session

from app.errors import DomainNotFound
from app.models.member import Member
from app.models.rental import STATUS_RENTED, STATUS_RETURNED, Rental
from app.repositories import book_repository, rental_repository


def rent_book(db: Session, member: Member, book_id: int) -> Rental:
    """도서 대여: 재고 확인 -> 대여 기록 생성 -> 재고 차감을 한 트랜잭션으로 묶은
    상태 변경 비즈니스 로직. 단순 INSERT가 아니라 Book.available_copies라는
    다른 테이블의 상태까지 같이 바뀌므로 라우터가 아니라 서비스 계층에 둔다.
    """
    book = book_repository.get_or_404(db, book_id)
    if book.available_copies <= 0:
        raise ValueError("대여 가능한 재고가 없습니다.")

    rental = Rental(member_id=member.id, book_id=book.id, status=STATUS_RENTED)
    book.available_copies -= 1
    db.add(rental)
    try:
        db.commit()
    except Exception:
        # commit 실패(예: DB 제약 위반) 시 세션에 남은 변경사항을 명시적으로 되돌린다.
        db.rollback()
        raise
    db.refresh(rental)
    return rental


def return_book(db: Session, member: Member, rental_id: int) -> Rental:
    """도서 반납: 본인 소유의 대여 기록인지 확인 후 상태를 반납완료로 바꾸고
    재고를 되돌린다. 이미 반납된 기록이면 그대로 반환한다(멱등)."""
    rental = rental_repository.get_or_404(db, rental_id)
    if rental.member_id != member.id:
        # 다른 사람의 대여 기록은 존재 자체를 숨긴다(정보 노출 방지).
        raise DomainNotFound(f"대여 기록(id={rental_id})을 찾을 수 없습니다.")
    if rental.status == STATUS_RETURNED:
        return rental

    rental.status = STATUS_RETURNED
    rental.returned_at = datetime.utcnow()
    rental.book.available_copies += 1
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(rental)
    return rental
