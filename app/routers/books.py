from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import require_login
from app.database import get_db
from app.models.member import Member
from app.repositories import book_repository
from app.services import rental_service

router = APIRouter(prefix="/books")
templates = Jinja2Templates(directory="app/templates")


@router.get("")
def list_books(
    request: Request,
    db: Session = Depends(get_db),
    current_member: Member = Depends(require_login),
):
    """보호 라우트. require_login을 통과하지 못하면 여기 도달하지 않는다."""
    books = book_repository.get_all(db)
    return templates.TemplateResponse(
        "books_list.html", {"request": request, "books": books, "member": current_member}
    )


@router.get("/{book_id}")
def book_detail(
    book_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_member: Member = Depends(require_login),
):
    book = book_repository.get_or_404(db, book_id)
    return templates.TemplateResponse(
        "book_detail.html", {"request": request, "book": book, "member": current_member, "error": None}
    )


@router.post("/{book_id}/rent")
def rent(
    book_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_member: Member = Depends(require_login),
):
    """상태 변경 액션: 재고 있음(대여 가능) -> 대여중. 재고 없으면 에러를 detail 화면에 표시한다."""
    try:
        rental_service.rent_book(db, current_member, book_id)
    except ValueError as exc:
        book = book_repository.get_or_404(db, book_id)
        return templates.TemplateResponse(
            "book_detail.html",
            {"request": request, "book": book, "member": current_member, "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse(url="/rentals", status_code=303)
