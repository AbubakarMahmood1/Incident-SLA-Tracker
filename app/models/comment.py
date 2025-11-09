"""Comment model for incident discussions."""

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Comment(Base, UUIDMixin, TimestampMixin):
    """Comment model for incident discussions and updates."""

    __tablename__ = "comments"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Foreign Keys
    incident_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False
    )
    author_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="comments")
    author: Mapped["User"] = relationship("User", back_populates="comments")

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, incident_id={self.incident_id}, author_id={self.author_id})>"
