"""
Módulo de compatibilidad para structured_logger.py.
Redirige las funciones de logging estructurado al PerformanceLogger existente.
"""

import time
from typing import Optional
from .logger import get_logger

_logger = None


def _get_logger():
    global _logger
    if _logger is None:
        _logger = get_logger()
    return _logger


# --- Funciones de logging compatibles con structured_logger.py ---

def log_success(msg: str, **kwargs):
    """Log de éxito"""
    _get_logger().success(msg)


def log_error(msg: str, **kwargs):
    """Log de error"""
    _get_logger().error(msg)


def log_warning(msg: str, **kwargs):
    """Log de advertencia"""
    _get_logger().warning(msg)


def log_info(msg: str, **kwargs):
    """Log de información"""
    _get_logger().info(msg)


def log_performance(operation: str, elapsed: float, **kwargs):
    """Log de performance con métricas"""
    _get_logger().info(f"⏱️ {operation} - {elapsed:.2f}s")


def log_data_extraction(data_type: str, count: int, source: str = "", **kwargs):
    """Log de extracción de datos"""
    _get_logger().log_data_extraction(data_type, count, source)


def log_api_call(endpoint: str, method: str = "GET", status_code: Optional[int] = None, **kwargs):
    """Log de llamadas a API"""
    _get_logger().info(f"API: {method} {endpoint}", endpoint=endpoint, method=method, status_code=status_code)


def log_file_operation(operation: str, file_path: str, size_bytes: int = 0, **kwargs):
    """Log de operaciones de archivos"""
    _get_logger().log_file_operation(operation, file_path, size_bytes)


def log_browser_action(action: str, target: str = "", **kwargs):
    """Log de acciones del navegador"""
    _get_logger().log_browser_action(action, target)


def log_checkpoint(checkpoint: str, progress: str = "", **kwargs):
    """Log de checkpoints"""
    _get_logger().log_checkpoint(checkpoint, progress)


def log_page_visit(url: str, wait_time: float = 0, **kwargs):
    """Log de navegación de páginas"""
    _get_logger().log_page_navigation(url, wait_time)


def log_batch_summary(operation_type: str, total_items: int, success_count: int,
                      error_count: int, total_time: float, **kwargs):
    """Log de resumen de operaciones por lotes"""
    success_rate = (success_count / total_items * 100) if total_items > 0 else 0
    avg_time = total_time / total_items if total_items > 0 else 0
    _get_logger().info(
        f"RESUMEN {operation_type}: {success_count}/{total_items} exitosos "
        f"({success_rate:.1f}%) en {total_time:.2f}s (promedio: {avg_time:.2f}s/item)"
    )


# --- Performance tracking ---
_timers: dict = {}


def start_timer(operation: str) -> None:
    """Inicia un timer para una operación"""
    _timers[operation] = time.time()


def end_timer(operation: str, **extra_context) -> float:
    """Termina un timer y registra el tiempo transcurrido"""
    if operation not in _timers:
        log_warning(f"Timer no encontrado para operación: {operation}")
        return 0.0
    elapsed = time.time() - _timers[operation]
    del _timers[operation]
    log_performance(operation, elapsed, **extra_context)
    return elapsed


def timer_decorator(operation_name: str):
    """Decorador para medir automáticamente el tiempo de una función"""
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_timer(operation_name, function=func.__name__)
        return wrapper
    return decorator


class log_operation:
    """Context manager para logear operaciones con timing automático"""

    def __init__(self, operation_name: str, **context):
        self.operation_name = operation_name
        self.context = context
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        log_info(f"Iniciando {self.operation_name}", **self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            elapsed = time.time() - self.start_time
            if exc_type is None:
                log_success(f"Completado {self.operation_name}",
                            elapsed_seconds=elapsed, **self.context)
            else:
                log_error(f"Error en {self.operation_name}: {exc_val}",
                          elapsed_seconds=elapsed, error_type=exc_type.__name__, **self.context)


def get_structured_logger():
    """Obtiene el logger - shim de compatibilidad"""
    return _get_logger()


__all__ = [
    "log_success", "log_error", "log_warning", "log_info",
    "log_performance", "log_data_extraction", "log_api_call",
    "log_file_operation", "log_browser_action", "log_checkpoint",
    "log_page_visit", "log_batch_summary",
    "start_timer", "end_timer", "timer_decorator",
    "log_operation", "get_structured_logger",
]
