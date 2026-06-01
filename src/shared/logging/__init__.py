"""Shared logging utilities."""

from typing import Any, Dict, Optional


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
            return logging.getLogger("acumba_automation")


def load_config(defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Shim mínimo para compatibilidad de tests"""
    try:
        from src.core.config.settings import load_config as core_load_config

        return core_load_config(defaults or {})
    except Exception:
        return defaults or {}


__all__ = ["get_logger", "load_config"]
