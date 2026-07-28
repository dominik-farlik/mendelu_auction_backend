from datetime import datetime
from enum import StrEnum
from typing import Optional, TYPE_CHECKING, List

from sqlalchemy import String, Float, ForeignKey, DateTime, Boolean, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.user import User
    from models.product_image import ProductImage


class SaleType(StrEnum):
    AUCTION = "auction"
    BUY_NOW = "buy_now"
    BOTH = "both"


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]]
    sale_type: Mapped[SaleType] = mapped_column(
        SQLEnum(SaleType, native_enum=False),
        default=SaleType.AUCTION
    )
    big_preview: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    starting_price: Mapped[float] = mapped_column(Float)
    buy_now_price: Mapped[float| None] = mapped_column(Float)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    cover_image: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner_id: Mapped[int] = mapped_column(ForeignKey("user.id")) 

    owner: Mapped["User"] = relationship(back_populates="products")
    images: Mapped[List["ProductImage"]] = relationship(back_populates="product")