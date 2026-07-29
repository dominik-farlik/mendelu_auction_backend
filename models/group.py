from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base
from models.organization import Organization

if TYPE_CHECKING:
    from models.user import User


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organization.id"))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="groups")
    manager: Mapped[Optional["User"]] = relationship(back_populates="managed_groups")
    members: Mapped[List["User"]] = relationship(
        secondary="user_group",
        back_populates="groups"
    )


class GroupBase(BaseModel):
    name: str
    organization_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class GroupCreate(GroupBase):
    pass


class GroupUpdate(GroupBase):
    manager_id: int | None = None


class GroupResponse(GroupBase):
    id: int
    manager_id: int | None = None
    created_at: datetime

