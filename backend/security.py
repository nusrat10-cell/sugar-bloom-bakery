from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import bcrypt
import jwt
from config import get_settings

settings = get_settings()


def _peppered_secret(password: str) -> bytes:
    peppered = f"{password}{settings.PASSWORD_PEPPER}".encode("utf-8")
    # bcrypt has a 72-byte input limit; SHA-256 pre-hash keeps full entropy safely
    return hashlib.sha256(peppered).hexdigest().encode("utf-8")


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(_peppered_secret(password), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not plain_password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            _peppered_secret(plain_password),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(subject: str, role: str, username: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "role": role,
        "username": username,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()