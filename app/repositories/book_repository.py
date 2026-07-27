from sqlalchemy.orm import Session

from app.errors import DomainNotFound
from app.models.book import Book


def get_all(db: Session):
    return db.query(Book).order_by(Book.id).all()


def get_or_404(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise DomainNotFound(f"도서(id={book_id})를 찾을 수 없습니다.")
    return book
