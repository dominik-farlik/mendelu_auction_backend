from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base
from models.organization import Organization


if TYPE_CHECKING:
    from models.user_group import user_group
    from models.user import User


class Group(Base):
    __tablename__ = "group"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organization.id"))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    organization: Mapped["Organization"] = relationship(back_populates="groups")
    manager: Mapped[Optional["User"]] = relationship(back_populates="managed_groups")
    members: Mapped[List["User"]] = relationship(
        secondary="user_group",
        back_populates="groups"
    )