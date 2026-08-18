import asyncio
import logging
from datetime import datetime, UTC

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Bid, Product
from models.product import Status
from ws_manager import manager


logger = logging.getLogger(__name__)


async def finalize_auction(product_id: int, db: Session):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return

    highest_bid = db.query(Bid).filter(Bid.product_id == product_id).order_by(desc(Bid.amount)).first()

    product.status = Status.FINISHED
    db.commit()

    ws_payload = {
        "type": "AUCTION_ENDED",
        "payload": {
            "product_id": product_id,
            "winner_id": highest_bid.bidder_id if highest_bid else None,
            "final_price": highest_bid.amount if highest_bid else None,
            "message": "Aukce skončila!"
        }
    }
    await manager.broadcast_to_product(ws_payload, product_id)

    # 2. Zde můžeš zavolat asynchronní odeslání e-mailů (vítězi i poraženým)
    # await send_auction_end_emails(product, highest_bid)

    # 3. Zde můžeš vytvořit objednávku (Order) v databázi pro fakturaci
    # create_order_for_winner(product, highest_bid)


async def auction_ender_task():
    while True:
        try:
            db = SessionLocal()

            now_utc = datetime.now(UTC)

            ended_products = db.query(Product).filter(
                Product.ends_at <= now_utc,
                Product.status == Status.APPROVED.value
            ).all()

            if ended_products:
                logger.info(f"Finished auction found, ID: {[p.id for p in ended_products]}")
                for product in ended_products:
                    await finalize_auction(product.id, db)

        except Exception as e:
            logger.error(f"Error while checking finished auctions: {e}")
        finally:
            db.close()

        await asyncio.sleep(10)