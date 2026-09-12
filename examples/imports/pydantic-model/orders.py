import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Status(str, Enum):
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class Orders(BaseModel):
    """One row per customer order."""

    order_id: str = Field(max_length=32)
    order_timestamp: datetime.datetime
    customer_id: Optional[str] = None
    order_total: int = Field(description="Order total in cents.", ge=0)
    status: Status
