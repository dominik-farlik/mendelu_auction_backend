import json
import os
from datetime import datetime, UTC
from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from sqlalchemy import select, delete
from sqlalchemy.orm import Session, selectinload

from database import get_db
from dependencies import RoleChecker, get_current_user_optional
from models import ProductImage, Bid
from models.product import Product, ProductResponse, ProductCreate, Status, ProductBid, ProductUpdateStatus
from models.group import Group
from models.role import RoleEnum
from models.user import User
from routers.auth import get_current_user
from utils import save_upload_file

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

allow_only_manager = RoleChecker([RoleEnum.MANAGER])
allow_editor_or_manager = RoleChecker([RoleEnum.EDITOR, RoleEnum.MANAGER])


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
        product_data: str = Form(..., description="JSON řetězec odpovídající ProductCreate"),
        cover_image: Optional[UploadFile] = File(None, description="Hlavní úvodní obrázek"),
        additional_images: List[UploadFile] = File([], description="Seznam dalších obrázků"),
        current_user: User = Depends(allow_editor_or_manager),
        db: Session = Depends(get_db)
):
    """
    Vytvoření nového produktu včetně nahrání hlavního obrázku a galerie.
    """
    try:
        product_in = ProductCreate(**json.loads(product_data))
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Neplatný formát JSON dat v poli product_data.")

    group_result = db.execute(select(Group).where(Group.id == product_in.group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skupina s ID {product_in.group_id} neexistuje."
        )

    new_product = Product(
        **product_in.model_dump(
            exclude={"cover_image"}),
            cover_image=save_upload_file(cover_image),
            created_by_id=current_user.id,
    )

    db.add(new_product)
    db.flush()

    for img_file in additional_images:
        if img_file.filename:
            img_path = save_upload_file(img_file)
            product_image = ProductImage(
                product_id=new_product.id,
                filename=img_path
            )
            db.add(product_image)

    db.commit()
    db.refresh(new_product)

    return new_product


@router.patch("/{product_id}",
              response_model=ProductResponse,
              status_code=status.HTTP_200_OK,
              dependencies=[Depends(allow_editor_or_manager)]
              )
async def update_product(
        product_id: int,
        product_data: str = Form(..., description="JSON řetězec odpovídající ProductCreate"),
        cover_image: Optional[UploadFile] = File(None, description="Nový hlavní úvodní obrázek"),
        additional_images: List[UploadFile] = File([], description="Seznam nových dalších obrázků"),
        db: Session = Depends(get_db)
):
    """
    Úprava existujícího produktu.
    Pokud je poskytnut nový cover_image, přepíše se (a starý smaže).
    Pokud jsou poskytnuty nové additional_images, nahradí starou galerii (a staré fotky se smažou).
    """

    product = db.execute(select(Product).where(Product.id == product_id)).scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produkt s ID {product_id} nebyl nalezen."
        )

    try:
        product_in = ProductCreate(**json.loads(product_data))
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Neplatný formát JSON dat v poli product_data."
        )

    if product_in.group_id != product.group_id:
        group = db.execute(select(Group).where(Group.id == product_in.group_id)).scalar_one_or_none()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skupina s ID {product_in.group_id} neexistuje."
            )

    update_data = product_in.model_dump(exclude={"cover_image"})
    for key, value in update_data.items():
        setattr(product, key, value)

    product.status = "pending"

    # Aktualizace hlavního obrázku (pokud byl nahrán nový)
    if cover_image and cover_image.filename:
        if product.cover_image and os.path.exists(product.cover_image):
            try:
                os.remove(product.cover_image)
            except OSError as e:
                print(f"Varování: Nepodařilo se smazat starý cover image {product.cover_image}: {e}")

        product.cover_image = save_upload_file(cover_image)

    # Aktualizace galerie (pokud byly nahrány nové fotky)
    if additional_images and additional_images[0].filename:
        old_gallery_images = db.execute(
            select(ProductImage).where(ProductImage.product_id == product.id)
        ).scalars().all()

        for old_img in old_gallery_images:
            if old_img.filename and os.path.exists(old_img.filename):
                try:
                    os.remove(old_img.filename)
                except OSError as e:
                    print(f"Varování: Nepodařilo se smazat obrázek z galerie {old_img.filename}: {e}")

        db.execute(delete(ProductImage).where(ProductImage.product_id == product.id))
        db.flush()

        for img_file in additional_images:
            if img_file.filename:
                img_path = save_upload_file(img_file)
                new_product_image = ProductImage(
                    product_id=product.id,
                    filename=img_path
                )
                db.add(new_product_image)

    db.commit()
    db.refresh(product)

    return product


@router.patch("/{product_id}/status", response_model=ProductResponse, dependencies=[Depends(allow_only_manager)])
async def update_product_status(
        product_id: int,
        status_data: ProductUpdateStatus,
        db: Session = Depends(get_db),
):
    """
    Schválení produktu manažerem (změna stavu na aktivní).
    """
    result = db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produkt nebyl nalezen."
        )

    product.status = status_data.status
    db.commit()
    db.refresh(product)

    return product


@router.get("/", response_model=List[ProductResponse])
async def get_products(
        current_user: Annotated[User, Depends(get_current_user_optional)],
        skip: int = 0,
        limit: int = 100,
        only_active: bool = True,
        db: Session = Depends(get_db)
):
    """Získání seznamu produktů"""
    now = datetime.now(UTC)

    query = select(Product).options(
        selectinload(Product.bids),
        selectinload(Product.followers)
    )

    if only_active:
        query = query.where(
            Product.status == Status.APPROVED,
            Product.starts_at <= now,
            Product.ends_at >= now
        )

    result = db.execute(query.offset(skip).limit(limit))
    products = result.scalars().all()

    for product in products:
        is_followed = False
        if current_user:
            is_followed = any(follow.follower_id == current_user.id for follow in product.followers)

        setattr(product, "is_followed", is_followed)

    return products


@router.get("/group/{group_id}", response_model=List[ProductResponse], dependencies=[Depends(get_current_user)])
async def get_products_by_group(
        group_id: int,
        db: Session = Depends(get_db),
):
    """Získá všechny produkty patřící do specifikované skupiny."""
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skupina s ID {group_id} nebyla nalezena."
        )

    return group.products


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
        product_id: int,
        current_user: Annotated[User, Depends(get_current_user_optional)],
        db: Session = Depends(get_db)
):
    """Získání detailu konkrétního produktu."""
    result = db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produkt nebyl nalezen."
        )

    product.bids = sorted(product.bids, key=lambda bid: bid.amount, reverse=True)

    is_followed = False
    if current_user:
        is_followed = any(follow.follower_id == current_user.id for follow in product.followers)
    setattr(product, "is_followed", is_followed)

    return product


@router.get("/{product_id}/bids", response_model=List[ProductBid])
async def get_product_bids(
        product_id: int,
        db: Session = Depends(get_db)
):
    """Získání příhozů produktu"""
    result = db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produkt nebyl nalezen."
        )

    bids_result = db.execute(
        select(Bid)
        .where(Bid.product_id == product_id)
        .order_by(Bid.amount.desc())
    )
    bids = bids_result.scalars().all()

    return bids
