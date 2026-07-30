from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from models.user import User
    from models.product import Product


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    organization: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    manager_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    manager: Mapped[Optional["User"]] = relationship(back_populates="managed_groups")
    members: Mapped[List["User"]] = relationship(
        secondary="user_group",
        back_populates="groups"
    )
    products: Mapped[List["Product"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class GroupBase(BaseModel):
    name: str
    organization: str | None = None

    model_config = ConfigDict(from_attributes=True)


class GroupCreate(GroupBase):
    pass


class GroupUpdate(GroupBase):
    manager_id: int | None = None


class GroupResponse(GroupBase):
    id: int
    manager_id: int | None = None
    created_at: datetime

