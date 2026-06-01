"""Custom exceptions for the Acumbamail automation system."""

from .exceptions import (
    AcumbaMailError,
    ConfigurationError,
    AuthenticationError,
    APIError,
    BrowserAutomationError,
    BrowserError,  # Alias para compatibilidad
    DataProcessingError,
    ValidationError,
    ErrorSeverity,
)

__all__ = [
    "AcumbaMailError",
    "ConfigurationError",
    "AuthenticationError",
    "APIError",
    "BrowserAutomationError",
    "BrowserError",  # Alias para compatibilidad
    "DataProcessingError",
    "ValidationError",
    "ErrorSeverity",
]
