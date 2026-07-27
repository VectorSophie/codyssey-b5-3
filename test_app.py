"""자가 점검 스크립트: python test_app.py 로 실행 (pytest 불필요).

로그인 실패/성공, 보호 라우트 접근 차단/허용, 대여->반납 상태 변경 흐름을 검증한다.
"""
import os
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

client = TestClient(app)


def test_flow():
    # 1) 보호 라우트는 비로그인 상태에서 로그인 페이지로 리다이렉트된다.
    resp = client.get("/books", follow_redirects=False)
    assert resp.status_code == 303, resp.status_code
    assert resp.headers["location"] == "/login"

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

    # 5) 대여 -> 목록에서 "대여중" 상태 확인
    resp = client.post("/books/1/rent", follow_redirects=False)
    assert resp.status_code == 303, resp.status_code
    resp = client.get("/rentals")
    assert "대여중" in resp.text

    # 6) 반납 -> 상태가 반납완료로 바뀐다 (상태 변경 비즈니스 로직 검증)
    resp = client.post("/rentals/1/return", follow_redirects=False)
    assert resp.status_code == 303, resp.status_code
    resp = client.get("/rentals")
    assert "반납완료" in resp.text

    # 7) 로그아웃 후 다시 보호됨
    client.post("/logout")
    resp = client.get("/books", follow_redirects=False)
    assert resp.status_code == 303, resp.status_code

    print("OK: all self-checks passed")


if __name__ == "__main__":
    try:
        test_flow()
    finally:
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
