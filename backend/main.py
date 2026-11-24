import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field

from audit import log_action
from config import get_settings
from database import get_supabase
from rbac import (
    AdminUserDep,
    CurrentUserDep,
    check_product_permission,
    get_group_membership,
    require_group_owner,
)
from security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)

settings = get_settings()
app = FastAPI(title="Sugar Bloom Bakery API")

allowed_origins = [
    origin.strip()
    for origin in settings.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REFRESH_COOKIE_NAME = "refresh_token"


def set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="none" if settings.COOKIE_SECURE else "lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        samesite="none" if settings.COOKIE_SECURE else "lax",
        secure=settings.COOKIE_SECURE,
    )


def issue_session(user: dict, request: Request, response: Response) -> dict:
    db = get_supabase()
    raw_refresh = create_refresh_token()
    token_hash = hash_token(raw_refresh)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    ).isoformat()

    ip_addr = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    db.table("refresh_tokens").insert(
        {
            "user_id": user["id"],
            "token_hash": token_hash,
            "expires_at": expires_at,
            "revoked": False,
            "ip_address": ip_addr,
            "user_agent": user_agent,
        }
    ).execute()

    set_refresh_cookie(response, raw_refresh)
    access_token = create_access_token(
        subject=user["id"],
        role=user["role"],
        username=user["username"],
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
            "is_banned": user.get("is_banned", False),
        },
    }


# ---------- Schemas ----------

class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=40)
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=40)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    category: str = Field(min_length=1, max_length=60)
    price: float = Field(ge=0)
    stock: int = Field(ge=0)
    group_id: str | None = None
    assigned_to: str | None = None


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=60)
    price: float | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    assigned_to: str | None = None


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = ""


class GroupUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = ""


class GroupMemberPermissionRequest(BaseModel):
    user_id: str
    can_create: bool = False
    can_update: bool = False
    can_assign: bool = False


class RoleUpdateRequest(BaseModel):
    role: Literal["user", "admin"]


class BanRequest(BaseModel):
    banned: bool
    reason: str | None = None


# ---------- Auth & Profile Routes ----------

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, request: Request, response: Response):
    db = get_supabase()
    email_clean = payload.email.strip().lower()
    username_clean = payload.username.strip()

    existing_email = db.table("users").select("id").eq("email", email_clean).limit(1).execute()
    if existing_email.data:
        raise HTTPException(status_code=400, detail="Email is already registered")

    existing_user = (
        db.table("users").select("id").eq("username", username_clean).limit(1).execute()
    )
    if existing_user.data:
        raise HTTPException(status_code=400, detail="Username is already taken")

    user_insert = (
        db.table("users")
        .insert(
            {
                "email": email_clean,
                "username": username_clean,
                "full_name": payload.full_name.strip(),
                "password_hash": hash_password(payload.password),
                "role": "user",
                "is_banned": False,
            }
        )
        .execute()
    )
    created_user = user_insert.data[0]

    log_action(
        action="SIGNUP",
        user_id=created_user["id"],
        actor_email=created_user["email"],
        target_type="user",
        target_id=created_user["id"],
        details=f"Registered account ({created_user['username']})",
        request=request,
    )

    return issue_session(created_user, request, response)


@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request, response: Response):
    db = get_supabase()
    email_clean = payload.email.strip().lower()

    res = db.table("users").select("*").eq("email", email_clean).limit(1).execute()
    if not res.data:
        log_action(
            action="LOGIN_FAILED",
            user_id=None,
            actor_email=email_clean,
            target_type="auth",
            details="Unknown email",
            request=request,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = res.data[0]
    if not verify_password(payload.password, user["password_hash"]):
        log_action(
            action="LOGIN_FAILED",
            user_id=user["id"],
            actor_email=user["email"],
            target_type="auth",
            details="Incorrect password",
            request=request,
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.get("is_banned"):
        log_action(
            action="LOGIN_FAILED",
            user_id=user["id"],
            actor_email=user["email"],
            target_type="auth",
            details="Banned account login attempt",
            request=request,
        )
        raise HTTPException(
            status_code=403,
            detail=f"Account is banned. Reason: {user.get('ban_reason') or 'Policy violation'}",
        )

    log_action(
        action="LOGIN_SUCCESS",
        user_id=user["id"],
        actor_email=user["email"],
        target_type="auth",
        target_id=user["id"],
        details="User logged in",
        request=request,
    )

    return issue_session(user, request, response)


@app.post("/api/auth/refresh")
def refresh_access_token(request: Request, response: Response):
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    db = get_supabase()
    token_hash = hash_token(raw_token)
    res = (
        db.table("refresh_tokens")
        .select("*")
        .eq("token_hash", token_hash)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    token_row = res.data[0]
    if token_row.get("revoked"):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    expires_dt = datetime.fromisoformat(token_row["expires_at"].replace("Z", "+00:00"))
    if expires_dt <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token has expired")

    user_res = (
        db.table("users").select("*").eq("id", token_row["user_id"]).limit(1).execute()
    )
    if not user_res.data:
        raise HTTPException(status_code=401, detail="User not found")

    user = user_res.data[0]
    if user.get("is_banned"):
        raise HTTPException(status_code=403, detail="Account is banned")

    db.table("refresh_tokens").update({"revoked": True}).eq("id", token_row["id"]).execute()

    new_raw_refresh = create_refresh_token()
    new_hash = hash_token(new_raw_refresh)
    new_expires = (
        datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    ).isoformat()

    db.table("refresh_tokens").insert(
        {
            "user_id": user["id"],
            "token_hash": new_hash,
            "expires_at": new_expires,
            "revoked": False,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        }
    ).execute()

    set_refresh_cookie(response, new_raw_refresh)
    access_token = create_access_token(
        subject=user["id"],
        role=user["role"],
        username=user["username"],
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
            "is_banned": user.get("is_banned", False),
        },
    }


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    db = get_supabase()
    if raw_token:
        token_hash = hash_token(raw_token)
        found = (
            db.table("refresh_tokens")
            .select("*")
            .eq("token_hash", token_hash)
            .limit(1)
            .execute()
        )
        if found.data:
            row = found.data[0]
            db.table("refresh_tokens").update({"revoked": True}).eq("id", row["id"]).execute()
            user_res = (
                db.table("users")
                .select("email")
                .eq("id", row["user_id"])
                .limit(1)
                .execute()
            )
            actor_email = user_res.data[0]["email"] if user_res.data else None
            log_action(
                action="LOGOUT",
                user_id=row["user_id"],
                actor_email=actor_email,
                target_type="session",
                target_id=row["id"],
                details="User logged out",
                request=request,
            )

    clear_refresh_cookie(response)
    return {"ok": True}


@app.get("/api/auth/me")
def get_me(current_user: CurrentUserDep):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "username": current_user["username"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
        "is_banned": current_user.get("is_banned", False),
    }


@app.patch("/api/auth/profile")
def update_profile(
    payload: ProfileUpdateRequest,
    request: Request,
    current_user: CurrentUserDep,
):
    db = get_supabase()
    username_clean = payload.username.strip()

    taken = (
        db.table("users")
        .select("id")
        .eq("username", username_clean)
        .neq("id", current_user["id"])
        .limit(1)
        .execute()
    )
    if taken.data:
        raise HTTPException(status_code=400, detail="Username is already taken")

    updated = (
        db.table("users")
        .update(
            {
                "full_name": payload.full_name.strip(),
                "username": username_clean,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", current_user["id"])
        .execute()
    )
    u = updated.data[0]

    log_action(
        action="PROFILE_UPDATED",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="user",
        target_id=current_user["id"],
        details=f"Updated profile username={u['username']}",
        request=request,
    )

    return {
        "id": u["id"],
        "email": u["email"],
        "username": u["username"],
        "full_name": u["full_name"],
        "role": u["role"],
    }


@app.post("/api/auth/change-password")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    current_user: CurrentUserDep,
):
    db = get_supabase()
    if not verify_password(payload.current_password, current_user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    db.table("users").update(
        {
            "password_hash": hash_password(payload.new_password),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", current_user["id"]).execute()

    db.table("refresh_tokens").update({"revoked": True}).eq(
        "user_id", current_user["id"]
    ).execute()
    clear_refresh_cookie(response)

    log_action(
        action="PASSWORD_CHANGED",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="user",
        target_id=current_user["id"],
        details="Changed password and revoked all refresh sessions",
        request=request,
    )

    return {"ok": True, "message": "Password updated. Please log in again."}


@app.get("/api/auth/sessions")
def list_sessions(current_user: CurrentUserDep):
    db = get_supabase()
    res = (
        db.table("refresh_tokens")
        .select("id, ip_address, user_agent, expires_at, revoked, created_at")
        .eq("user_id", current_user["id"])
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    return res.data


@app.delete("/api/auth/sessions/{session_id}")
def revoke_session(
    session_id: str,
    request: Request,
    response: Response,
    current_user: CurrentUserDep,
):
    db = get_supabase()
    res = (
        db.table("refresh_tokens")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", current_user["id"])
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session_row = res.data[0]
    raw_cookie = request.cookies.get(REFRESH_COOKIE_NAME)
    is_current = bool(raw_cookie and hash_token(raw_cookie) == session_row["token_hash"])

    db.table("refresh_tokens").update({"revoked": True}).eq("id", session_id).execute()

    if is_current:
        clear_refresh_cookie(response)

    log_action(
        action="LOGOUT",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="session",
        target_id=session_id,
        details="Revoked session",
        request=request,
    )
    return {"ok": True, "is_current_session": is_current}


# ---------- Products (Main Domain Resource) Routes ----------

@app.get("/api/products")
def list_products(
    current_user: CurrentUserDep,
    scope: Literal["all", "mine"] = "all",
):
    db = get_supabase()
    all_products = (
        db.table("products").select("*").order("created_at", desc=True).execute().data
    )

    if current_user.get("role") == "admin" and scope == "all":
        return all_products

    memberships = (
        db.table("group_members")
        .select("group_id")
        .eq("user_id", current_user["id"])
        .execute()
        .data
    )
    member_group_ids = {m["group_id"] for m in memberships}

    visible = []
    for p in all_products:
        is_owner = p["owner_id"] == current_user["id"]
        is_assigned = p.get("assigned_to") == current_user["id"]
        in_shared_group = (
            scope == "all"
            and p.get("group_id") is not None
            and p["group_id"] in member_group_ids
        )
        if is_owner or is_assigned or in_shared_group:
            visible.append(p)

    return visible


@app.post("/api/products", status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreateRequest,
    request: Request,
    current_user: CurrentUserDep,
):
    db = get_supabase()

    if payload.group_id:
        grp_res = (
            db.table("groups").select("*").eq("id", payload.group_id).limit(1).execute()
        )
        if not grp_res.data:
            raise HTTPException(status_code=404, detail="Group not found")
        group = grp_res.data[0]

        if current_user.get("role") != "admin" and group["owner_id"] != current_user["id"]:
            membership = get_group_membership(payload.group_id, current_user["id"])
            if not membership or not membership.get("can_create"):
                raise HTTPException(
                    status_code=403,
                    detail="You do not have can_create permission in this group",
                )

        if payload.assigned_to and current_user.get("role") != "admin" and group["owner_id"] != current_user["id"]:
            membership = get_group_membership(payload.group_id, current_user["id"])
            if not membership or not membership.get("can_assign"):
                raise HTTPException(
                    status_code=403,
                    detail="You do not have can_assign permission in this group",
                )

    created = (
        db.table("products")
        .insert(
            {
                "owner_id": current_user["id"],
                "group_id": payload.group_id,
                "assigned_to": payload.assigned_to,
                "name": payload.name.strip(),
                "description": payload.description.strip(),
                "category": payload.category.strip(),
                "price": payload.price,
                "stock": payload.stock,
            }
        )
        .execute()
        .data[0]
    )

    log_action(
        action="ITEM_CREATED",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="product",
        target_id=created["id"],
        details=f"Created item '{created['name']}'",
        request=request,
    )

    return created


@app.patch("/api/products/{product_id}")
def update_product(
    product_id: str,
    payload: ProductUpdateRequest,
    request: Request,
    current_user: CurrentUserDep,
):
    db = get_supabase()
    res = db.table("products").select("*").eq("id", product_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Item not found")

    product = res.data[0]
    check_product_permission(product, current_user, action="update")

    if payload.assigned_to is not None and current_user.get("role") != "admin":
        if product["owner_id"] != current_user["id"]:
            group_id = product.get("group_id")
            member = get_group_membership(group_id, current_user["id"]) if group_id else None
            if not member or not member.get("can_assign"):
                raise HTTPException(
                    status_code=403,
                    detail="You do not have can_assign permission for this item",
                )

    updates: dict = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.description is not None:
        updates["description"] = payload.description.strip()
    if payload.category is not None:
        updates["category"] = payload.category.strip()
    if payload.price is not None:
        updates["price"] = payload.price
    if payload.stock is not None:
        updates["stock"] = payload.stock
    if payload.assigned_to is not None:
        updates["assigned_to"] = payload.assigned_to

    updated = (
        db.table("products").update(updates).eq("id", product_id).execute().data[0]
    )

    log_action(
        action="ITEM_UPDATED",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="product",
        target_id=product_id,
        details=f"Updated item '{updated['name']}'",
        request=request,
    )

    return updated


@app.delete("/api/products/{product_id}")
def delete_product(
    product_id: str,
    request: Request,
    current_user: CurrentUserDep,
):
    db = get_supabase()
    res = db.table("products").select("*").eq("id", product_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Item not found")

    product = res.data[0]
    check_product_permission(product, current_user, action="delete")

    db.table("products").delete().eq("id", product_id).execute()

    log_action(
        action="ITEM_DELETED",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="product",
        target_id=product_id,
        details=f"Deleted item '{product['name']}'",
        request=request,
    )

    return {"ok": True, "deleted_id": product_id}


# ---------- Groups & Member Permissions Routes ----------

@app.get("/api/groups")
def list_groups(current_user: CurrentUserDep):
    db = get_supabase()
    all_groups = db.table("groups").select("*").order("created_at", desc=True).execute().data
    all_members = db.table("group_members").select("*").execute().data

    user_member_group_ids = {
        m["group_id"] for m in all_members if m["user_id"] == current_user["id"]
    }

    result = []
    for g in all_groups:
        if (
            current_user.get("role") == "admin"
            or g["owner_id"] == current_user["id"]
            or g["id"] in user_member_group_ids
        ):
            g_members = [m for m in all_members if m["group_id"] == g["id"]]
            result.append({**g, "members": g_members})
    return result


@app.post("/api/groups", status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreateRequest,
    request: Request,
    current_user: CurrentUserDep,
):
    db = get_supabase()
    created = (
        db.table("groups")
        .insert(
            {
                "name": payload.name.strip(),
                "description": payload.description.strip(),
                "owner_id": current_user["id"],
            }
        )
        .execute()
        .data[0]
    )

    log_action(
        action="GROUP_CREATED",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="group",
        target_id=created["id"],
        details=f"Created group '{created['name']}'",
        request=request,
    )

    return created


@app.patch("/api/groups/{group_id}")
def update_group(
    group_id: str,
    payload: GroupUpdateRequest,
    request: Request,
    current_user: CurrentUserDep,
):
    require_group_owner(group_id, current_user)
    db = get_supabase()
    updated = (
        db.table("groups")
        .update(
            {
                "name": payload.name.strip(),
                "description": payload.description.strip(),
            }
        )
        .eq("id", group_id)
        .execute()
        .data[0]
    )

    log_action(
        action="GROUP_UPDATED",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="group",
        target_id=group_id,
        details=f"Renamed group to '{updated['name']}'",
        request=request,
    )
    return updated


@app.delete("/api/groups/{group_id}")
def delete_group(
    group_id: str,
    request: Request,
    current_user: CurrentUserDep,
):
    group = require_group_owner(group_id, current_user)
    db = get_supabase()
    db.table("products").update({"group_id": None}).eq("group_id", group_id).execute()
    db.table("group_members").delete().eq("group_id", group_id).execute()
    db.table("groups").delete().eq("id", group_id).execute()

    log_action(
        action="GROUP_DELETED",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="group",
        target_id=group_id,
        details=f"Deleted group '{group['name']}'",
        request=request,
    )
    return {"ok": True, "deleted_id": group_id}


@app.post("/api/groups/{group_id}/members")
def upsert_group_member(
    group_id: str,
    payload: GroupMemberPermissionRequest,
    request: Request,
    current_user: CurrentUserDep,
):
    group = require_group_owner(group_id, current_user)
    if payload.user_id == group["owner_id"]:
        raise HTTPException(
            status_code=400, detail="Group owner already has full permissions"
        )

    db = get_supabase()
    target_user = (
        db.table("users").select("id, email").eq("id", payload.user_id).limit(1).execute()
    )
    if not target_user.data:
        raise HTTPException(status_code=404, detail="Target user not found")

    existing = (
        db.table("group_members")
        .select("*")
        .eq("group_id", group_id)
        .eq("user_id", payload.user_id)
        .limit(1)
        .execute()
    )

    if existing.data:
        row = (
            db.table("group_members")
            .update(
                {
                    "can_create": payload.can_create,
                    "can_update": payload.can_update,
                    "can_assign": payload.can_assign,
                }
            )
            .eq("id", existing.data[0]["id"])
            .execute()
            .data[0]
        )
    else:
        row = (
            db.table("group_members")
            .insert(
                {
                    "group_id": group_id,
                    "user_id": payload.user_id,
                    "can_create": payload.can_create,
                    "can_update": payload.can_update,
                    "can_assign": payload.can_assign,
                }
            )
            .execute()
            .data[0]
        )

    log_action(
        action="GROUP_MEMBER_UPDATED",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="group_member",
        target_id=row["id"],
        details=(
            f"Set permissions for user {payload.user_id} in group '{group['name']}': "
            f"create={payload.can_create}, update={payload.can_update}, assign={payload.can_assign}"
        ),
        request=request,
    )
    return row


@app.delete("/api/groups/{group_id}/members/{member_user_id}")
def remove_group_member(
    group_id: str,
    member_user_id: str,
    request: Request,
    current_user: CurrentUserDep,
):
    group = require_group_owner(group_id, current_user)
    db = get_supabase()
    db.table("group_members").delete().eq("group_id", group_id).eq(
        "user_id", member_user_id
    ).execute()

    log_action(
        action="GROUP_MEMBER_REMOVED",
        user_id=current_user["id"],
        actor_email=current_user["email"],
        target_type="group",
        target_id=group_id,
        details=f"Removed user {member_user_id} from group '{group['name']}'",
        request=request,
    )
    return {"ok": True}


# ---------- Admin Routes ----------

@app.get("/api/admin/overview")
def admin_overview(admin_user: AdminUserDep):
    db = get_supabase()
    users = db.table("users").select("id, role, is_banned").execute().data
    products = db.table("products").select("id, price, stock").execute().data
    groups = db.table("groups").select("id").execute().data
    logs = db.table("activity_logs").select("id, action").execute().data

    total_inventory_value = sum(
        float(p.get("price", 0) or 0) * int(p.get("stock", 0) or 0) for p in products
    )
    failed_logins = sum(1 for l in logs if l.get("action") == "LOGIN_FAILED")

    return {
        "total_users": len(users),
        "admin_users": sum(1 for u in users if u.get("role") == "admin"),
        "banned_users": sum(1 for u in users if u.get("is_banned")),
        "total_products": len(products),
        "total_inventory_value": round(total_inventory_value, 2),
        "total_groups": len(groups),
        "total_activity_logs": len(logs),
        "failed_login_attempts": failed_logins,
    }


@app.get("/api/admin/users")
def admin_list_users(
    admin_user: AdminUserDep,
    search: str = Query(default=""),
    role: str = Query(default=""),
):
    db = get_supabase()
    users = (
        db.table("users")
        .select("id, email, username, full_name, role, is_banned, ban_reason, created_at")
        .order("created_at", desc=True)
        .execute()
        .data
    )

    q = search.strip().lower()
    filtered = []
    for u in users:
        if role and u.get("role") != role:
            continue
        if q and q not in (u.get("email") or "").lower() and q not in (
            u.get("username") or ""
        ).lower() and q not in (u.get("full_name") or "").lower():
            continue
        filtered.append(u)
    return filtered


@app.patch("/api/admin/users/{user_id}/role")
def admin_update_role(
    user_id: str,
    payload: RoleUpdateRequest,
    request: Request,
    admin_user: AdminUserDep,
):
    if user_id == admin_user["id"] and payload.role != "admin":
        raise HTTPException(status_code=400, detail="Cannot remove your own admin role")

    db = get_supabase()
    existing = db.table("users").select("*").eq("id", user_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    updated = (
        db.table("users")
        .update({"role": payload.role, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", user_id)
        .execute()
        .data[0]
    )

    log_action(
        action="USER_ROLE_CHANGED",
        user_id=admin_user["id"],
        actor_email=admin_user["email"],
        target_type="user",
        target_id=user_id,
        details=f"Set role={payload.role} for {updated['email']}",
        request=request,
    )
    return updated


@app.patch("/api/admin/users/{user_id}/ban")
def admin_ban_user(
    user_id: str,
    payload: BanRequest,
    request: Request,
    admin_user: AdminUserDep,
):
    if user_id == admin_user["id"] and payload.banned:
        raise HTTPException(status_code=400, detail="Cannot ban your own admin account")

    db = get_supabase()
    existing = db.table("users").select("*").eq("id", user_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    reason = payload.reason.strip() if payload.reason else None
    updated = (
        db.table("users")
        .update(
            {
                "is_banned": payload.banned,
                "ban_reason": reason if payload.banned else None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", user_id)
        .execute()
        .data[0]
    )

    if payload.banned:
        db.table("refresh_tokens").update({"revoked": True}).eq("user_id", user_id).execute()

    log_action(
        action="USER_BANNED" if payload.banned else "USER_UNBANNED",
        user_id=admin_user["id"],
        actor_email=admin_user["email"],
        target_type="user",
        target_id=user_id,
        details=(
            f"{'Banned' if payload.banned else 'Unbanned'} {updated['email']}"
            + (f" ({reason})" if payload.banned and reason else "")
        ),
        request=request,
    )
    return updated


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: str,
    request: Request,
    admin_user: AdminUserDep,
):
    if user_id == admin_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")

    db = get_supabase()
    existing = db.table("users").select("*").eq("id", user_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    target = existing.data[0]
    db.table("refresh_tokens").delete().eq("user_id", user_id).execute()
    db.table("group_members").delete().eq("user_id", user_id).execute()
    db.table("groups").delete().eq("owner_id", user_id).execute()
    db.table("products").delete().eq("owner_id", user_id).execute()
    db.table("users").delete().eq("id", user_id).execute()

    log_action(
        action="USER_DELETED",
        user_id=admin_user["id"],
        actor_email=admin_user["email"],
        target_type="user",
        target_id=user_id,
        details=f"Deleted user {target['email']}",
        request=request,
    )
    return {"ok": True, "deleted_id": user_id}


@app.get("/api/admin/products")
def admin_list_all_products(admin_user: AdminUserDep):
    db = get_supabase()
    return (
        db.table("products").select("*").order("created_at", desc=True).execute().data
    )


@app.delete("/api/admin/products/{product_id}")
def admin_moderate_delete_product(
    product_id: str,
    request: Request,
    admin_user: AdminUserDep,
):
    db = get_supabase()
    existing = db.table("products").select("*").eq("id", product_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Item not found")

    item = existing.data[0]
    db.table("products").delete().eq("id", product_id).execute()

    log_action(
        action="ADMIN_ITEM_DELETED",
        user_id=admin_user["id"],
        actor_email=admin_user["email"],
        target_type="product",
        target_id=product_id,
        details=f"Moderated/deleted item '{item['name']}'",
        request=request,
    )
    return {"ok": True, "deleted_id": product_id}


@app.get("/api/admin/logs")
def admin_list_logs(
    admin_user: AdminUserDep,
    action: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=500),
):
    db = get_supabase()
    query = db.table("activity_logs").select("*").order("created_at", desc=True).limit(limit)
    rows = query.execute().data
    if action:
        rows = [r for r in rows if r.get("action") == action]
    return rows


@app.get("/api/admin/security")
def admin_security_summary(admin_user: AdminUserDep):
    db = get_supabase()
    sessions = (
        db.table("refresh_tokens")
        .select("id, user_id, ip_address, user_agent, revoked, expires_at, created_at")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
        .data
    )
    failed_logins = (
        db.table("activity_logs")
        .select("*")
        .eq("action", "LOGIN_FAILED")
        .order("created_at", desc=True)
        .limit(30)
        .execute()
        .data
    )
    return {
        "recent_sessions": sessions,
        "failed_logins": failed_logins,
    }


@app.get("/api/admin/export/products.csv")
def admin_export_products_csv(admin_user: AdminUserDep):
    db = get_supabase()
    products = db.table("products").select("*").order("created_at", desc=True).execute().data

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "name", "category", "price", "stock", "owner_id", "group_id", "assigned_to", "created_at"]
    )
    for p in products:
        writer.writerow(
            [
                p.get("id"),
                p.get("name"),
                p.get("category"),
                p.get("price"),
                p.get("stock"),
                p.get("owner_id"),
                p.get("group_id") or "",
                p.get("assigned_to") or "",
                p.get("created_at"),
            ]
        )

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bakery_products.csv"},
    )


@app.get("/api/admin/export/logs.csv")
def admin_export_logs_csv(admin_user: AdminUserDep):
    db = get_supabase()
    logs = (
        db.table("activity_logs")
        .select("*")
        .order("created_at", desc=True)
        .limit(500)
        .execute()
        .data
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "action", "user_id", "actor_email", "target_type", "target_id", "details", "ip_address", "created_at"]
    )
    for l in logs:
        writer.writerow(
            [
                l.get("id"),
                l.get("action"),
                l.get("user_id") or "",
                l.get("actor_email") or "",
                l.get("target_type") or "",
                l.get("target_id") or "",
                l.get("details") or "",
                l.get("ip_address") or "",
                l.get("created_at"),
            ]
        )

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity_logs.csv"},
    )