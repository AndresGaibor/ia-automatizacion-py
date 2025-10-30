"""
Custom exceptions for authentication and session management.

This module provides specific exception types for different authentication
failure scenarios to enable better error handling and recovery.
"""


class AuthenticationError(Exception):
    """Base exception for all authentication-related errors."""
    pass


class CookiePopupError(AuthenticationError):
    """Cookie popup detected but couldn't be handled properly."""

    def __init__(self, message="Cookie popup detected but couldn't be dismissed"):
        super().__init__(message)
        self.message = message


class SessionExpiredError(AuthenticationError):
    """Session validation failed - user needs to re-authenticate."""

    def __init__(self, message="Session has expired and requires re-authentication"):
        super().__init__(message)
        self.message = message


class AuthenticationFailedError(AuthenticationError):
    """Login failed after maximum retry attempts."""

    def __init__(self, message="Authentication failed after maximum retries"):
        super().__init__(message)
        self.message = message


class SessionSaveError(AuthenticationError):
    """Failed to save or load session state properly."""

    def __init__(self, message="Failed to save session state"):
        super().__init__(message)
        self.message = message


class URLRedirectError(AuthenticationError):
    """Unexpected URL redirect detected (likely to login page)."""

    def __init__(self, current_url: str, expected_url: str = None):
        message = f"Unexpected redirect to {current_url}"
        if expected_url:
            message += f" (expected {expected_url})"
        super().__init__(message)
        self.current_url = current_url
        self.expected_url = expected_url
        self.message = message