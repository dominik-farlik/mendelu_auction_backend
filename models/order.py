import enum
from datetime import datetime, UTC
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from models.base import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime(timezone=True), nullable=False)

    product = relationship("Product", back_populates="orders")