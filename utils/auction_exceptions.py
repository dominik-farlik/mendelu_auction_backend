from datetime import datetime, UTC

from fastapi import HTTPException
from starlette import status

from models import Product
from models.product import Status


def check_auction_existence(product: Product | None) -> None:
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aukce nebyla nalezena"
        )


def check_auction_active(product: Product) -> None:
    if product.status == Status.FINISHED.value:
        raise HTTPException(status_code=409, detail="Aukce již skončila (vyhodnocuje se).")

    if product.status != Status.APPROVED.value:
        raise HTTPException(status_code=403, detail="Tato aukce není aktuálně spuštěna.")

    now_utc = datetime.now(UTC)

    if product.starts_at and product.starts_at >= now_utc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aukce ještě nezačala"
        )

    if product.ends_at and product.ends_at <= now_utc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aukce již skončila"
        )