"""Attachment schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AttachmentBase(BaseModel):
    """Base attachment schema."""

    filename: str
    file_size: int
    mime_type: str


class AttachmentCreate(AttachmentBase):
    """Schema for creating an attachment."""

    file_path: str
    incident_id: UUID


class AttachmentInDB(AttachmentBase):
    """Schema for attachment in database."""

    id: UUID
    file_path: str
    incident_id: UUID
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AttachmentResponse(AttachmentInDB):
    """Schema for attachment response."""

    pass


class AttachmentWithUploader(AttachmentInDB):
    """Schema for attachment with uploader details."""

    uploader: "UserResponse | None" = None

    class Config:
        from_attributes = True


class AttachmentListResponse(BaseModel):
    """Schema for paginated attachment list."""

    items: list[AttachmentWithUploader]
    total: int
    page: int
    page_size: int
    pages: int


# Import to avoid circular import issues
from app.schemas.user import UserResponse  # noqa: E402

AttachmentWithUploader.model_rebuild()
