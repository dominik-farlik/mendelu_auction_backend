import enum
from datetime import datetime, UTC
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Integer, Float, ForeignKey, DateTime, Enum, String
from sqlalchemy.orm import relationship, mapped_column, Mapped

from models.base import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PROCESSING = "processing"
    
class DeliveryMethod(str, enum.Enum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


class Order(Base):
    __tablename__ = "order"

    id = mapped_column(Integer, primary_key=True, index=True)
    product_id = mapped_column(Integer, ForeignKey("product.id"), nullable=False)
    buyer_id = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    amount = mapped_column(Float, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(String(20), default=OrderStatus.PENDING, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_method: Mapped[Optional[DeliveryMethod]] = mapped_column(String(20), default=DeliveryMethod.PICKUP, nullable=True)
    shipping_address = mapped_column(String(255), nullable=True)

    product = relationship("Product", back_populates="orders")
    buyer = relationship("User", back_populates="wins")


class ConfirmOrderRequest(BaseModel):
    delivery_method: str
    shipping_address: Optional[str] = None