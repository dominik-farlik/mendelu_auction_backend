import asyncio
from datetime import datetime, UTC, timedelta

from sqlalchemy import desc

from database import logger, SessionLocal
from models import Product, User, Bid
from models.order import Order, OrderStatus
from utils.email_actions import send_runner_up_email


async def unpaid_order_checker_task():
    while True:
        try:
            db = SessionLocal()
            now_utc = datetime.now(UTC)

            expired_orders = db.query(Order).filter(
                Order.status == OrderStatus.PENDING,
                Order.expires_at <= now_utc
            ).all()

            for order in expired_orders:
                order.status = OrderStatus.EXPIRED
                db.commit()
                logger.info(f"Order ID {order.id} for product {order.product_id} expired due to non-payment.")

                bids = db.query(Bid).filter(Bid.product_id == order.product_id).order_by(desc(Bid.amount)).all()

                existing_buyer_ids = {o.buyer_id for o in db.query(Order).filter(Order.product_id == order.product_id).all()}

                next_bid = None
                for bid in bids:
                    if bid.bidder_id not in existing_buyer_ids:
                        next_bid = bid
                        break

                if next_bid:
                    new_expires_at = datetime.now(UTC) + timedelta(hours=48)
                    next_order = Order(
                        product_id=order.product_id,
                        buyer_id=next_bid.bidder_id,
                        amount=next_bid.amount,
                        status=OrderStatus.PENDING,
                        expires_at=new_expires_at
                    )
                    db.add(next_order)
                    db.commit()

                    next_user = db.query(User).filter(User.id == next_bid.bidder_id).first()
                    product = db.query(Product).filter(Product.id == order.product_id).first()
                    if next_user and product:
                        await send_runner_up_email(next_user.email, product.title, next_bid.amount, new_expires_at)
                        logger.info(f"Offered product {product.id} to runner-up user ID {next_bid.bidder_id}")
                else:
                    logger.info(f"No more bidders available for product {order.product_id}.")

        except Exception as e:
            logger.error(f"Error while checking unpaid orders: {e}")
        finally:
            db.close()

        await asyncio.sleep(60)