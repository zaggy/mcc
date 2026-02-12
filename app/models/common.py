from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    pages: int
