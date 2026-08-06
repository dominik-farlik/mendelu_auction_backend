from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from models.user import User
    from models.product import Product


class Watchlist(Base):
    __tablename__ = "watchlist"

    __table_args__ = (
        UniqueConstraint('follower_id', 'product_id', name='uq_user_product_watchlist'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    started_follow: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    follower_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"))

    follower: Mapped["User"] = relationship(back_populates="followed_products")
    product: Mapped["Product"] = relationship(back_populates="followers")