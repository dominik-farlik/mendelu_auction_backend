from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import get_db
from models import User, Product, Bid
from models.bid import BidCreate
from models.user import UserResponse, UserUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def read_my_profile(current_user: Annotated[User, Depends(get_current_user)]):
    """Vrátí profil aktuálně přihlášeného uživatele"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
        user_update: UserUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db)
):
    """Upraví údaje aktuálně přihlášeného uživatele"""
    current_user.username = user_update.username
    current_user.email = user_update.email
    current_user.first_name = user_update.first_name
    current_user.last_name = user_update.last_name

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/bid/{product_id}", status_code=status.HTTP_201_CREATED)
async def bid(
        product_id: int,
        bid_data: BidCreate,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aukce nebyla nalezena"
        )

    highest_bid = db.query(Bid).filter(Bid.product_id == product_id).order_by(desc(Bid.amount)).first()

    if highest_bid:
        required_minimum = highest_bid.amount
        if product.min_bid:
            required_minimum += product.min_bid
    else:
        required_minimum = getattr(product, 'starting_price', 0)
    print(required_minimum, product.min_bid)
    if bid_data.amount < required_minimum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Příhoz musí být alespoň {required_minimum} Kč"
        )

    new_bid = Bid(
        amount=bid_data.amount,
        bidder_id=current_user.id,
        product_id=product_id
    )

    db.add(new_bid)
    db.commit()
    db.refresh(new_bid)

    return {"message": "Přihození bylo úspěšné."}
