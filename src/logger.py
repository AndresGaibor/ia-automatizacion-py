"""
Wrapper de compatibilidad - redirige a shared/logging/logger.py.

Este archivo existe solo para mantener compatibilidad con imports antiguos.
El código fuente real está en src/shared/logging/logger.py.
"""

import os
import sys
from pathlib import Path

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

# Re-exportar todo desde shared/logging/logger
from .shared.logging.logger import (
    LogLevel,
    ErrorSeverity,
    PerformanceLogger,
    get_logger,
    timer,
)

__all__ = [
    "LogLevel",
    "ErrorSeverity",
    "PerformanceLogger",
    "get_logger",
    "timer",
]
