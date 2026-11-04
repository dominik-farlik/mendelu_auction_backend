from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base
from models.organization import OrganizationResponse
from models.user import ManagerResponse, UserResponse

if TYPE_CHECKING:
    from models.user import User
    from models.product import Product
    from models.organization import Organization


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    manager_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organization.id", ondelete="SET NULL"),
        index=True
    )

    manager: Mapped[Optional["User"]] = relationship(back_populates="managed_groups")
    organization: Mapped[Optional["Organization"]] = relationship(back_populates="groups")
    members: Mapped[List["User"]] = relationship(
        secondary="user_group",
        back_populates="groups"
    )
    products: Mapped[List["Product"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class GroupBase(BaseModel):
    id: int | None = None
    name: str
    organization_id: int | None = None


class GroupWithOrganization(GroupBase):
    organization: OrganizationResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: str | None = None
    organization_id: int | None = None
    manager_id: int | None = None


class GroupResponse(GroupWithOrganization):
    members: List[UserResponse] | None = None
    manager: ManagerResponse
    created_at: datetime


class AddMember(BaseModel):
    email: str
