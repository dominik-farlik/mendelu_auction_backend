from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.product import Product


class ProductImage(Base):
    __tablename__ = "product_image"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Vygenerovaný název souboru, např. "d8e8fca2...98.jpg"
    filename: Mapped[str] = mapped_column(String(255), unique=True)

    # Propojení s konkrétním produktem
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    product: Mapped["Product"] = relationship(back_populates="images")