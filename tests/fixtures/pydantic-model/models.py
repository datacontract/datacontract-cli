import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Status(str, Enum):
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class Address(BaseModel):
    """A postal address."""

    street: str
    city: str
    postal_code: Optional[str] = None


class LineItem(BaseModel):
    sku: str = Field(description="Stock keeping unit.", max_length=32)
    quantity: Annotated[int, Field(ge=1)]


class Orders(BaseModel):
    """One row per customer order."""

    order_id: UUID
    order_timestamp: datetime.datetime
    order_date: datetime.date
    customer_id: str = Field(min_length=1, max_length=64)
    order_total: Decimal = Field(ge=0)
    status: Status
    channel: Literal["web", "mobile", "store"]
    priority: Literal[1, 2, 3]
    shipping_address: Address
    line_items: list[LineItem]
    tags: list[str] = []
    attributes: dict[str, str] = {}
    note: str | None = None
    is_gift: bool = False
    payload: bytes
