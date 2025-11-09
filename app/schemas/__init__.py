"""Schemas package for request/response validation."""

from app.schemas.attachment import (
    AttachmentCreate,
    AttachmentListResponse,
    AttachmentResponse,
    AttachmentWithUploader,
)
from app.schemas.comment import (
    CommentCreate,
    CommentListResponse,
    CommentResponse,
    CommentUpdate,
    CommentWithAuthor,
)
from app.schemas.incident import (
    IncidentAssign,
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    IncidentStatusUpdate,
    IncidentUpdate,
    IncidentWithDetails,
)
from app.schemas.sla import (
    SLAPauseRequest,
    SLAResponse,
    SLAResumeRequest,
    SLAUpdate,
)
from app.schemas.user import (
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenData",
    # Incident
    "IncidentCreate",
    "IncidentUpdate",
    "IncidentResponse",
    "IncidentWithDetails",
    "IncidentListResponse",
    "IncidentStatusUpdate",
    "IncidentAssign",
    # SLA
    "SLAResponse",
    "SLAUpdate",
    "SLAPauseRequest",
    "SLAResumeRequest",
    # Comment
    "CommentCreate",
    "CommentUpdate",
    "CommentResponse",
    "CommentWithAuthor",
    "CommentListResponse",
    # Attachment
    "AttachmentCreate",
    "AttachmentResponse",
    "AttachmentWithUploader",
    "AttachmentListResponse",
]
