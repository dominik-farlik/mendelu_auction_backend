import asyncio
from datetime import datetime, UTC, timedelta

from database import logger, SessionLocal
from models import Product, User, Bid
from models.order import Order, OrderStatus
from utils.email_actions import send_runner_up_email


async def unpaid_order_checker_task():
    """1. Kontroluje expirované objednávky v nekonečném cyklu."""
    while True:
        db = SessionLocal()
        try:
            now_utc = datetime.now(UTC)

            expired_orders = db.query(Order).filter(
                Order.status == OrderStatus.PENDING,
                Order.expires_at <= now_utc
            ).all()

            for order in expired_orders:
                order.status = OrderStatus.EXPIRED
                db.commit()
                logger.info(f"Order ID {order.id} for product {order.product_id} expired due to non-payment.")

                await process_next_bidder(db, order.product_id)

        except Exception as e:
            logger.error(f"Error while checking unpaid orders: {e}")
            db.rollback()
        finally:
            db.close()

        await asyncio.sleep(60)


from sqlalchemy import desc


async def process_next_bidder(db, product_id: int):
    """2. Procesuje novou objednávku pro dalšího zájemce v pořadí (Optimalizováno)."""
    try:
        existing_buyers = db.query(Order.buyer_id).filter(Order.product_id == product_id)

        next_bid = (
            db.query(Bid)
            .filter(
                Bid.product_id == product_id,
                Bid.bidder_id.notin_(existing_buyers)
            )
            .order_by(desc(Bid.amount))
            .first()
        )

        if next_bid:
            new_expires_at = datetime.now(UTC) + timedelta(hours=48)
            next_order = Order(
                product_id=product_id,
                buyer_id=next_bid.bidder_id,
                amount=next_bid.amount,
                status=OrderStatus.PENDING,
                expires_at=new_expires_at
            )
            db.add(next_order)
            db.commit()

            user, product = (
                db.query(User, Product)
                .filter(User.id == next_bid.bidder_id, Product.id == product_id)
                .first()
            ) or (None, None)

            if user and product:
                await send_runner_up_email(user.email, product.title, next_bid.amount, new_expires_at)
                logger.info(f"Offered product {product.id} to runner-up user ID {next_bid.bidder_id}")
        else:
            logger.info(f"No more bidders available for product {product_id}.")

    except Exception as e:
        logger.error(f"Error processing next bidder for product {product_id}: {e}")
        db.rollback()