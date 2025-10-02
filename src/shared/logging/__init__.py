"""Shared logging utilities."""

# Import from the logger module
try:
    from .logger import get_logger
except ImportError:
    # Fallback for different import contexts
    try:
        from src.shared.logging.logger import get_logger
    except ImportError:
        # Last resort - create a basic logger
        import logging
        def get_logger():
            return logging.getLogger('acumba_automation')

__all__ = ['get_logger']