from typing import List, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.role import Role, RoleResponse

if TYPE_CHECKING:
    from models.product import Product
    from models.group import Group
    from models.bid import Bid
    from models.watchlist import Watchlist


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)

    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), default=1)

    role: Mapped["Role"] = relationship(back_populates="users")
    created_products: Mapped[List["Product"]] = relationship(back_populates="created_by")
    managed_groups: Mapped[List["Group"]] = relationship(back_populates="manager")
    groups: Mapped[List["Group"]] = relationship(secondary="user_group", back_populates="members")
    bids: Mapped[list["Bid"]] = relationship(back_populates="bidder", cascade="all, delete-orphan")
    followed_products: Mapped[list["Watchlist"]] = relationship(back_populates="follower", cascade="all, delete-orphan")


class UserBase(BaseModel):
    first_name: str
    last_name: str

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    id: int
    email: str
    username: str | None
    role: RoleResponse


class UserCreate(UserBase):
    email: str
    password: str
    username: str | None = None


class UserUpdate(UserBase):
    email: str
    username: str | None = None


class ManagerResponse(UserBase):
    id: int
