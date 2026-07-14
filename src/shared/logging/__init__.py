"""Shared logging utilities."""

from typing import Any, Dict, Optional

from .logger import get_logger


def load_config(defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Shim mínimo para compatibilidad de tests"""
    try:
        from src.core.config.settings import load_config as core_load_config
        return core_load_config(defaults or {})
    except Exception:
        return defaults or {}


__all__ = ["get_logger", "load_config"]
