import logging
import structlog
from pythonjsonlogger import jsonlogger
from colorama import Fore, Style, init as colorama_init
from rich.console import Console
from rich.logging import RichHandler
import os
import sys
import time
from functools import wraps
from typing import Optional, Dict, Any
from datetime import datetime

colorama_init(autoreset=True)
console = Console()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "dev")  # 'dev' or 'json'

# --- Performance tracking ---
_timers: Dict[str, float] = {}

# --- Handlers ---
stream_handler = RichHandler(console=console, show_time=True, show_level=True, show_path=False)
stream_handler.setLevel(LOG_LEVEL)

json_handler = logging.StreamHandler(sys.stdout)
json_handler.setLevel(LOG_LEVEL)
json_formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s %(module)s %(funcName)s %(lineno)d"
)
json_handler.setFormatter(json_formatter)

# --- Logger config ---
logging.basicConfig(
    level=LOG_LEVEL,
    handlers=[stream_handler if LOG_FORMAT == "dev" else json_handler],
    format="%(message)s"
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("acumba_structured")

# --- Performance tracking functions ---
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

# --- Logging helpers with context ---
def log_success(msg: str, **kwargs):
    """Log de éxito con contexto estructurado"""
    logger.info(f"✅ {Fore.GREEN}{msg}{Style.RESET_ALL}", **kwargs)

def log_error(msg: str, **kwargs):
    """Log de error con contexto estructurado"""
    logger.error(f"❌ {Fore.RED}{msg}{Style.RESET_ALL}", **kwargs)

def log_warning(msg: str, **kwargs):
    """Log de advertencia con contexto estructurado"""
    logger.warning(f"⚠️ {Fore.YELLOW}{msg}{Style.RESET_ALL}", **kwargs)

def log_info(msg: str, **kwargs):
    """Log de información con contexto estructurado"""
    logger.info(f"ℹ️ {msg}", **kwargs)

def log_performance(operation: str, elapsed: float, **kwargs):
    """Log de performance con métricas"""
    # Determinar color basado en tiempo
    if elapsed < 1.0:
        color = Fore.GREEN
        grade = "RÁPIDO"
    elif elapsed < 5.0:
        color = Fore.YELLOW
        grade = "NORMAL"
    else:
        color = Fore.RED
        grade = "LENTO"
    
    logger.info(f"⏱️ {color}{operation} - {elapsed:.2f}s [{grade}]{Style.RESET_ALL}", 
               operation=operation, elapsed_seconds=elapsed, performance_grade=grade, **kwargs)

def log_page_visit(url: str, wait_time: float = 0, **kwargs):
    """Log de navegación de páginas"""
    logger.info(f"🔗 NAVEGACIÓN: {url} - Espera: {wait_time:.2f}s", 
               url=url, wait_time_seconds=wait_time, **kwargs)

def log_data_extraction(data_type: str, count: int, source: str = "", **kwargs):
    """Log de extracción de datos con métricas"""
    source_str = f" desde {source}" if source else ""
    logger.info(f"📊 DATOS: Extraídos {count} de {data_type}{source_str}", 
               data_type=data_type, count=count, source=source, **kwargs)

def log_api_call(endpoint: str, method: str = "GET", status_code: Optional[int] = None, **kwargs):
    """Log de llamadas a API"""
    status_str = f" [{status_code}]" if status_code else ""
    logger.info(f"🌐 API: {method} {endpoint}{status_str}", 
               endpoint=endpoint, method=method, status_code=status_code, **kwargs)

def log_file_operation(operation: str, file_path: str, size_bytes: int = 0, **kwargs):
    """Log de operaciones de archivos"""
    size_str = f" ({size_bytes} bytes)" if size_bytes > 0 else ""
    logger.info(f"📁 ARCHIVO: {operation} - {file_path}{size_str}", 
               operation=operation, file_path=file_path, size_bytes=size_bytes, **kwargs)

def log_browser_action(action: str, target: str = "", **kwargs):
    """Log de acciones del navegador"""
    target_str = f" en '{target}'" if target else ""
    logger.info(f"🌐 BROWSER: {action}{target_str}", 
               action=action, target=target, **kwargs)

def log_checkpoint(checkpoint: str, progress: str = "", **kwargs):
    """Log de checkpoints importantes"""
    progress_str = f" - {progress}" if progress else ""
    logger.info(f"📍 CHECKPOINT: {checkpoint}{progress_str}", 
               checkpoint=checkpoint, progress=progress, **kwargs)

def log_batch_summary(operation_type: str, total_items: int, success_count: int, 
                     error_count: int, total_time: float, **kwargs):
    """Log de resumen de operaciones por lotes"""
    success_rate = (success_count / total_items * 100) if total_items > 0 else 0
    avg_time = total_time / total_items if total_items > 0 else 0
    
    logger.info(f"📊 RESUMEN {operation_type}: {success_count}/{total_items} exitosos "
               f"({success_rate:.1f}%) en {total_time:.2f}s (promedio: {avg_time:.2f}s/item)", 
               operation_type=operation_type, total_items=total_items, 
               success_count=success_count, error_count=error_count,
               success_rate=success_rate, total_time=total_time, 
               avg_time_per_item=avg_time, **kwargs)

# --- Context managers ---
class log_operation:
    """Context manager para logear operaciones con timing automático"""
    def __init__(self, operation_name: str, **context):
        self.operation_name = operation_name
        self.context = context
        self.start_time: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        log_info(f"🚀 Iniciando {self.operation_name}", **self.context)
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

# --- Convenience functions for compatibility ---
def get_structured_logger():
    """Obtiene el logger estructurado configurado"""
    return logger

# --- Examples: ---
# log_success("Operación completada", user="andres", items_processed=150)
# log_error("Error de conexión", endpoint="/api/campaigns", retry_count=3)
# log_performance("procesamiento_campañas", 45.2, campaigns_processed=10)
# 
# with log_operation("autenticación", user="test@example.com"):
#     # código de autenticación
#     pass
#
# @timer_decorator("procesamiento_datos")
# def procesar_datos():
#     # función que será cronometrada automáticamente
#     pass
