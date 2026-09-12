"""Bridges NextAuth sessions (frontend) to FastAPI.

NextAuth signs a compact HS256 JWT with `AUTH_SHARED_SECRET` after a
successful Google/Discord/Apple sign-in (see frontend/src/lib/auth.ts —
the `jwt` callback mints it and exposes it on `session.backendToken`). The
frontend sends it as `Authorization: Bearer <token>` on every API call, and
`get_current_user` below verifies it and lazily provisions the local User
row — there is no separate registration step.

This is deliberately NOT NextAuth's own encrypted session cookie; that
format is provider-internal (JWE, A256CBC-HS512) and awkward to verify
from a different stack. A second, small, plainly-verifiable JWT is the
standard way to bridge NextAuth to an external backend.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload:
    def __init__(self, sub: str, email: str, name: str, provider: str, picture: str | None):
        self.sub = sub
        self.email = email
        self.name = name
        self.provider = provider
        self.picture = picture


def decode_bridge_token(token: str) -> TokenPayload:
    try:
        claims: dict[str, Any] = jwt.decode(token, settings.auth_shared_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    for field in ("sub", "email", "provider"):
        if field not in claims:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token missing '{field}'")

    return TokenPayload(
        sub=claims["sub"],
        email=claims["email"],
        name=claims.get("name") or claims["email"].split("@")[0],
        provider=claims["provider"],
        picture=claims.get("picture"),
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    payload = decode_bridge_token(credentials.credentials)

    user = (
        db.query(User)
        .filter(User.auth_provider == payload.provider, User.auth_provider_id == payload.sub)
        .first()
    )
    needs_commit = False
    if user is None:
        # First sign-in with this provider identity — try to merge into an
        # existing account by email, otherwise provision a new one.
        user = db.query(User).filter(User.email == payload.email).first()
        if user is None:
            user = User(
                email=payload.email,
                name=payload.name,
                avatar_url=payload.picture,
                auth_provider=payload.provider,
                auth_provider_id=payload.sub,
            )
            db.add(user)
        else:
            user.auth_provider = payload.provider
            user.auth_provider_id = payload.sub
        needs_commit = True

    should_be_staff = payload.email.lower() in settings.staff_email_set
    if user.is_staff != should_be_staff:
        user.is_staff = should_be_staff
        needs_commit = True

    if needs_commit:
        db.commit()
        db.refresh(user)

    return user


def issue_dev_token(sub: str, email: str, name: str, provider: str = "dev") -> str:
    """Only used by tests / local `scripts/dev_login.py` — mints a token the
    same shape NextAuth produces, without needing a real OAuth round trip."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": sub,
        "email": email,
        "name": name,
        "provider": provider,
        "iat": now,
        "exp": now + timedelta(days=1),
    }
    return jwt.encode(claims, settings.auth_shared_secret, algorithm=settings.jwt_algorithm)
