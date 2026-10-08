from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from starlette import status

from config import get_settings
from database import get_db
from dependencies import RoleChecker
from models import User, Order, Group
from models.order import OrderStatus, ConfirmOrderRequest, DeliveryMethod
from models.product import OrderDetailResponse, ProductResponse, Product, Status
from models.role import RoleEnum
from routers.auth import get_current_user
from utils.order_payment_checker import process_next_bidder

router = APIRouter(prefix="/orders", tags=["Orders"])


allow_editor_or_manager = RoleChecker([RoleEnum.EDITOR, RoleEnum.MANAGER])


@router.get("/by-product/{product_id}", response_model=OrderDetailResponse)
async def get_order_by_product(
        product_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.product_id == product_id,
        Order.buyer_id == current_user.id,
        Order.status.in_([OrderStatus.PENDING, OrderStatus.PAID, OrderStatus.PROCESSING])
    ).first()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aktivní objednávka pro tento produkt nebyla nalezena."
        )

    return {
        "order_id": order.id,
        "amount": order.amount,
        "status": order.status,
        "expires_at": order.expires_at,
        "product": order.product,
        "bank_account": getattr(get_settings(), "TRANSPARENT_ACCOUNT", "Zatím nezadáno"),
        "variable_symbol": str(order.product.id)
    }


@router.get("/group/{group_id}", response_model=List[OrderDetailResponse], dependencies=[Depends(allow_editor_or_manager)])
async def get_orders_by_group(
        group_id: int,
        db: Session = Depends(get_db),
):
    """Získá všechny objednávky pro hotové produkty patřící do specifikované skupiny."""
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skupina s ID {group_id} nebyla nalezena."
        )

    orders = (
        db.query(Order)
        .options(joinedload(Order.buyer))
        .join(Product, Order.product_id == Product.id)
        .filter(
            Product.group_id == group_id,
            Product.status == Status.FINISHED,
        )
        .all()
    )

    return [
        {
            "order_id": order.id,
            "amount": order.amount,
            "status": order.status,
            "expires_at": order.expires_at,
            "product": order.product,
            "buyer": order.buyer,
            "delivery_method": order.delivery_method,
            "shipping_address": order.shipping_address,
            "bank_account": getattr(get_settings(), "TRANSPARENT_ACCOUNT", "Zatím nezadáno"),
            "variable_symbol": str(order.product.id),
        }
        for order in orders
    ]


@router.post("/{order_id}/confirm")
async def confirm_order(
        order_id: int,
        request: ConfirmOrderRequest,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id, Order.buyer_id == current_user.id).first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objednávka nebyla nalezena.")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tuto objednávku nelze potvrdit, nečeká na platbu.")

    if request.delivery_method == "shipping" and not request.shipping_address:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Při doručení poštou je adresa povinná.")

    db_delivery_method = DeliveryMethod.PICKUP if request.delivery_method == "personal" else DeliveryMethod.DELIVERY

    order.status = OrderStatus.PROCESSING
    order.delivery_method = db_delivery_method
    order.shipping_address = request.shipping_address if request.delivery_method == "shipping" else None

    db.commit()

    return {"message": "Objednávka byla potvrzena a čeká na zpracování platby."}


@router.post("/{order_id}/mark-paid", dependencies=[Depends(allow_editor_or_manager)])
async def mark_order_as_paid(
        order_id: int,
        db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objednávka nebyla nalezena.")

    if order.status != OrderStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Objednávku nelze označit jako zaplacenou. Aktuální stav je: {order.status.value}"
        )

    order.status = OrderStatus.PAID
    db.commit()

    # Zde můžete volitelně přidat odeslání e-mailu uživateli:
    # await send_payment_received_email(order.buyer.email, order.product.title)

    return {"message": f"Objednávka {order_id} byla úspěšně označena jako zaplacená."}


@router.post("/{order_id}/cancel-win")
async def cancel_won_auction(
        order_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id, Order.buyer_id == current_user.id).first()
    if not order or order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Objednávku nelze odmítnout.")

    order.status = OrderStatus.CANCELLED
    db.commit()

    await process_next_bidder(db, order.product_id)

    return {"message": "Výhra byla odmítnuta. Nabídka byla posunuta dalšímu dražiteli."}