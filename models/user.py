from typing import List, TYPE_CHECKING

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.role import Role
from models.user_group import user_group


if TYPE_CHECKING:
    from models.product import Product
    from models.group import Group


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str | None] = mapped_column(String(50))

    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), default=1)

    role: Mapped["Role"] = relationship(back_populates="users")
    products: Mapped[List["Product"]] = relationship(back_populates="owner")
    managed_groups: Mapped[List["Group"]] = relationship(back_populates="manager")
    groups: Mapped[List["Group"]] = relationship(
        secondary="user_group",
        back_populates="members"
    )