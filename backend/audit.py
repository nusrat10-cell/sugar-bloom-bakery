from fastapi import Request
from database import get_supabase


def log_action(
    action: str,
    user_id: str | None = None,
    actor_email: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: str | None = None,
    request: Request | None = None,
) -> None:
    try:
        db = get_supabase()
        ip_address = request.client.host if request and request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown") if request else "unknown"

        db.table("activity_logs").insert(
            {
                "user_id": user_id,
                "actor_email": actor_email,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "details": details,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        ).execute()
    except Exception:
        # Avoid breaking primary API flows if logging encounters a transient issue
        pass