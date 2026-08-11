from enum import StrEnum
from typing import List, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base


class RoleEnum(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"
    MANAGER = "manager"

if TYPE_CHECKING:
    from models.user import User


class Role(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[RoleEnum] = mapped_column(String(50), unique=True, index=True)

    users: Mapped[List["User"]] = relationship(back_populates="role")


class RoleResponse(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    name: RoleEnum