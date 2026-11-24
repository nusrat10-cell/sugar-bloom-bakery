from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from database import get_supabase
from security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    user_id = payload["sub"]
    db = get_supabase()
    res = db.table("users").select("*").eq("id", user_id).limit(1).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user = res.data[0]
    if user.get("is_banned"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is banned. Reason: {user.get('ban_reason') or 'Policy violation'}",
        )

    active_sessions = (
        db.table("refresh_tokens")
        .select("id")
        .eq("user_id", user_id)
        .eq("revoked", False)
        .limit(1)
        .execute()
    )
    if not active_sessions.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked. Please log in again.",
        )

    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


CurrentUserDep = Annotated[dict, Depends(get_current_user)]
AdminUserDep = Annotated[dict, Depends(require_admin)]


def get_group_membership(group_id: str, user_id: str) -> dict | None:
    db = get_supabase()
    res = (
        db.table("group_members")
        .select("*")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


def require_group_owner(group_id: str, user: dict) -> dict:
    db = get_supabase()
    res = db.table("groups").select("*").eq("id", group_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Group not found")
    group = res.data[0]
    if user.get("role") != "admin" and group["owner_id"] != user["id"]:
        raise HTTPException(
            status_code=403,
            detail="Only the group owner can perform this action",
        )
    return group


def check_product_permission(product: dict, user: dict, action: str) -> None:
    """
    action: 'read' | 'update' | 'delete'
    - Admin can access any record.
    - Owner can read, update, delete their own record.
    - Shared group member can read if in group, and update if can_update is True.
      Only owner/admin can delete.
    """
    if user.get("role") == "admin":
        return

    if product["owner_id"] == user["id"]:
        return

    if action == "delete":
        raise HTTPException(status_code=403, detail="Only the owner can delete this item")

    group_id = product.get("group_id")
    if group_id:
        member = get_group_membership(group_id, user["id"])
        if member:
            if action == "read":
                return
            if action == "update" and member.get("can_update"):
                return

    raise HTTPException(status_code=403, detail="Access denied for this record")