# b5-3 도서 대여 서비스 — 인증/인가 + 연관관계 확장

FastAPI + SQLAlchemy + Jinja2 SSR 기반 도서 대여 서비스. b5-2(단일 모델 CRUD)를 확장해
로그인/로그아웃(세션 기반 인증), 보호 라우트, 3개 모델의 연관관계, 상태가 바뀌는
핵심 비즈니스 로직(대여 → 반납)을 통합했다.

## 개발 환경

| 항목 | 버전 |
|---|---|
| Python | 3.12 (요구사항: 3.10 이상) |
| fastapi | 0.115.6 |
| uvicorn | 0.32.1 |
| sqlalchemy | 2.0.36 |
| jinja2 | 3.1.4 |
| python-multipart | 0.0.19 |
| itsdangerous | 2.2.0 |
| passlib | 1.7.4 |
| bcrypt | 4.0.1 |

## 실행 방법

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

`http://localhost:8000` 접속. 최초 실행 시 테스트 계정 1명과 샘플 도서 3권이 자동으로 채워진다
(`app/main.py`의 `seed()`). DB 파일은 프로젝트 루트의 `database.db` (SQLite).

## 테스트 계정

| 항목 | 값 |
|---|---|
| 아이디 | `tester` |
| 비밀번호 | `test1234` |
| 저장 방식 | DB 저장 (`members` 테이블, bcrypt 해시) |

로그인 화면과 도메인의 "회원"을 분리하지 않고 `Member` 모델 하나로 겸했다 — 이 규모의
앱에서 인증 계정과 도메인 회원을 별도 테이블로 나눌 이유가 없어서다.

## 공개/보호 경로 정책

| 경로 | 구분 | 설명 |
|---|---|---|
| `GET /` | 공개 | 홈. 로그인 여부에 따라 문구/링크만 달라짐 |
| `GET /login`, `POST /login` | 공개 | 로그인 폼 및 처리 |
| `POST /logout` | 공개 | 로그아웃(세션 초기화) |
| `GET /books` | **보호** | 도서 목록 |
| `GET /books/{id}` | **보호** | 도서 상세 |
| `POST /books/{id}/rent` | **보호** | 대여(상태 변경) |
| `GET /rentals` | **보호** | 내 대여 목록 |
| `POST /rentals/{id}/return` | **보호** | 반납(상태 변경) |

보호 라우트는 `Depends(require_login)`을 의존성으로 걸어 표시한다(`app/auth/dependencies.py`).
비로그인 상태로 보호 라우트에 접근하면 `NotAuthenticated` 예외가 발생하고, `app/main.py`에
등록된 전역 예외 핸들러가 `303 See Other`로 `/login`으로 리다이렉트한다.

## 주요 기능 경로

| 기능 | 경로 |
|---|---|
| 도서 목록/재고 확인 | `GET /books` |
| 도서 상세 + 대여하기 | `GET /books/{id}`, `POST /books/{id}/rent` |
| 내 대여 목록 + 반납하기 | `GET /rentals`, `POST /rentals/{id}/return` |

## 인증 방식 선택 사유

**방식 A(세션 기반)** 선택. `starlette.middleware.sessions.SessionMiddleware`가 로그인 성공 시
`request.session["member_id"]`를 서명된(itsdangerous) 쿠키에 저장하고, 이후 요청마다
`get_current_member` 의존성이 이를 읽어 DB에서 회원을 조회한다. JWT는 토큰 재발급/만료/저장 위치
(localStorage vs 쿠키) 등 신경 쓸 게 늘어나는데, 이 앱은 SSR 단일 서버 구조라 서버가 세션 상태를
직접 들고 있는 편이 훨씬 단순하고 정확하다 — SPA/모바일 클라이언트가 따로 붙는 구조가 아니면
JWT를 쓸 이유가 없다.

## 폴더 구조

```
app/
├── main.py                  # 앱 조립: 미들웨어, 라우터 등록, 전역 예외 핸들러, seed
├── database.py               # engine / SessionLocal / get_db
├── errors.py                  # DomainNotFound (404 처리용)
├── models/                    # SQLAlchemy ORM 모델 (Member, Book, Rental)
├── auth/dependencies.py      # 인증/인가: get_current_member, require_login
├── repositories/               # DB 접근 (책/대여/회원)
├── services/                   # 비즈니스 로직 (로그인 인증, 대여/반납)
├── routers/                    # 요청/응답 (pages, books, rentals)
└── templates/                  # Jinja2 템플릿
```

## 도메인 모델 및 연관관계

- `Member` 1 : N `Rental` (양방향, `back_populates`)
- `Book` 1 : N `Rental` (양방향, `back_populates`)
- `Rental.status`: `대여중` → `반납완료` (상태 변경 비즈니스 로직의 핵심)

cascade 정책: `Book.rentals`는 `cascade="all, delete-orphan"` — 책 레코드가 삭제되면 그 책에 대한
대여 기록도 의미가 없으므로 함께 삭제한다. 반면 `Member.rentals`는 cascade를 걸지 않았다 — 회원이
삭제되어도 "누가 언제 무엇을 빌렸는지"는 감사 기록으로 남아야 한다는 판단이다(이유는
`app/models/member.py`, `app/models/book.py`에 주석으로도 남겨두었다).

## 상태 변경 비즈니스 기능

"대여하기"를 누르면 `Rental`이 `대여중` 상태로 생성되면서 동시에 `Book.available_copies`가 1
줄어든다. "반납하기"를 누르면 `Rental.status`가 `반납완료`로 바뀌고 `Book.available_copies`가
다시 1 늘어난다. 두 테이블의 상태가 한 트랜잭션으로 같이 바뀌어야 하므로 라우터가 아니라
`app/services/rental_service.py`에 로직을 두었다.

## 자가 점검

```bash
source .venv/bin/activate
python test_app.py
```

`fastapi.testclient.TestClient`로 (1) 비로그인 시 보호 라우트 → `/login` 리다이렉트,
(2) 잘못된 비밀번호 로그인 실패, (3) 로그인 성공, (4) 로그인 후 보호 라우트 접근 성공,
(5) 대여 → `대여중` 상태 확인, (6) 반납 → `반납완료` 상태 확인, (7) 로그아웃 후 재차 보호됨을
검증한다.
