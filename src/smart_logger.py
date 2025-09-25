"""
Smart Logger con integración a config.yaml

Este módulo extiende el PerformanceLogger existente para que respete
la configuración debug en config.yaml y proporcione logging inteligente.
"""

from .logger import PerformanceLogger
from .utils import load_config
from typing import Optional, Dict, Any

class SmartLogger(PerformanceLogger):
    """Logger inteligente que respeta configuración de config.yaml"""

    def __init__(self, log_file: Optional[str] = None, force_verbose_level: Optional[int] = None):
        # Cargar configuración desde config.yaml
        config = load_config()

        # Determinar nivel de verbosidad basado en configuración
        verbose_level = self._determine_verbose_level(config, force_verbose_level)

        # Determinar si mostrar en consola
        self.show_console = self._should_show_console(config)

        # Inicializar logger base
        super().__init__(log_file, verbose_level)

        # Configurar handler de consola basado en configuración
        self._configure_console_handler()

        # Almacenar configuración para referencia
        self.config = config
        self.logging_config = config.get('logging', {})

    def _determine_verbose_level(self, config: Dict[str, Any], force_level: Optional[int]) -> int:
        """Determina el nivel de verbosidad basado en configuración"""
        if force_level is not None:
            return force_level

        # Verificar configuración de logging específica
        logging_config = config.get('logging', {})

        if not logging_config.get('enabled', True):
            return 1  # Nivel mínimo si logging está deshabilitado

        # Mapear nivel de string a número
        level_map = {
            'silent': 0,
            'minimal': 1,
            'normal': 3,
            'verbose': 4,
            'debug': 5,
            'trace': 5
        }

        config_level = logging_config.get('level', 'normal')
        if isinstance(config_level, str):
            config_level = config_level.lower()
        verbose_level = level_map.get(config_level, 3)

        # Si debug: true en raíz de config, forzar nivel alto
        if config.get('debug', False):
            verbose_level = max(verbose_level, 4)

        return verbose_level

    def _should_show_console(self, config: Dict[str, Any]) -> bool:
        """Determina si debe mostrar logs en consola"""
        logging_config = config.get('logging', {})

        # Si logging está deshabilitado, no mostrar en consola
        if not logging_config.get('enabled', True):
            return False

        # Si debug: true, siempre mostrar en consola
        if config.get('debug', False):
            return True

        # Usar configuración específica de console_output
        return logging_config.get('console_output', False)

    def _configure_console_handler(self):
        """Configura el handler de consola basado en configuración"""
        # Encontrar handler de consola existente
        console_handler = None
        for handler in self.logger.handlers:
            if hasattr(handler, 'stream') and hasattr(handler.stream, 'name'):
                if handler.stream.name in ['<stdout>', '<stderr>']:
                    console_handler = handler
                    break

        if console_handler:
            if self.show_console:
                # Ajustar nivel del handler de consola
                if self.verbose_level >= 4:  # Debug/verbose mode
                    console_handler.setLevel(self.logger.level)
                else:
                    console_handler.setLevel(40)  # Solo errores críticos
            else:
                # Deshabilitar salida a consola
                console_handler.setLevel(100)  # Nivel muy alto para desactivar

    def log_with_config_check(self, level: str, message: str, **kwargs):
        """Log solo si el nivel está permitido por configuración"""
        if not self.logging_config.get('enabled', True):
            return

        # Llamar método apropiado del logger base
        method = getattr(self, level, self.info)
        method(message, **kwargs)

    def debug_only(self, message: str, **kwargs):
        """Log solo si debug está habilitado en config"""
        if self.config.get('debug', False):
            self.debug(message, **kwargs)

    def console_print(self, message: str, force: bool = False):
        """Imprime a consola solo si está permitido por configuración"""
        if force or self.show_console:
            print(message)

    def conditional_log(self, condition: bool, level: str, message: str, **kwargs):
        """Log condicional basado en parámetro y configuración"""
        if condition and self.logging_config.get('enabled', True):
            method = getattr(self, level, self.info)
            method(message, **kwargs)

# Variable global para logger inteligente
_smart_logger_instance: Optional[SmartLogger] = None

def get_smart_logger(force_verbose_level: Optional[int] = None) -> SmartLogger:
    """
    Obtiene instancia global del logger inteligente

    Args:
        force_verbose_level: Forzar nivel específico ignorando config
    """
    global _smart_logger_instance

    if _smart_logger_instance is None:
        from .logger import get_log_file_path
        _smart_logger_instance = SmartLogger(get_log_file_path(), force_verbose_level)

    return _smart_logger_instance

def get_logger(verbose_level: int = None) -> SmartLogger:
    """
    Función de compatibilidad que devuelve el logger inteligente
    Reemplaza la función original para mantener compatibilidad
    """
    return get_smart_logger(verbose_level)

# Context managers útiles
class DebugContext:
    """Context manager para logging temporal en modo debug"""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.logger = get_smart_logger()

    def __enter__(self):
        self.logger.debug_only(f"🚀 Iniciando {self.operation_name}")
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.logger.debug_only(f"❌ Error en {self.operation_name}: {exc_val}")
        else:
            self.logger.debug_only(f"✅ Completado {self.operation_name}")

class ConditionalLogging:
    """Context manager para logging condicional"""

    def __init__(self, condition: bool, operation_name: str):
        self.condition = condition
        self.operation_name = operation_name
        self.logger = get_smart_logger()

    def __enter__(self):
        if self.condition:
            self.logger.info(f"🚀 Iniciando {self.operation_name}")
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.condition:
            if exc_type:
                self.logger.error(f"❌ Error en {self.operation_name}: {exc_val}")
            else:
                self.logger.log_success(f"Completado {self.operation_name}")

# Decoradores útiles
def debug_log(func):
    """Decorador para logging automático en modo debug"""
    def wrapper(*args, **kwargs):
        logger = get_smart_logger()
        logger.debug_only(f"🔧 Ejecutando {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug_only(f"✅ {func.__name__} completado")
            return result
        except Exception as e:
            logger.debug_only(f"❌ Error en {func.__name__}: {e}")
            raise
    return wrapper

def conditional_log_decorator(condition_func):
    """Decorador para logging condicional basado en función"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_smart_logger()
            should_log = condition_func() if callable(condition_func) else condition_func

            if should_log:
                logger.info(f"🔧 Ejecutando {func.__name__}")

            try:
                result = func(*args, **kwargs)
                if should_log:
                    logger.log_success(f"Completado {func.__name__}")
                return result
            except Exception as e:
                if should_log:
                    logger.log_error(func.__name__, e)
                raise
        return wrapper
    return decorator

# Funciones de conveniencia
def is_debug_enabled() -> bool:
    """Verifica si debug está habilitado en config"""
    config = load_config()
    return config.get('debug', False)

def is_logging_enabled() -> bool:
    """Verifica si logging está habilitado en config"""
    config = load_config()
    logging_config = config.get('logging', {})
    return logging_config.get('enabled', True)

def get_logging_level() -> str:
    """Obtiene el nivel de logging configurado"""
    config = load_config()
    logging_config = config.get('logging', {})
    return logging_config.get('level', 'normal')

# Ejemplo de uso:
#
# # Logging básico que respeta configuración
# logger = get_smart_logger()
# logger.info("Mensaje que se muestra según configuración")
# logger.debug_only("Solo si debug: true en config.yaml")
#
# # Context managers
# with DebugContext("operación_compleja"):
#     # código que solo logea si debug está habilitado
#     pass
#
# with ConditionalLogging(is_debug_enabled(), "operación_visible"):
#     # código que logea según condición
#     pass
#
# # Decoradores
# @debug_log
# def mi_funcion():
#     pass
#
# @conditional_log_decorator(lambda: is_debug_enabled())
# def otra_funcion():
#     pass