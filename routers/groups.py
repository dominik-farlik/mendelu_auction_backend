from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from dependencies import RoleChecker
from models import Group
from models.group import GroupResponse, GroupCreate, GroupUpdate, AddMember
from models.role import RoleEnum
from routers.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/groups", tags=["Groups"])

allow_only_manager = RoleChecker([RoleEnum.MANAGER])


@router.get("/", response_model=List[GroupResponse])
async def get_groups(
        current_user: Annotated[User, Depends(allow_only_manager)],
        db: Session = Depends(get_db)
):
    """Vrátí seznam všech skupin (pouze pro managery/adminy)."""
    statement = select(Group)
    groups = db.scalars(statement).all()
    return groups


@router.get("/my", response_model=List[GroupResponse])
async def get_user_groups(
        current_user: Annotated[User, Depends(get_current_user)],
):
    """Vrátí seznam skupin, kterých je aktuální přihlášený uživatel členem."""
    return current_user.groups


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(group_id: int, db: Session = Depends(get_db)):
    """Vrátí detail konkrétní skupiny podle ID."""
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skupina nenalezena"
        )
    return group


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
        group_data: GroupCreate,
        current_user: Annotated[User, Depends(allow_only_manager)],
        db: Session = Depends(get_db),
):
    """Vytvoří novou skupinu."""
    existing = db.scalar(select(Group).where(Group.name == group_data.name))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skupina s tímto názvem již existuje"
        )

    new_group = Group(
        name=group_data.name,
        organization=group_data.organization,
        manager_id=current_user.id
    )

    current_user.groups.append(new_group)

    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
        group_id: int,
        group_data: GroupUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db),
):
    """Aktualizuje existující skupinu."""
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skupina nenalezena"
        )

    # Aktualizujeme pouze pole, která byla v požadavku poslána
    update_data = group_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(group, key, value)

    db.commit()
    db.refresh(group)
    return group


@router.post("/{group_id}/members")
async def add_member_to_group(
        group_id: int,
        member_data: AddMember,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db),
):
    """Přidá existujícího uživatele do skupiny podle jeho e-mailu."""

    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skupina nenalezena"
        )

    user_to_add: User | None = db.scalar(select(User).where(User.email == member_data.email))
    if not user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Uživatel s e-mailem '{member_data.email}' nebyl nalezen"
        )

    if user_to_add.role.name not in (RoleEnum.EDITOR, RoleEnum.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Uživatel nemá dostatečné oprávnění pro přidání do skupiny."
        )

    if group in user_to_add.groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tento uživatel je již členem dané skupiny"
        )

    group.members.append(user_to_add)
    db.commit()
    db.refresh(group)

    return {"message": "Uživatel byl úspěšně přidán do skupiny."}


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
        group_id: int,
        current_user: Annotated[User, Depends(allow_only_manager)],
        db: Session = Depends(get_db),
):
    """Smaže skupinu podle ID."""
    group = db.get(Group, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skupina nenalezena"
        )

    db.delete(group)
    db.commit()
    return None
