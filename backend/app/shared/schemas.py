from typing import Any, Generic, Literal, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    message: str = "OK"


class Insight(BaseModel):
    type: str = Field(..., description="Insight category: growth, warning, trend, segment")
    title: str = Field(..., description="Short headline")
    detail: str = Field(..., description="Explanation with data")
    severity: Literal["positive", "warning", "neutral", "critical"] = Field(
        ..., description="positive, warning, neutral, critical"
    )


class PaginationMeta(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)
    total_items: int = 0
    total_pages: int = 0


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T] = []
    pagination: PaginationMeta = PaginationMeta()
    message: str = "OK"


class KPICard(BaseModel):
    label: str
    value: float
    formatted: str
    change_pct: float | None = None
    trend: str = "neutral"


class FilterOptions(BaseModel):
    categories: list[str] = []
    states: list[str] = []
    months: list[str] = []
