"""
Sistema de logging avanzado para Acumba Automation
Implementa logging estructurado con JSON, logs por funcionalidad y mejores prácticas 2025
"""

import logging
import logging.handlers
import json
import time
import uuid
import os
import threading
from datetime import datetime
from typing import Dict, Optional, Any, Callable, List
from functools import wraps
from pathlib import Path
import traceback
import contextlib

try:
    from playwright.sync_api import Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Page = None


class JSONFormatter(logging.Formatter):
    """Formateador JSON para logs estructurados"""

    def __init__(self):
        super().__init__()

    def format(self, record):
        """Convierte el log record a formato JSON estructurado"""

        # Campos base del log
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": threading.current_thread().name,
        }

        # Agregar campos personalizados si existen
        if hasattr(record, 'operation_id'):
            log_entry['operation_id'] = record.operation_id

        if hasattr(record, 'duration'):
            log_entry['duration_ms'] = record.duration

        if hasattr(record, 'context'):
            log_entry['context'] = record.context

        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type

        if hasattr(record, 'stack_trace'):
            log_entry['stack_trace'] = record.stack_trace

        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id

        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id

        # Información adicional para errores
        if record.exc_info and record.exc_info[0] is not None:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class OperationContext:
    """Contexto para operaciones que permite tracking completo"""

    def __init__(self, operation_name: str, logger, context: Dict[str, Any] = None, page: 'Page' = None):
        self.operation_name = operation_name
        self.operation_id = str(uuid.uuid4())[:8]
        self.logger = logger
        self.context = context or {}
        self.start_time = None
        self.page = page  # Página de Playwright para screenshots

    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(
            f"🚀 INICIO: {self.operation_name}",
            extra={
                'operation_id': self.operation_id,
                'context': self.context
            }
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000  # ms

        if exc_type is None:
            self.logger.info(
                f"✅ COMPLETADO: {self.operation_name}",
                extra={
                    'operation_id': self.operation_id,
                    'duration': duration,
                    'context': self.context
                }
            )
        else:
            # Capturar screenshot si hay error y página disponible
            screenshot_path = None
            if self.page and PLAYWRIGHT_AVAILABLE:
                try:
                    # Usar el método del logger para capturar screenshot
                    screenshot_path = self.logger._capture_error_screenshot(
                        self.page, self.operation_name, self.operation_id
                    )
                except Exception:
                    pass  # No fallar por screenshot

            extra_data = {
                'operation_id': self.operation_id,
                'duration': duration,
                'context': self.context,
                'error_type': exc_type.__name__,
                'stack_trace': traceback.format_exc()
            }

            if screenshot_path:
                extra_data['screenshot_path'] = screenshot_path

            self.logger.error(
                f"❌ ERROR: {self.operation_name} - {exc_val}",
                extra=extra_data
            )

    def log_progress(self, message: str, current: int = None, total: int = None):
        """Log de progreso dentro de la operación"""
        extra = {
            'operation_id': self.operation_id,
            'context': self.context
        }

        if current is not None and total is not None:
            percentage = (current / total) * 100 if total > 0 else 0
            message = f"📈 PROGRESO: {message} ({current}/{total} - {percentage:.1f}%)"
            extra['progress'] = {'current': current, 'total': total, 'percentage': percentage}
        else:
            message = f"📍 CHECKPOINT: {message}"

        self.logger.info(message, extra=extra)


class EnhancedLogger:
    """Logger avanzado con múltiples funcionalidades y logs estructurados"""

    def __init__(self, name: str, log_dir: str = None):
        self.name = name
        self.log_dir = Path(log_dir) if log_dir else self._get_default_log_dir()
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configurar logger principal
        self.logger = logging.getLogger(f"acumba.{name}")
        self.logger.setLevel(logging.DEBUG)

        # Evitar duplicación de handlers
        if not self.logger.handlers:
            self._setup_handlers()

        # Métricas de operaciones
        self.operation_metrics = {}
        self.session_id = str(uuid.uuid4())[:8]

    def _get_default_log_dir(self) -> Path:
        """Obtiene el directorio de logs por defecto"""
        try:
            from .utils import data_path
            return Path(data_path("logs"))
        except ImportError:
            project_root = Path(__file__).parent.parent
            return project_root / "data" / "logs"

    def _setup_handlers(self):
        """Configura los handlers de logging"""
        timestamp = datetime.now().strftime("%Y%m%d")

        # Handler para archivo específico de funcionalidad (JSON)
        json_file = self.log_dir / f"{self.name}_{timestamp}.json"
        json_handler = logging.handlers.RotatingFileHandler(
            json_file, maxBytes=50*1024*1024, backupCount=5
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(json_handler)

        # Handler para archivo de texto legible
        text_file = self.log_dir / f"{self.name}_{timestamp}.log"
        text_handler = logging.handlers.RotatingFileHandler(
            text_file, maxBytes=50*1024*1024, backupCount=5
        )
        text_handler.setLevel(logging.INFO)
        text_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-8s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        text_handler.setFormatter(text_formatter)
        self.logger.addHandler(text_handler)

        # Handler de consola (solo warnings y errores)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Handler para errores críticos (archivo separado)
        if self.name != "errors":  # Evitar recursión
            error_file = self.log_dir / f"errors_{timestamp}.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_file, maxBytes=10*1024*1024, backupCount=10
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(text_formatter)
            self.logger.addHandler(error_handler)

    def operation(self, operation_name: str, context: Dict[str, Any] = None, page: 'Page' = None) -> OperationContext:
        """Crea un contexto de operación para tracking completo"""
        return OperationContext(operation_name, self.logger, context, page)

    def debug(self, message: str, **kwargs):
        """Log de debug con contexto opcional"""
        self.logger.debug(message, extra=self._build_extra(**kwargs))

    def info(self, message: str, **kwargs):
        """Log de información con contexto opcional"""
        self.logger.info(message, extra=self._build_extra(**kwargs))

    def warning(self, message: str, **kwargs):
        """Log de warning con contexto opcional"""
        self.logger.warning(message, extra=self._build_extra(**kwargs))

    def error(self, message: str, error: Exception = None, page: 'Page' = None, **kwargs):
        """Log de error con información de excepción y screenshot opcional"""
        extra = self._build_extra(**kwargs)

        if error:
            extra['error_type'] = type(error).__name__
            extra['stack_trace'] = traceback.format_exc()

        # Capturar screenshot si se proporciona página
        if page and PLAYWRIGHT_AVAILABLE:
            screenshot_path = self._capture_error_screenshot(page, "error", extra.get('operation_id', 'unknown'))
            if screenshot_path:
                extra['screenshot_path'] = screenshot_path

        self.logger.error(message, extra=extra, exc_info=error is not None)

    def critical(self, message: str, error: Exception = None, page: 'Page' = None, **kwargs):
        """Log crítico con información de excepción y screenshot opcional"""
        extra = self._build_extra(**kwargs)

        if error:
            extra['error_type'] = type(error).__name__
            extra['stack_trace'] = traceback.format_exc()

        # Capturar screenshot si se proporciona página
        if page and PLAYWRIGHT_AVAILABLE:
            screenshot_path = self._capture_error_screenshot(page, "critical", extra.get('operation_id', 'unknown'))
            if screenshot_path:
                extra['screenshot_path'] = screenshot_path

        self.logger.critical(message, extra=extra, exc_info=error is not None)

    def _build_extra(self, **kwargs) -> Dict[str, Any]:
        """Construye información extra para el log"""
        extra = {
            'session_id': self.session_id
        }
        extra.update(kwargs)
        return extra

    def time_operation(self, operation_name: str, context: Dict[str, Any] = None):
        """Decorador para medir tiempo de operaciones"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.operation(operation_name, context):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def log_browser_action(self, action: str, target: str = "", context: Dict[str, Any] = None):
        """Log especializado para acciones del navegador"""
        message = f"🌐 BROWSER: {action}"
        if target:
            message += f" → {target}"

        self.info(message, context=context or {})

    def log_file_operation(self, operation: str, file_path: str, size: int = 0, context: Dict[str, Any] = None):
        """Log especializado para operaciones de archivos"""
        message = f"📁 FILE: {operation} → {file_path}"
        if size > 0:
            message += f" ({self._format_bytes(size)})"

        extra_context = {'file_path': file_path, 'operation': operation}
        if size > 0:
            extra_context['file_size'] = size

        if context:
            extra_context.update(context)

        self.info(message, context=extra_context)

    def log_data_extraction(self, data_type: str, count: int, source: str = "", context: Dict[str, Any] = None):
        """Log especializado para extracción de datos"""
        message = f"📊 DATA: Extraídos {count} registros de {data_type}"
        if source:
            message += f" desde {source}"

        extra_context = {
            'data_type': data_type,
            'count': count,
            'source': source
        }

        if context:
            extra_context.update(context)

        self.info(message, context=extra_context)

    def log_performance_metric(self, metric_name: str, value: float, unit: str = "ms", context: Dict[str, Any] = None):
        """Log de métricas de rendimiento"""
        message = f"⚡ METRIC: {metric_name} = {value:.2f}{unit}"

        extra_context = {
            'metric_name': metric_name,
            'metric_value': value,
            'metric_unit': unit
        }

        if context:
            extra_context.update(context)

        self.info(message, context=extra_context)

        # Almacenar métrica para análisis posterior
        if metric_name not in self.operation_metrics:
            self.operation_metrics[metric_name] = []
        self.operation_metrics[metric_name].append({
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        })

    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de métricas de rendimiento"""
        summary = {}

        for metric_name, values in self.operation_metrics.items():
            if values:
                metric_values = [v['value'] for v in values]
                summary[metric_name] = {
                    'count': len(metric_values),
                    'avg': sum(metric_values) / len(metric_values),
                    'min': min(metric_values),
                    'max': max(metric_values),
                    'total': sum(metric_values)
                }

        return summary

    def _format_bytes(self, bytes_size: int) -> str:
        """Formatea bytes en unidades legibles"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f}TB"

    def _capture_error_screenshot(self, page: 'Page', operation: str, operation_id: str) -> Optional[str]:
        """Captura screenshot cuando ocurre un error"""
        if not PLAYWRIGHT_AVAILABLE or not page:
            return None

        try:
            # Crear nombre de archivo único
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_{operation}_{operation_id}_{timestamp}.png"
            screenshot_path = self.log_dir / "screenshots" / filename

            # Crear directorio de screenshots si no existe
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            # Capturar screenshot
            page.screenshot(path=str(screenshot_path), full_page=True)

            # Log de la captura
            self.info(f"📸 Screenshot capturado por error: {filename}",
                     context={
                         "screenshot_path": str(screenshot_path),
                         "operation": operation,
                         "operation_id": operation_id,
                         "file_size": screenshot_path.stat().st_size if screenshot_path.exists() else 0
                     })

            return str(screenshot_path)

        except Exception as e:
            # No fallar el logging por un error de screenshot
            self.warning(f"No se pudo capturar screenshot: {e}",
                        context={"operation": operation, "operation_id": operation_id})
            return None

    def capture_screenshot(self, page: 'Page', name: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Captura screenshot manual con nombre personalizado"""
        if not PLAYWRIGHT_AVAILABLE or not page:
            self.warning("Screenshot no disponible - Playwright no está disponible o página es None")
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            screenshot_path = self.log_dir / "screenshots" / filename

            # Crear directorio si no existe
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            # Capturar screenshot
            page.screenshot(path=str(screenshot_path), full_page=True)

            size = screenshot_path.stat().st_size if screenshot_path.exists() else 0

            self.log_file_operation("Screenshot capturado", str(screenshot_path), size,
                                  context=context or {})

            return str(screenshot_path)

        except Exception as e:
            self.error(f"Error capturando screenshot {name}", error=e,
                      context=context or {})
            return None

    def log_browser_error(self, action: str, error: Exception, page: 'Page' = None, context: Dict[str, Any] = None):
        """Log especializado para errores del navegador con screenshot automático"""
        error_context = {
            "browser_action": action,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }

        if context:
            error_context.update(context)

        # Capturar screenshot del error
        screenshot_path = None
        if page and PLAYWRIGHT_AVAILABLE:
            try:
                screenshot_path = self._capture_error_screenshot(page, f"browser_{action}", str(uuid.uuid4())[:8])
                if screenshot_path:
                    error_context["screenshot_path"] = screenshot_path
            except Exception:
                pass  # No fallar por screenshot

        self.error(f"🌐 ERROR NAVEGADOR: {action} - {error}",
                  error=error, context=error_context)

    def log_operation_failure(self, operation: str, details: str, page: 'Page' = None, context: Dict[str, Any] = None):
        """Log para fallos de operaciones con captura automática"""
        failure_context = {
            "operation": operation,
            "failure_details": details
        }

        if context:
            failure_context.update(context)

        # Capturar screenshot del fallo
        screenshot_path = None
        if page and PLAYWRIGHT_AVAILABLE:
            screenshot_path = self._capture_error_screenshot(page, f"failure_{operation}", str(uuid.uuid4())[:8])
            if screenshot_path:
                failure_context["screenshot_path"] = screenshot_path

        self.error(f"💥 FALLO DE OPERACIÓN: {operation} - {details}",
                  context=failure_context)


class LoggerManager:
    """Gestor central de loggers para toda la aplicación"""

    _instance = None
    _loggers: Dict[str, EnhancedLogger] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_logger(self, name: str) -> EnhancedLogger:
        """Obtiene o crea un logger específico"""
        if name not in self._loggers:
            self._loggers[name] = EnhancedLogger(name)
        return self._loggers[name]

    def get_main_logger(self) -> EnhancedLogger:
        """Obtiene el logger principal"""
        return self.get_logger("main")

    def get_auth_logger(self) -> EnhancedLogger:
        """Obtiene el logger de autenticación"""
        return self.get_logger("auth")

    def get_browser_logger(self) -> EnhancedLogger:
        """Obtiene el logger del navegador"""
        return self.get_logger("browser")

    def get_crear_lista_logger(self) -> EnhancedLogger:
        """Obtiene el logger de crear lista"""
        return self.get_logger("crear_lista")

    def get_listar_campanias_logger(self) -> EnhancedLogger:
        """Obtiene el logger de listar campañas"""
        return self.get_logger("listar_campanias")

    def get_performance_logger(self) -> EnhancedLogger:
        """Obtiene el logger de rendimiento"""
        return self.get_logger("performance")

    def get_errors_logger(self) -> EnhancedLogger:
        """Obtiene el logger de errores"""
        return self.get_logger("errors")

    def shutdown_all(self):
        """Cierra todos los loggers de forma segura"""
        for logger in self._loggers.values():
            for handler in logger.logger.handlers:
                handler.close()
                logger.logger.removeHandler(handler)


# Instancia global del gestor
logger_manager = LoggerManager()

# Funciones de conveniencia para acceso rápido
def get_logger(name: str = "main") -> EnhancedLogger:
    """Obtiene un logger específico"""
    return logger_manager.get_logger(name)

def get_main_logger() -> EnhancedLogger:
    """Obtiene el logger principal"""
    return logger_manager.get_main_logger()

def get_auth_logger() -> EnhancedLogger:
    """Obtiene el logger de autenticación"""
    return logger_manager.get_auth_logger()

def get_browser_logger() -> EnhancedLogger:
    """Obtiene el logger del navegador"""
    return logger_manager.get_browser_logger()

def get_crear_lista_logger() -> EnhancedLogger:
    """Obtiene el logger de crear lista"""
    return logger_manager.get_crear_lista_logger()

def get_listar_campanias_logger() -> EnhancedLogger:
    """Obtiene el logger de listar campañas"""
    return logger_manager.get_listar_campanias_logger()

def get_performance_logger() -> EnhancedLogger:
    """Obtiene el logger de rendimiento"""
    return logger_manager.get_performance_logger()

def get_errors_logger() -> EnhancedLogger:
    """Obtiene el logger de errores"""
    return logger_manager.get_errors_logger()

# Decorador conveniente para operaciones
def log_operation(operation_name: str, logger_name: str = "main", context: Dict[str, Any] = None):
    """Decorador para logging automático de operaciones"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            with logger.operation(operation_name, context):
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Context manager para manejo de errores con logging
@contextlib.contextmanager
def log_errors(operation_name: str, logger_name: str = "main", reraise: bool = True):
    """Context manager para capturar y loggear errores"""
    logger = get_logger(logger_name)
    try:
        yield logger
    except Exception as e:
        logger.error(f"Error en {operation_name}", error=e)
        if reraise:
            raise