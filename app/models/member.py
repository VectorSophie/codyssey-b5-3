from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Member(Base):
    """로그인 계정 + 대여 서비스 이용자를 겸하는 모델(이 앱 규모에서는 둘을 분리할 이유가 없다)."""

    __tablename__ = "members"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(50), nullable=False)

    # 회원이 삭제되어도 "누가 언제 무엇을 빌렸는지"는 감사 기록으로 남아야 하므로
    # cascade를 걸지 않는다(회원 삭제 기능 자체도 이 앱엔 없다).
    rentals = relationship("Rental", back_populates="member")

    def __repr__(self) -> str:
        return f"<Member id={self.id} username={self.username!r}>"
