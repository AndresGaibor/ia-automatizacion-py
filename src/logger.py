import logging
import time
from datetime import datetime
from functools import wraps
from typing import Dict, Optional, Any, Callable
import os
import signal

class PerformanceLogger:
    """Logger especializado para medir rendimiento y tiempos de operación"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.timings: Dict[str, float] = {}
        self.start_times: Dict[str, float] = {}
        self.operation_counts: Dict[str, int] = {}
        
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
    
    def start_timer(self, operation: str) -> None:
        """Inicia el cronómetro para una operación"""
        self.start_times[operation] = time.time()
        self.logger.info(f"⏱️ INICIO: {operation}")
    
    def end_timer(self, operation: str, extra_info: str = "") -> float:
        """Termina el cronómetro y registra el tiempo transcurrido"""
        if operation not in self.start_times:
            self.logger.warning(f"⚠️ No se encontró tiempo de inicio para: {operation}")
            return 0.0
        
        elapsed = time.time() - self.start_times[operation]
        self.timings[operation] = elapsed
        
        self.operation_counts[operation] = self.operation_counts.get(operation, 0) + 1
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
        """Registra acciones del navegador con contexto"""
        target_str = f" en '{target}'" if target else ""
        extra_str = f" - {extra_info}" if extra_info else ""
        self.logger.info(f"🌐 BROWSER: {action}{target_str}{extra_str}")
    
    def log_data_extraction(self, data_type: str, count: int, source: str = ""):
        """Registra extracciones de datos"""
        source_str = f" desde {source}" if source else ""
        self.logger.info(f"📊 DATOS: Extraídos {count} registros de {data_type}{source_str}")
    
    def log_error(self, operation: str, error: Exception, context: str = ""):
        """Registra errores con contexto"""
        context_str = f" - Contexto: {context}" if context else ""
        self.logger.error(f"❌ ERROR en {operation}: {str(error)}{context_str}")
    
    def log_warning(self, operation: str, message: str):
        """Registra advertencias"""
        self.logger.warning(f"⚠️ WARNING en {operation}: {message}")
    
    def with_timeout(self, timeout_seconds: int = 300):
        """Decorador para aplicar timeout a operaciones que pueden colgarse"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                def timeout_handler(signum, frame):
                    self.log_error(func.__name__, Exception("Timeout"), f"Operación excedió {timeout_seconds}s")
                    raise TimeoutError(f"Operación {func.__name__} excedió timeout de {timeout_seconds} segundos")
                
                # Solo en sistemas Unix
                if hasattr(signal, 'SIGALRM'):
                    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout_seconds)
                
                try:
                    result = func(*args, **kwargs)
                    if hasattr(signal, 'SIGALRM'):
                        signal.alarm(0)  # Cancelar alarma
                        signal.signal(signal.SIGALRM, old_handler)
                    return result
                except TimeoutError:
                    if hasattr(signal, 'SIGALRM'):
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, old_handler)
                    raise
                except Exception as e:
                    if hasattr(signal, 'SIGALRM'):
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
        """Registra progreso de operaciones"""
        percentage = (current / total) * 100 if total > 0 else 0
        operation_str = f"{operation} - " if operation else ""
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
        """Registra un heartbeat para monitorear que el proceso sigue vivo"""
        details_str = f" - {details}" if details else ""
        self.logger.info(f"💓 HEARTBEAT: {operation}{details_str}")
    
    def log_checkpoint(self, checkpoint: str, progress: str = ""):
        """Registra un checkpoint para seguimiento detallado"""
        progress_str = f" - {progress}" if progress else ""
        self.logger.info(f"📍 CHECKPOINT: {checkpoint}{progress_str}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen del rendimiento"""
        total_time = sum(self.timings.values())
        return {
            'operaciones_totales': len(self.timings),
            'tiempo_total_segundos': total_time,
            'tiempo_promedio_por_operacion': total_time / len(self.timings) if self.timings else 0,
            'operacion_mas_lenta': max(self.timings.items(), key=lambda x: x[1]) if self.timings else None,
            'operacion_mas_rapida': min(self.timings.items(), key=lambda x: x[1]) if self.timings else None,
            'detalle_tiempos': dict(sorted(self.timings.items(), key=lambda x: x[1], reverse=True))
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

def get_logger() -> PerformanceLogger:
    """Obtiene la instancia global del logger"""
    global _global_logger
    if _global_logger is None:
        _global_logger = PerformanceLogger(get_log_file_path())
    return _global_logger

def timer(operation_name: str, extra_info: str = ""):
    """Decorador conveniente para medir tiempo de funciones"""
    return get_logger().time_operation(operation_name, extra_info)