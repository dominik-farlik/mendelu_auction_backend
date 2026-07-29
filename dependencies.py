from typing import Annotated
from fastapi import Depends, HTTPException, status
from models import User
from models.role import RoleEnum
from routers.auth import get_current_user

class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: Annotated[User, Depends(get_current_user)]):
        if not current_user.role or current_user.role.name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nemáte dostatečná oprávnění pro tuto akci."
            )
        return current_user