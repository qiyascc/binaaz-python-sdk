from __future__ import annotations

from typing import Any, Optional


class BinaAzError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(BinaAzError):
    pass


class InvalidRequestError(BinaAzError, ValueError):
    pass


class TransportError(BinaAzError):
    def __init__(self, message: str, *, path: str = "") -> None:
        super().__init__(message)
        self.path = path


class NotSentError(TransportError):
    pass


class OutcomeUnknownError(TransportError):
    def __init__(self, message: str, *, status_code: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.status_code = status_code


class APIError(BinaAzError):
    def __init__(self, message: str, *, status_code: int = 0, body: Any = None, path: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.path = path

    def __str__(self) -> str:
        return f"[{self.status_code}] {self.message}" if self.status_code else self.message


class BlockedError(APIError):
    pass


class BadRequestError(APIError):
    pass


class AuthenticationError(APIError):
    pass


class NotFoundError(APIError):
    pass


class RateLimitError(APIError):
    def __init__(self, message: str, *, retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(APIError):
    pass


class GraphQLError(BadRequestError):
    def __init__(self, message: str, *, errors: Any = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.errors = list(errors or [])


class ItemError(BadRequestError):
    def __init__(self, message: str, *, status: Optional[str] = None, errors: Any = None,
                 locked_until: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.status = status
        self.errors = list(errors or [])
        self.locked_until = locked_until


class NotSupportedError(BinaAzError):
    pass


class CodeRejectedError(BadRequestError):
    pass


def for_status(status: int) -> type[APIError]:
    if status in (401, 403, 419):
        return AuthenticationError
    if status == 404:
        return NotFoundError
    if status == 429:
        return RateLimitError
    if status >= 500:
        return ServerError
    if status >= 400:
        return BadRequestError
    return APIError
