"""Shared logging utilities."""

# Import from the legacy logger module for backward compatibility
try:
    from .legacy_logger import get_logger
except ImportError:
    try:
        from ...logger import get_logger
    except ImportError:
        from src.logger import get_logger

__all__ = ['get_logger']