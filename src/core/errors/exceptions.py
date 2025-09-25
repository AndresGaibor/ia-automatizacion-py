"""Enhanced error handling with custom exception hierarchies."""
from enum import Enum, auto
from typing import Optional, Dict, Any


class ErrorSeverity(Enum):
    """Standardized error severity levels."""
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class AcumbaMailError(Exception):
    """Base exception for Acumbamail automation."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.severity = severity
        self.context = context or {}
        self.cause = cause

    def __str__(self):
        base_msg = super().__str__()
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base_msg} (Context: {context_str})"
        return base_msg


class ConfigurationError(AcumbaMailError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            context=context
        )


class AuthenticationError(AcumbaMailError):
    """Raised when authentication fails."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            context=context
        )


class APIError(AcumbaMailError):
    """Raised for API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        endpoint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        full_context = context or {}
        if status_code is not None:
            full_context['status_code'] = status_code
        if endpoint is not None:
            full_context['endpoint'] = endpoint

        severity = ErrorSeverity.HIGH if status_code and status_code >= 500 else ErrorSeverity.MEDIUM
        super().__init__(message, severity=severity, context=full_context)


class BrowserAutomationError(AcumbaMailError):
    """Raised for browser automation related errors."""

    def __init__(
        self,
        message: str,
        page_url: Optional[str] = None,
        selector: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        full_context = context or {}
        if page_url:
            full_context['page_url'] = page_url
        if selector:
            full_context['selector'] = selector

        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            context=full_context
        )


class DataProcessingError(AcumbaMailError):
    """Raised for data processing and validation errors."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        row_number: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        full_context = context or {}
        if file_path:
            full_context['file_path'] = file_path
        if row_number is not None:
            full_context['row_number'] = row_number

        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            context=full_context
        )


class ValidationError(AcumbaMailError):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        full_context = context or {}
        if field_name:
            full_context['field_name'] = field_name
        if field_value is not None:
            full_context['field_value'] = field_value

        super().__init__(
            message,
            severity=ErrorSeverity.LOW,
            context=full_context
        )