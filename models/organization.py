from typing import List, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.group import Group


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    logo: Mapped[str | None] = mapped_column(String(255))

    groups: Mapped[List["Group"]] = relationship(back_populates="organization")


class OrganizationResponse(BaseModel):
    id: int
    name: str
    description: str
    logo: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationPublicResponse(OrganizationResponse):
    """Veřejný profil organizace včetně statistik aukcí."""
    total_raised: float
    finished_auctions_count: int
    active_auctions_count: int
