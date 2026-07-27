class DomainNotFound(Exception):
    """요청한 도메인 데이터(도서/대여 기록 등)를 찾을 수 없을 때 발생시킨다."""
