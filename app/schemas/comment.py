"""Comment schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CommentBase(BaseModel):
    """Base comment schema."""

    content: str = Field(..., min_length=1)
    is_internal: bool = Field(default=False)


class CommentCreate(CommentBase):
    """Schema for creating a comment."""

    pass


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""

    content: str | None = Field(None, min_length=1)
    is_internal: bool | None = None


class CommentInDB(CommentBase):
    """Schema for comment in database."""

    id: UUID
    incident_id: UUID
    author_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentResponse(CommentInDB):
    """Schema for comment response."""

    pass


class CommentWithAuthor(CommentInDB):
    """Schema for comment with author details."""

    author: "UserResponse | None" = None

    class Config:
        from_attributes = True


class CommentListResponse(BaseModel):
    """Schema for paginated comment list."""

    items: list[CommentWithAuthor]
    total: int
    page: int
    page_size: int
    pages: int


# Import to avoid circular import issues
from app.schemas.user import UserResponse  # noqa: E402

CommentWithAuthor.model_rebuild()
