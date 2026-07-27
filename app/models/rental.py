from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base

STATUS_RENTED = "대여중"
STATUS_RETURNED = "반납완료"


class Rental(Base):
    """대여 1건 = 회원(N:1) + 도서(N:1)를 잇는 관계 모델이자 상태(대여중/반납완료)를 갖는다."""

    __tablename__ = "rentals"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    status = Column(String(20), nullable=False, default=STATUS_RENTED)
    rented_at = Column(DateTime, default=datetime.utcnow)
    returned_at = Column(DateTime, nullable=True)

    member = relationship("Member", back_populates="rentals")
    book = relationship("Book", back_populates="rentals")
