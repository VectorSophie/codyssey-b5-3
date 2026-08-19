from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Book(Base):
    """대여 대상 도서 한 종. `available_copies`는 대여/반납 때마다 증감하는 재고 수량이다."""

    __tablename__ = "books"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100), nullable=False)
    total_copies = Column(Integer, nullable=False, default=1)
    available_copies = Column(Integer, nullable=False, default=1)

    # 책 레코드가 삭제되면 그 책에 딸린 대여 기록은 더 이상 의미가 없으므로
    # (부모 없는 대여 기록이 남는 것을 막기 위해) 함께 삭제한다.
    rentals = relationship("Rental", back_populates="book", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Book id={self.id} title={self.title!r} available={self.available_copies}/{self.total_copies}>"
