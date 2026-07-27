from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100), nullable=False)
    total_copies = Column(Integer, nullable=False, default=1)
    available_copies = Column(Integer, nullable=False, default=1)

    # 책 레코드가 삭제되면 그 책에 딸린 대여 기록은 더 이상 의미가 없으므로
    # (부모 없는 대여 기록이 남는 것을 막기 위해) 함께 삭제한다.
    rentals = relationship("Rental", back_populates="book", cascade="all, delete-orphan")
