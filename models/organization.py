from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class Organization(Base):
    __tablename__ = "organization"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)