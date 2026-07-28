from typing import List, TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.role import Role

if TYPE_CHECKING:
    from models.product import Product
    from models.group import Group


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
    products: Mapped[List["Product"]] = relationship(back_populates="owner")
    managed_groups: Mapped[List["Group"]] = relationship(back_populates="manager")
    groups: Mapped[List["Group"]] = relationship(
        secondary="user_group",
        back_populates="members"
    )


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: str
    first_name: str
    last_name: str
    username: str | None = None

    class Config:
        from_attributes = True