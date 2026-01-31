#!/usr/bin/env python3
"""
Unified exception handling module for the application.

This module defines custom exceptions that can be used throughout the application
for consistent error handling and API responses.
"""

from typing import Any


class AppException(Exception):
    """Base exception class for application-specific errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to a dictionary for API responses."""
        result = {
            "success": False,
            "message": self.message,
            "error_code": self.error_code,
        }
        if self.details:
            result["details"] = self.details
        return result


# Authentication Exceptions
class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class TokenExpiredError(AuthenticationError):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, error_code="TOKEN_EXPIRED")


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, error_code="INVALID_TOKEN")


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""

    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(message, error_code="INVALID_CREDENTIALS")


# Authorization Exceptions
class AuthorizationError(AppException):
    """Raised when user lacks permission."""

    def __init__(self, message: str = "Permission denied", **kwargs):
        super().__init__(message, status_code=403, **kwargs)


class RateLimitExceededError(AuthorizationError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, error_code="RATE_LIMIT_EXCEEDED", details=details)


class AccountLockedError(AuthorizationError):
    """Raised when account is locked due to too many failed attempts."""

    def __init__(
        self,
        message: str = "Account temporarily locked",
        lockout_remaining: int | None = None,
    ):
        details = {"lockout_remaining_seconds": lockout_remaining} if lockout_remaining else {}
        super().__init__(message, error_code="ACCOUNT_LOCKED", details=details)


# Resource Exceptions
class ResourceNotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: str | None = None,
        resource_id: str | None = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, status_code=404, details=details)


class AccountNotFoundError(ResourceNotFoundError):
    """Raised when an email account is not found."""

    def __init__(self, email: str):
        super().__init__(
            message=f"Account not found: {email}",
            resource_type="account",
            resource_id=email,
        )


class EmailNotFoundError(ResourceNotFoundError):
    """Raised when an email message is not found."""

    def __init__(self, message_id: str):
        super().__init__(
            message=f"Email not found: {message_id}",
            resource_type="email",
            resource_id=message_id,
        )


# IMAP Exceptions
class IMAPError(AppException):
    """Base exception for IMAP-related errors."""

    def __init__(self, message: str = "IMAP operation failed", **kwargs):
        super().__init__(message, status_code=502, **kwargs)


class IMAPConnectionError(IMAPError):
    """Raised when IMAP connection fails."""

    def __init__(self, message: str = "Failed to connect to IMAP server"):
        super().__init__(message, error_code="IMAP_CONNECTION_FAILED")


class IMAPAuthenticationError(IMAPError):
    """Raised when IMAP authentication fails."""

    def __init__(self, message: str = "IMAP authentication failed"):
        super().__init__(message, error_code="IMAP_AUTH_FAILED")


class TokenRefreshError(IMAPError):
    """Raised when OAuth token refresh fails."""

    def __init__(self, message: str = "Failed to refresh access token"):
        super().__init__(message, error_code="TOKEN_REFRESH_FAILED")


# Database Exceptions
class DatabaseError(AppException):
    """Base exception for database-related errors."""

    def __init__(self, message: str = "Database operation failed", **kwargs):
        super().__init__(message, status_code=500, **kwargs)


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(self, message: str = "Failed to connect to database"):
        super().__init__(message, error_code="DB_CONNECTION_FAILED")


class DuplicateEntryError(DatabaseError):
    """Raised when trying to create a duplicate entry."""

    def __init__(self, message: str = "Entry already exists"):
        super().__init__(message, status_code=409, error_code="DUPLICATE_ENTRY")


# Validation Exceptions
class ValidationError(AppException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: str | None = None,
        **kwargs,
    ):
        details = {"field": field} if field else {}
        super().__init__(message, status_code=422, details=details, **kwargs)


class InvalidEmailFormatError(ValidationError):
    """Raised when email format is invalid."""

    def __init__(self, email: str):
        super().__init__(
            message=f"Invalid email format: {email}",
            field="email",
            error_code="INVALID_EMAIL_FORMAT",
        )


class ConfigurationError(AppException):
    """Raised when there's a configuration error."""

    def __init__(self, message: str = "Configuration error", **kwargs):
        super().__init__(message, status_code=500, **kwargs)


# Service Exceptions
class ServiceUnavailableError(AppException):
    """Raised when a service is temporarily unavailable."""

    def __init__(self, message: str = "Service temporarily unavailable", **kwargs):
        super().__init__(message, status_code=503, **kwargs)


class ExternalServiceError(AppException):
    """Raised when an external service call fails."""

    def __init__(
        self,
        message: str = "External service error",
        service_name: str | None = None,
        **kwargs,
    ):
        details = {"service": service_name} if service_name else {}
        super().__init__(message, status_code=502, details=details, **kwargs)
