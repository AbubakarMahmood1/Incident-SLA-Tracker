"""Application service errors mapped to stable API responses."""


class ServiceError(Exception):
    status_code = 400
    code = "service_error"


class NotFoundError(ServiceError):
    status_code = 404
    code = "not_found"


class ForbiddenError(ServiceError):
    status_code = 403
    code = "forbidden"


class ConflictError(ServiceError):
    status_code = 409
    code = "conflict"


class IdempotencyConflictError(ConflictError):
    code = "idempotency_conflict"


class InvalidTransitionError(ConflictError):
    code = "invalid_transition"
