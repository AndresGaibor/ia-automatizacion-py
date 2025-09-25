"""Custom exceptions for the Acumbamail automation system."""

from .exceptions import (
    AcumbaMailError,
    ConfigurationError,
    AuthenticationError,
    APIError,
    BrowserAutomationError,
    DataProcessingError,
    ValidationError,
    ErrorSeverity
)

__all__ = [
    'AcumbaMailError',
    'ConfigurationError',
    'AuthenticationError',
    'APIError',
    'BrowserAutomationError',
    'DataProcessingError',
    'ValidationError',
    'ErrorSeverity'
]