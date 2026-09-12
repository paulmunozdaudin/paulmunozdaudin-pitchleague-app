import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Platform-level staff access (the system admin panel), distinct from
    # being a league's admin — see core/security.py, bootstrapped from
    # STAFF_EMAILS since there's no in-app role-granting UI.
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)

    # Identity of the OAuth provider that created this account (google |
    # discord | apple). Bridged in from the NextAuth session — see
    # docs/ARCHITECTURE.md#auth.
    auth_provider: Mapped[str] = mapped_column(String(20))
    auth_provider_id: Mapped[str] = mapped_column(String(255))

    def __repr__(self) -> str:  # pragma: no cover
        return f"User(id={self.id}, email={self.email!r})"
