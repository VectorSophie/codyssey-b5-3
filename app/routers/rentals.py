from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import get_or_create_csrf_token, require_login, verify_csrf
from app.database import get_db
from app.models.member import Member
from app.repositories import rental_repository
from app.services import rental_service

router = APIRouter(prefix="/rentals")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["csrf_token"] = get_or_create_csrf_token


@router.get("")
def my_rentals(
    request: Request,
    db: Session = Depends(get_db),
    current_member: Member = Depends(require_login),
):
    """member.rentals(연관관계)가 아니라 별도 조회를 쓰는 이유는 최신순 정렬이 필요해서다."""
    rentals = rental_repository.get_by_member(db, current_member.id)
    return templates.TemplateResponse(
        "my_rentals.html", {"request": request, "rentals": rentals, "member": current_member}
    )


@router.post("/{rental_id}/return", dependencies=[Depends(verify_csrf)])
def return_rental(
    rental_id: int,
    db: Session = Depends(get_db),
    current_member: Member = Depends(require_login),
):
    """상태 변경 액션: 대여중 -> 반납완료."""
    rental_service.return_book(db, current_member, rental_id)
    return RedirectResponse(url="/rentals", status_code=303)
