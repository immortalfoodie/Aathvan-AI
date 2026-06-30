"""Authentication service — password hashing and JWT management."""

from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
import bcrypt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.schemas.auth import SignupRequest


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def create_access_token(user_id: int) -> str:
    """Create a signed JWT for the given user."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Decode a JWT and return the user ID, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        return int(user_id) if user_id else None
    except (JWTError, ValueError):
        return None


def create_user(db: Session, data: SignupRequest) -> User:
    """Create a new user in the database."""
    hashed_pwd = hash_password(data.password) if data.password else None
    user = User(
        email=data.email,
        hashed_password=hashed_pwd,
        name=data.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def find_or_create_google_user(
    db: Session,
    google_id: str,
    email: str,
    name: str,
    access_token: str,
    refresh_token: str | None,
) -> User:
    """Find user by google_id, or match by email and link, or create a new user."""
    # 1. Match by Google ID
    user = db.query(User).filter(User.google_id == google_id).first()
    if user:
        # Update access and refresh tokens
        user.google_access_token = access_token
        if refresh_token:
            user.google_refresh_token = refresh_token
        db.commit()
        db.refresh(user)
        return user

    # 2. Match by email
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.google_id = google_id
        user.google_access_token = access_token
        if refresh_token:
            user.google_refresh_token = refresh_token
        db.commit()
        db.refresh(user)
        return user

    # 3. Create brand new user
    user = User(
        email=email,
        hashed_password=None,  # Google-only user, no standard password
        name=name,
        google_id=google_id,
        google_access_token=access_token,
        google_refresh_token=refresh_token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def link_google_account(
    db: Session,
    user: User,
    google_id: str,
    access_token: str,
    refresh_token: str | None,
) -> User:
    """Link Google OAuth columns to an existing authenticated User."""
    user.google_id = google_id
    user.google_access_token = access_token
    if refresh_token:
        user.google_refresh_token = refresh_token
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Validate credentials and return the user, or None."""
    user = db.query(User).filter(User.email == email).first()
    # Google-only users won't have a hashed_password
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Fetch a user by primary key."""
    return db.query(User).filter(User.id == user_id).first()

