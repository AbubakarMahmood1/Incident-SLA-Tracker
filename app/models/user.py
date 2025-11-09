"""User model for authentication and assignment."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """User model for system users."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    reported_incidents: Mapped[list["Incident"]] = relationship(
        "Incident", back_populates="reporter", foreign_keys="[Incident.reporter_id]"
    )
    assigned_incidents: Mapped[list["Incident"]] = relationship(
        "Incident", back_populates="assignee", foreign_keys="[Incident.assignee_id]"
    )
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="author")
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="uploaded_by_user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
