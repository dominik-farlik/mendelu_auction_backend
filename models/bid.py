from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from models.user import User
    from models.product import Product

MAX_BID_AMOUNT = 100_000_000


class Bid(Base):
    __tablename__ = "bid"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[float] = mapped_column(nullable=False)
    bid_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    bidder_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"))

    bidder: Mapped["User"] = relationship(back_populates="bids")
    product: Mapped["Product"] = relationship(back_populates="bids")


class BidCreate(BaseModel):
    amount: float = Field(..., gt=0, le=MAX_BID_AMOUNT)

    model_config = ConfigDict(allow_inf_nan=False)
