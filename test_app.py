"""자가 점검 스크립트: python test_app.py 로 실행 (pytest 불필요).

로그인 실패/성공, 보호 라우트 접근 차단/허용, 대여->반납 상태 변경 흐름,
플래시 메시지, CSRF 토큰 검증, cascade 삭제를 검증한다.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["SESSION_SECRET_KEY"] = "test-secret"

TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_database.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

# main.py를 import하기 전에 엔진을 테스트 전용 DB로 바꿔치기한다.
import app.database as database  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

database.engine = create_engine(f"sqlite:///{TEST_DB}", connect_args={"check_same_thread": False})
database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.models.book import Book  # noqa: E402
from app.models.rental import Rental  # noqa: E402

client = TestClient(app)


def extract_csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "csrf_token hidden input을 찾을 수 없음"
    return match.group(1)


def test_flow():
    # 1) 보호 라우트는 비로그인 상태에서 로그인 페이지로 리다이렉트된다.
    resp = client.get("/books", follow_redirects=False)
    assert resp.status_code == 303, resp.status_code
    assert resp.headers["location"] == "/login"

    # 1-1) 리다이렉트 사유가 플래시 메시지로 로그인 화면에 1회 표시된다.
    resp = client.get("/login")
    assert "로그인이 필요한 기능입니다" in resp.text
    resp = client.get("/login")
    assert "로그인이 필요한 기능입니다" not in resp.text, "플래시는 한 번 읽으면 사라져야 한다"

    # 2) 잘못된 비밀번호는 로그인 실패(401)
    resp = client.post("/login", data={"username": "tester", "password": "wrong"})
    assert resp.status_code == 401, resp.status_code

    # 3) 올바른 계정으로 로그인 성공 -> /books로 리다이렉트
    resp = client.post(
        "/login", data={"username": "tester", "password": "test1234"}, follow_redirects=False
    )
    assert resp.status_code == 303, resp.status_code
    assert resp.headers["location"] == "/books"

    # 4) 로그인 후에는 보호 라우트에 접근 가능
    resp = client.get("/books")
    assert resp.status_code == 200
    assert "채식주의자" in resp.text

    # 4-1) 도서 상세 화면 폼에서 CSRF 토큰을 꺼낸다(세션당 하나, 모든 폼이 공유).
    resp = client.get("/books/1")
    csrf_token = extract_csrf(resp.text)

    # 4-2) 잘못된 CSRF 토큰으로는 상태 변경 요청이 거부된다(403) — CSRF 방어 검증.
    resp = client.post("/books/1/rent", data={"csrf_token": "invalid-token"})
    assert resp.status_code == 403, resp.status_code

    # 5) 올바른 토큰으로 대여 -> 목록에서 "대여중" 상태 확인
    resp = client.post("/books/1/rent", data={"csrf_token": csrf_token}, follow_redirects=False)
    assert resp.status_code == 303, resp.status_code
    resp = client.get("/rentals")
    assert "대여중" in resp.text

    # 6) 반납 -> 상태가 반납완료로 바뀐다 (상태 변경 비즈니스 로직 검증)
    resp = client.post(
        "/rentals/1/return", data={"csrf_token": csrf_token}, follow_redirects=False
    )
    assert resp.status_code == 303, resp.status_code
    resp = client.get("/rentals")
    assert "반납완료" in resp.text

    # 7) 로그아웃 후 다시 보호됨
    client.post("/logout", data={"csrf_token": csrf_token})
    resp = client.get("/books", follow_redirects=False)
    assert resp.status_code == 303, resp.status_code

    print("OK: all self-checks passed")


def test_cascade_delete():
    """책이 삭제되면 그 책에 딸린 Rental도 cascade="all, delete-orphan"으로 함께 삭제된다."""
    db = database.SessionLocal()
    try:
        book = Book(title="테스트용 임시 도서", author="테스터", total_copies=1, available_copies=1)
        db.add(book)
        db.commit()
        db.refresh(book)

        rental = Rental(member_id=1, book_id=book.id, status="대여중")
        db.add(rental)
        db.commit()

        db.delete(book)
        db.commit()

        remaining = db.query(Rental).filter(Rental.book_id == book.id).count()
        assert remaining == 0, "책 삭제 시 딸린 Rental도 함께 삭제되어야 한다(cascade 확인)"
        print("OK: cascade delete 검증 통과")
    finally:
        db.close()


if __name__ == "__main__":
    try:
        test_flow()
        test_cascade_delete()
    finally:
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
