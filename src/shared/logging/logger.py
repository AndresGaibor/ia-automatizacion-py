import logging
import time
from datetime import datetime
from functools import wraps
from typing import Dict, Optional, Any, Callable, List
from enum import Enum
import os
import signal
from collections import defaultdict, Counter

class LogLevel(Enum):
    """Niveles de logging con severidad"""
    TRACE = 1    # Debugging detallado
    DEBUG = 2    # Información de desarrollo
    INFO = 3     # Información general
    SUCCESS = 4  # Operaciones exitosas
    WARNING = 5  # Advertencias
    ERROR = 6    # Errores recuperables
    CRITICAL = 7 # Errores críticos

class ErrorSeverity(Enum):
    """Clasificación de severidad de errores"""
    EXPECTED = "expected"      # Errores esperados (cookies, límites)
    RECOVERABLE = "recoverable" # Errores que se pueden reintentar
    TECHNICAL = "technical"     # Errores técnicos (selectores, timeouts)
    CRITICAL = "critical"       # Errores que detienen el proceso

class PerformanceLogger:
    """Logger especializado mejorado para rendimiento y análisis inteligente"""

    def __init__(self, log_file: Optional[str] = None, verbose_level: int = 3):
        self.timings: Dict[str, float] = {}
        self.start_times: Dict[str, float] = {}
        self.operation_counts: Dict[str, int] = {}
        self.verbose_level = verbose_level  # 1=mínimo, 5=máximo

        # Nuevas estructuras para análisis inteligente
        self.error_patterns: Dict[str, int] = Counter()
        self.operation_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.ui_failures: Dict[str, int] = Counter()
        self.performance_baselines: Dict[str, float] = {}
        self.current_batch: Dict[str, Any] = {}
        self.heartbeat_interval = 10  # segundos entre heartbeats
        self.last_heartbeat: Dict[str, float] = {}
        
        self.logger = logging.getLogger('acumba_automation')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.WARNING)  # Only show warnings and errors in console
            self.logger.addHandler(console_handler)
            
            if log_file:
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

    # -------------------------------------------------------------
    # Passthrough API estilo logging.Logger para compatibilidad
    # Now supports structured logging with extra fields
    # -------------------------------------------------------------
    def debug(self, msg: str, *args, **kwargs) -> None:
        # Handle structured logging by extracting extra fields
        extra_fields = {k: v for k, v in kwargs.items() if k not in ['exc_info', 'stack_info', 'extra']}
        if extra_fields:
            # Only pass standard logging kwargs to the underlying logger
            standard_kwargs = {k: v for k, v in kwargs.items() if k in ['exc_info', 'stack_info', 'extra']}
            self.logger.debug(f"{msg} | {extra_fields}", *args, **standard_kwargs)
        else:
            self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        # Handle structured logging by extracting extra fields
        extra_fields = {k: v for k, v in kwargs.items() if k not in ['exc_info', 'stack_info', 'extra']}
        if extra_fields:
            # Only pass standard logging kwargs to the underlying logger
            standard_kwargs = {k: v for k, v in kwargs.items() if k in ['exc_info', 'stack_info', 'extra']}
            self.logger.info(f"{msg} | {extra_fields}", *args, **standard_kwargs)
        else:
            self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        # Handle structured logging by extracting extra fields
        extra_fields = {k: v for k, v in kwargs.items() if k not in ['exc_info', 'stack_info', 'extra']}
        if extra_fields:
            # Only pass standard logging kwargs to the underlying logger
            standard_kwargs = {k: v for k, v in kwargs.items() if k in ['exc_info', 'stack_info', 'extra']}
            self.logger.warning(f"{msg} | {extra_fields}", *args, **standard_kwargs)
        else:
            self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        # Handle structured logging by extracting extra fields
        extra_fields = {k: v for k, v in kwargs.items() if k not in ['exc_info', 'stack_info', 'extra']}
        if extra_fields:
            # Only pass standard logging kwargs to the underlying logger
            standard_kwargs = {k: v for k, v in kwargs.items() if k in ['exc_info', 'stack_info', 'extra']}
            self.logger.error(f"{msg} | {extra_fields}", *args, **standard_kwargs)
        else:
            self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        # Handle structured logging by extracting extra fields
        extra_fields = {k: v for k, v in kwargs.items() if k not in ['exc_info', 'stack_info', 'extra']}
        if extra_fields:
            # Only pass standard logging kwargs to the underlying logger
            standard_kwargs = {k: v for k, v in kwargs.items() if k in ['exc_info', 'stack_info', 'extra']}
            self.logger.critical(f"{msg} | {extra_fields}", *args, **standard_kwargs)
        else:
            self.logger.critical(msg, *args, **kwargs)

    def success(self, msg: str, *args, **kwargs) -> None:
        # Handle structured logging by extracting extra fields
        extra_fields = {k: v for k, v in kwargs.items() if k not in ['exc_info', 'stack_info', 'extra']}
        if extra_fields:
            # Only pass standard logging kwargs to the underlying logger
            standard_kwargs = {k: v for k, v in kwargs.items() if k in ['exc_info', 'stack_info', 'extra']}
            self.logger.info(f"✅ {msg} | {extra_fields}", *args, **standard_kwargs)
        else:
            self.logger.info(f"✅ {msg}", *args, **kwargs)
    
    def start_timer(self, operation: str, batch_key: Optional[str] = None) -> None:
        """Inicia el cronómetro para una operación con agrupación inteligente"""
        self.start_times[operation] = time.time()

        # Solo logear inicio si es operación importante o verbose_level alto
        if self.verbose_level >= 4 or any(keyword in operation.lower() for keyword in ['login', 'main', 'navegacion']):
            self.logger.info(f"⏱️ INICIO: {operation}")

        # Inicializar batch si se especifica
        if batch_key:
            if batch_key not in self.current_batch:
                self.current_batch[batch_key] = {
                    'operations': [],
                    'start_time': time.time(),
                    'errors': [],
                    'total_items': 0
                }
    
    def end_timer(self, operation: str, extra_info: str = "", batch_key: Optional[str] = None) -> float:
        """Termina el cronómetro con logging inteligente y agrupación"""
        if operation not in self.start_times:
            if self.verbose_level >= 3:
                self.logger.warning(f"⚠️ No se encontró tiempo de inicio para: {operation}")
            return 0.0

        elapsed = time.time() - self.start_times[operation]
        self.timings[operation] = elapsed
        self.operation_counts[operation] = self.operation_counts.get(operation, 0) + 1

        # Detectar degradación de performance
        self._check_performance_degradation(operation, elapsed)

        # Agregar a batch si se especifica
        if batch_key and batch_key in self.current_batch:
            self.current_batch[batch_key]['operations'].append({
                'operation': operation,
                'time': elapsed,
                'info': extra_info
            })
        else:
            # Logging individual solo para operaciones importantes o verbose alto
            if (elapsed > 5.0 or  # Operaciones lentas siempre se logean
                self.verbose_level >= 4 or
                any(keyword in operation.lower() for keyword in ['login', 'main', 'error', 'navegacion'])):

                count_info = f" (#{self.operation_counts[operation]})" if self.operation_counts[operation] > 1 else ""
                extra_str = f" - {extra_info}" if extra_info else ""
                self.logger.info(f"⏱️ FIN: {operation}{count_info} - Tiempo: {elapsed:.2f}s{extra_str}")

        del self.start_times[operation]
        return elapsed
    
    def time_operation(self, operation_name: str, extra_info: str = ""):
        """Decorador para medir automáticamente el tiempo de una función"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                self.start_timer(operation_name)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    self.end_timer(operation_name, extra_info)
            return wrapper
        return decorator
    
    def log_browser_action(self, action: str, target: str = "", extra_info: str = ""):
        """Registra acciones del navegador con contexto (reducido para operaciones repetitivas)"""
        # Solo logear acciones importantes o con verbose alto
        if (self.verbose_level >= 4 or
            any(keyword in action.lower() for keyword in ['login', 'error', 'fallback', 'retry'])):
            target_str = f" en '{target}'" if target else ""
            extra_str = f" - {extra_info}" if extra_info else ""
            self.logger.info(f"🌐 BROWSER: {action}{target_str}{extra_str}")
    
    def log_data_extraction(self, data_type: str, count: int, source: str = ""):
        """Registra extracciones de datos"""
        source_str = f" desde {source}" if source else ""
        self.logger.info(f"📊 DATOS: Extraídos {count} registros de {data_type}{source_str}")
    
    def log_error(self, operation: str, error: Exception, context: str = "", severity: ErrorSeverity = ErrorSeverity.TECHNICAL):
        """Registra errores con clasificación de severidad"""
        error_key = f"{operation}:{type(error).__name__}"
        self.error_patterns[error_key] += 1

        # Detectar patrones problemáticos
        if self.error_patterns[error_key] >= 3:
            self._detect_ui_changes(operation, str(error))

        context_str = f" - Contexto: {context}" if context else ""
        severity_icon = self._get_severity_icon(severity)

        self.logger.error(f"{severity_icon} ERROR [{severity.value}] en {operation}: {str(error)}{context_str}")
    
    def log_warning(self, operation: str, message: str, severity: ErrorSeverity = ErrorSeverity.EXPECTED):
        """Registra advertencias con clasificación"""
        severity_icon = self._get_severity_icon(severity)
        self.logger.warning(f"{severity_icon} WARNING [{severity.value}] en {operation}: {message}")
    
    def with_timeout(self, timeout_seconds: int = 300):
        """Decorador para aplicar timeout a operaciones que pueden colgarse"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                def timeout_handler(signum, frame):
                    self.log_error(func.__name__, Exception("Timeout"), f"Operación excedió {timeout_seconds}s")
                    raise TimeoutError(f"Operación {func.__name__} excedió timeout de {timeout_seconds} segundos")
                
                # Solo en sistemas Unix
                old_handler = None
                if hasattr(signal, 'SIGALRM'):
                    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout_seconds)
                
                try:
                    result = func(*args, **kwargs)
                    if hasattr(signal, 'SIGALRM') and old_handler is not None:
                        signal.alarm(0)  # Cancelar alarma
                        signal.signal(signal.SIGALRM, old_handler)
                    return result
                except TimeoutError:
                    if hasattr(signal, 'SIGALRM') and old_handler is not None:
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_handler)
                    raise
                except Exception:
                    if hasattr(signal, 'SIGALRM') and old_handler is not None:
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_handler)
                    raise
            return wrapper
        return decorator
    
    def log_success(self, operation: str, message: str = ""):
        """Registra operaciones exitosas"""
        msg_str = f" - {message}" if message else ""
        self.logger.info(f"✅ ÉXITO: {operation}{msg_str}")
    
    def log_progress(self, current: int, total: int, operation: str = ""):
        """Registra progreso con cálculo correcto y agrupación inteligente"""
        # Calcular porcentaje correctamente
        percentage = (current / total) * 100 if total > 0 else 0
        operation_str = f"{operation} - " if operation else ""

        # Solo logear progreso en intervalos (cada 10% o cada 5 items para listas pequeñas)
        should_log = (total <= 20 or  # Listas pequeñas: siempre
                     current == 1 or  # Primer item
                     current == total or  # Último item
                     current % max(1, total // 10) == 0 or  # Cada 10%
                     self.verbose_level >= 4)  # Modo verbose

        if should_log:
            self.logger.info(f"📈 PROGRESO: {operation_str}{current}/{total} ({percentage:.1f}%)")
    
    def log_page_navigation(self, url: str, wait_time: float = 0):
        """Registra navegación de páginas"""
        wait_str = f" - Tiempo de espera: {wait_time:.2f}s" if wait_time > 0 else ""
        self.logger.info(f"🔗 NAVEGACIÓN: {url}{wait_str}")
    
    def log_file_operation(self, operation: str, file_path: str, size: int = 0):
        """Registra operaciones de archivos"""
        size_str = f" ({size} bytes)" if size > 0 else ""
        self.logger.info(f"📁 ARCHIVO: {operation} - {file_path}{size_str}")
    
    def log_heartbeat(self, operation: str, details: str = ""):
        """Registra heartbeat inteligente (solo cuando es necesario)"""
        current_time = time.time()

        # Solo logear heartbeat si ha pasado suficiente tiempo desde el último
        if (operation not in self.last_heartbeat or
            current_time - self.last_heartbeat[operation] >= self.heartbeat_interval):

            self.last_heartbeat[operation] = current_time
            if self.verbose_level >= 3:  # Reducir heartbeats salvo en modo verbose
                details_str = f" - {details}" if details else ""
                self.logger.info(f"💓 HEARTBEAT: {operation}{details_str}")
    
    def log_checkpoint(self, checkpoint: str, progress: str = ""):
        """Registra checkpoint con filtrado inteligente"""
        # Solo checkpoints importantes o verbose alto
        if (self.verbose_level >= 4 or
            any(keyword in checkpoint.lower() for keyword in ['login', 'error', 'final', 'inicio'])):
            progress_str = f" - {progress}" if progress else ""
            self.logger.info(f"📍 CHECKPOINT: {checkpoint}{progress_str}")
    
    def start_batch_operation(self, batch_key: str, operation_type: str, total_items: int = 0):
        """Inicia una operación por lotes para agrupación de logs"""
        self.current_batch[batch_key] = {
            'type': operation_type,
            'operations': [],
            'start_time': time.time(),
            'errors': [],
            'total_items': total_items,
            'items_processed': 0
        }

    def end_batch_operation(self, batch_key: str) -> Dict[str, Any]:
        """Finaliza operación por lotes y genera resumen"""
        if batch_key not in self.current_batch:
            return {}

        batch = self.current_batch[batch_key]
        total_time = time.time() - batch['start_time']
        total_operations = len(batch['operations'])

        # Crear resumen estructurado
        summary = {
            'operation_type': batch['type'],
            'total_operations': total_operations,
            'total_time': total_time,
            'items_processed': batch.get('items_processed', 0),
            'avg_time_per_operation': total_time / max(1, total_operations),
            'errors': batch['errors'],
            'success_rate': (total_operations - len(batch['errors'])) / max(1, total_operations) * 100,
            'performance_grade': self._calculate_performance_grade(batch['type'], total_time, total_operations)
        }

        # Log resumen agrupado en lugar de logs individuales
        self.logger.info(f"📊 RESUMEN {batch['type']}: {total_operations} operaciones en {total_time:.1f}s "
                        f"(promedio: {summary['avg_time_per_operation']:.2f}s/op, éxito: {summary['success_rate']:.1f}%)")

        del self.current_batch[batch_key]
        return summary

    def _get_severity_icon(self, severity: ErrorSeverity) -> str:
        """Obtiene icono según severidad"""
        icons = {
            ErrorSeverity.EXPECTED: "ℹ️",
            ErrorSeverity.RECOVERABLE: "⚠️",
            ErrorSeverity.TECHNICAL: "❌",
            ErrorSeverity.CRITICAL: "🚨"
        }
        return icons.get(severity, "❌")

    def _check_performance_degradation(self, operation: str, elapsed: float):
        """Detecta degradación de performance"""
        if operation not in self.performance_baselines:
            self.performance_baselines[operation] = elapsed
            return

        baseline = self.performance_baselines[operation]
        if elapsed > baseline * 2.0:  # 100% más lento que baseline
            self.logger.warning(f"🐌 DEGRADACIÓN: {operation} tardó {elapsed:.2f}s vs baseline {baseline:.2f}s (+{((elapsed/baseline-1)*100):.0f}%)")

    def _detect_ui_changes(self, operation: str, error_msg: str):
        """Detecta posibles cambios en la UI"""
        ui_indicators = ['timeout', 'not found', 'locator', 'selector']
        if any(indicator in error_msg.lower() for indicator in ui_indicators):
            self.ui_failures[operation] += 1
            if self.ui_failures[operation] >= 3:
                self.logger.critical(f"🔧 POSIBLE CAMBIO UI: {operation} falló {self.ui_failures[operation]} veces - revisar selectores")

    def _calculate_performance_grade(self, operation_type: str, total_time: float, operations: int) -> str:
        """Calcula grado de performance basado en métricas"""
        if operations == 0:
            return "N/A"

        avg_time = total_time / operations

        # Umbrales basados en tipo de operación
        thresholds = {
            'navigation': {'A': 2.0, 'B': 5.0, 'C': 10.0},
            'extraction': {'A': 0.5, 'B': 2.0, 'C': 5.0},
            'default': {'A': 3.0, 'B': 8.0, 'C': 15.0}
        }

        threshold = thresholds.get(operation_type, thresholds['default'])

        if avg_time <= threshold['A']:
            return "A"
        elif avg_time <= threshold['B']:
            return "B"
        elif avg_time <= threshold['C']:
            return "C"
        else:
            return "D"

    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen mejorado del rendimiento"""
        total_time = sum(self.timings.values())

        # Agrupar operaciones similares
        grouped_operations = defaultdict(list)
        for op, time_val in self.timings.items():
            # Extraer tipo base de operación (ej: "procesar_pagina_X" -> "procesar_pagina")
            base_op = "_".join(op.split("_")[:2]) if "_" in op else op
            grouped_operations[base_op].append(time_val)

        return {
            'operaciones_totales': len(self.timings),
            'tiempo_total_segundos': total_time,
            'tiempo_promedio_por_operacion': total_time / len(self.timings) if self.timings else 0,
            'operacion_mas_lenta': max(self.timings.items(), key=lambda x: x[1]) if self.timings else None,
            'operacion_mas_rapida': min(self.timings.items(), key=lambda x: x[1]) if self.timings else None,
            'detalle_tiempos': dict(self.timings),
            'operaciones_agrupadas': {
                base_op: {
                    'count': len(times),
                    'total_time': sum(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times)
                } for base_op, times in grouped_operations.items()
            },
            'error_patterns': dict(self.error_patterns),
            'ui_failures': dict(self.ui_failures),
            'performance_baselines': self.performance_baselines
        }
    
    def print_performance_report(self, show_in_console: bool = False):
        """Imprime un reporte detallado de rendimiento"""
        summary = self.get_performance_summary()
        
        report = f"\n{'='*60}\n"
        report += "📊 REPORTE DE RENDIMIENTO\n"
        report += f"{'='*60}\n"
        report += f"🔢 Operaciones totales: {summary['operaciones_totales']}\n"
        report += f"⏱️ Tiempo total: {summary['tiempo_total_segundos']:.2f} segundos\n"
        
        if summary['operacion_mas_lenta']:
            report += f"🐌 Operación más lenta: {summary['operacion_mas_lenta'][0]} ({summary['operacion_mas_lenta'][1]:.2f}s)\n"
        
        if summary['operacion_mas_rapida']:
            report += f"⚡ Operación más rápida: {summary['operacion_mas_rapida'][0]} ({summary['operacion_mas_rapida'][1]:.2f}s)\n"
        
        report += "\n📋 DETALLE DE TIEMPOS:\n"
        for operation, time_taken in summary['detalle_tiempos'].items():
            report += f"  • {operation}: {time_taken:.2f}s\n"
        
        report += f"{'='*60}\n"
        
        # Log to file always
        self.logger.info(f"PERFORMANCE_REPORT:{report}")
        
        # Only print to console if requested
        if show_in_console:
            print(report)

def get_log_file_path() -> str:
    """Obtiene la ruta del archivo de log"""
    try:
        from .utils import data_path
    except ImportError:
        # Fallback for when imported directly
        def data_path(name):
            project_root = os.path.dirname(os.path.dirname(__file__))
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, name)
    
    timestamp = datetime.now().strftime("%Y%m%d")
    return data_path(f"automation_{timestamp}.log")

_global_logger: Optional[PerformanceLogger] = None

def get_logger(verbose_level: int = 3) -> PerformanceLogger:
    """Obtiene la instancia global del logger con nivel de verbosidad configurable

    Args:
        verbose_level: 1=mínimo, 3=normal, 5=máximo detalle
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = PerformanceLogger(get_log_file_path(), verbose_level)
        _cleanup_old_logs()
    return _global_logger

def _cleanup_old_logs(max_days: int = 30):
    """Limpia logs antiguos para evitar acumulación"""
    try:
        from .utils import data_path
        import glob
        import os
        from datetime import datetime, timedelta

        data_dir = os.path.dirname(data_path("dummy"))
        log_pattern = os.path.join(data_dir, "automation_*.log")
        logs_dir = os.path.join(data_dir, "logs")

        cutoff_date = datetime.now() - timedelta(days=max_days)

        # Limpiar logs principales
        for log_file in glob.glob(log_pattern):
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                if file_time < cutoff_date:
                    os.remove(log_file)
            except (OSError, ValueError):
                pass

        # Limpiar logs detallados
        if os.path.exists(logs_dir):
            for log_file in glob.glob(os.path.join(logs_dir, "*.log")):
                try:
                    file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                    if file_time < cutoff_date:
                        os.remove(log_file)
                except (OSError, ValueError):
                    pass

    except ImportError:
        pass  # Fallback si no se puede importar utils
    except Exception:
        pass  # Fallar silenciosamente para no interrumpir la aplicación

def timer(operation_name: str, extra_info: str = ""):
    """Decorador conveniente para medir tiempo de funciones"""
    return get_logger().time_operation(operation_name, extra_info)

# Funciones de conveniencia para diferentes niveles de verbosidad
def get_minimal_logger() -> PerformanceLogger:
    """Logger con mínimo detalle (solo errores críticos y resúmenes)"""
    return get_logger(verbose_level=1)

def get_normal_logger() -> PerformanceLogger:
    """Logger con detalle normal (operaciones importantes)"""
    return get_logger(verbose_level=3)

def get_verbose_logger() -> PerformanceLogger:
    """Logger con máximo detalle (para debugging)"""
    return get_logger(verbose_level=5)

# Crear una instancia de logger a nivel de módulo para compatibilidad
# Muchos módulos hacen: `from src.logger import logger` y esperan métodos estilo logging.
# Aquí exponemos el logger subyacente (logging.Logger) del PerformanceLogger global.
try:
    logger = get_logger().logger  # logging.Logger
except Exception:
    # Fallback muy defensivo para evitar romper importaciones en escenarios de arranque temprano
    logger = logging.getLogger('acumba_automation_fallback')
    if not logger.handlers:
        _fmt = logging.Formatter('[%(asctime)s] %(levelname)s - %(name)s - %(message)s',
                                 datefmt='%Y-%m-%d %H:%M:%S')
        _ch = logging.StreamHandler()
        _ch.setFormatter(_fmt)
        _ch.setLevel(logging.INFO)
        logger.addHandler(_ch)
    logger.setLevel(logging.INFO)

# Exportar enums para uso externo
__all__ = ['PerformanceLogger', 'LogLevel', 'ErrorSeverity', 'get_logger', 'logger',
           'get_minimal_logger', 'get_normal_logger', 'get_verbose_logger', 'timer']