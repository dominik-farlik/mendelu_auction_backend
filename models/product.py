from datetime import datetime
from enum import StrEnum
from typing import Optional, TYPE_CHECKING, List

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import String, Float, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.group import GroupBase
from models.user import UserResponse

if TYPE_CHECKING:
    from models.user import User
    from models.product_image import ProductImage
    from models.bid import Bid
    from models.group import Group


class SaleType(StrEnum):
    AUCTION = "auction"
    BUY_NOW = "buy_now"
    BOTH = "both"


class Status(StrEnum):
    ACTIVE = "active"
    PENDING = "pending"
    APPROVED = "approved"
    CANCELLED = "cancelled"


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]]
    sale_type: Mapped[SaleType] = mapped_column(String(20), default=SaleType.AUCTION)
    big_preview: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    starting_price: Mapped[float] = mapped_column(Float)
    buy_now_price: Mapped[float| None] = mapped_column(Float)
    min_bid: Mapped[float| None] = mapped_column(Float)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    cover_image: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    status: Mapped[Status] = mapped_column(String(10), default=Status.PENDING, nullable=False)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), nullable=False)

    created_by: Mapped["User"] = relationship(back_populates="created_products")
    group: Mapped["Group"] = relationship(back_populates="products")
    images: Mapped[List["ProductImage"]] = relationship(back_populates="product")
    bids: Mapped[List["Bid"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductBase(BaseModel):
    title: str = Field(..., max_length=100)
    description: Optional[str] = None
    starting_price: float = Field(..., gt=0)
    buy_now_price: Optional[float] = Field(None, gt=0)
    min_bid: Optional[float] = Field(None, gt=0)
    cover_image: Optional[str] = Field(None, max_length=255)
    sale_type: SaleType = SaleType.AUCTION
    big_preview: bool = False
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ProductImageResponse(BaseModel):
    filename: str

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(ProductBase):
    group_id: int


class ProductResponse(ProductBase):
    id: int
    created_by_id: int
    group: GroupBase
    created_at: datetime
    status: Status
    images: List[ProductImageResponse] = []


class ProductBid(BaseModel):
    bidder: UserResponse
    amount: float

    model_config = ConfigDict(from_attributes=True)
