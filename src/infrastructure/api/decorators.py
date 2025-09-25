"""
Decoradores para endpoints de la API
"""
import functools
from typing import Callable, Optional, Dict, TypeVar
try:  # Python 3.10+ has ParamSpec in typing, fallback to typing_extensions otherwise
    from typing import ParamSpec  # type: ignore
except Exception:  # pragma: no cover - fallback for older runtimes
    from typing_extensions import ParamSpec  # type: ignore
import logging
import time
from collections import defaultdict, deque
import threading

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

# Generic parameters to preserve function signatures and return types
P = ParamSpec("P")
R = TypeVar("R")


def disabled_endpoint(reason: str = "Temporalmente deshabilitado") -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorador para deshabilitar endpoints temporalmente sin borrar el código.
    
    Args:
        reason: Motivo por el cual está deshabilitado el endpoint
        
    Example:
        @disabled_endpoint("mientras se revisan los modelos")
        def get_basic_info(self, campaign_id: int) -> CampaignBasicInfo:
            # Código original se preserva
            pass
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore[return-value]
            error_msg = f"Endpoint '{func.__name__}' está {reason}"
            logger.warning(error_msg)
            raise NotImplementedError(error_msg)
        
        # Actualizar docstring para indicar que está deshabilitado
        if wrapper.__doc__:
            wrapper.__doc__ = f"🔴 DESHABILITADO: {wrapper.__doc__}"
        else:
            wrapper.__doc__ = f"🔴 DESHABILITADO: {reason}"
            
        return wrapper
    return decorator


def experimental_endpoint(warning_msg: str = "Este endpoint es experimental") -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorador para marcar endpoints como experimentales.
    
    Args:
        warning_msg: Mensaje de advertencia a mostrar
        
    Example:
        @experimental_endpoint("API en desarrollo - puede cambiar")
        def new_feature(self):
            pass
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            logger.warning(f"{func.__name__}: {warning_msg}")
            return func(*args, **kwargs)
        
        # Marcar en docstring como experimental
        if wrapper.__doc__:
            wrapper.__doc__ = f"⚠️ EXPERIMENTAL: {wrapper.__doc__}"
        else:
            wrapper.__doc__ = f"⚠️ EXPERIMENTAL: {warning_msg}"
            
        return wrapper
    return decorator


def deprecated_endpoint(replacement: Optional[str] = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorador para marcar endpoints como deprecados (pero aún funcionales).
    
    Args:
        replacement: Nombre del método/endpoint que debe usarse en su lugar
        
    Example:
        @deprecated_endpoint("usar get_detailed_info() en su lugar")
        def get_old_info(self):
            pass
    """
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            warning_msg = f"Endpoint '{func.__name__}' está deprecado"
            if replacement:
                warning_msg += f". {replacement}"
            
            logger.warning(warning_msg)
            # Continúa ejecutando la función original
            return func(*args, **kwargs)
        
        # Marcar en docstring como deprecado
        if wrapper.__doc__:
            wrapper.__doc__ = f"⚠️ DEPRECADO: {wrapper.__doc__}"
        else:
            wrapper.__doc__ = f"⚠️ DEPRECADO: {replacement or 'Será removido en versión futura'}"
            
        return wrapper
    return decorator


# Rate limiting global storage
_rate_limits: Dict[str, deque] = defaultdict(lambda: deque())
_rate_limit_lock = threading.Lock()


def rate_limit(max_calls: int, time_window: int, unit: str = "minuto") -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorador para limitar la tasa de llamadas a endpoints de la API.
    
    Cuando se excede el límite, espera automáticamente y reintenta.
    No falla - garantiza que la función se ejecute eventualmente.
    
    Args:
        max_calls: Número máximo de llamadas permitidas
        time_window: Ventana de tiempo para el límite
        unit: Unidad de tiempo ("segundo", "minuto", "hora")
        
    Examples:
        @rate_limit(10, 1, "minuto")  # 10 llamadas por minuto
        def get_campaign_info(self, campaign_id):
            pass
            
        @rate_limit(5, 1, "segundo")  # 5 llamadas por segundo  
        def get_quick_data(self):
            pass
            
        @rate_limit(100, 1, "hora")   # 100 llamadas por hora
        def get_bulk_data(self):
            pass
    """
    # Convertir tiempo a segundos
    time_multipliers = {
        "segundo": 1,
        "minuto": 60,
        "hora": 3600
    }
    
    if unit not in time_multipliers:
        raise ValueError(f"Unidad '{unit}' no válida. Use: segundo, minuto, hora")
    
    window_seconds = time_window * time_multipliers[unit]
    
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Crear identificador único para la función
            func_id = f"{func.__module__}.{func.__qualname__}"
            
            with _rate_limit_lock:
                now = time.time()
                call_times = _rate_limits[func_id]
                
                # Limpiar llamadas antiguas fuera de la ventana
                while call_times and call_times[0] <= now - window_seconds:
                    call_times.popleft()
                
                # Verificar si hemos excedido el límite
                if len(call_times) >= max_calls:
                    # Calcular tiempo de espera hasta que la llamada más antigua expire
                    oldest_call = call_times[0]
                    wait_time = (oldest_call + window_seconds) - now
                    
                    if wait_time > 0:
                        logger.warning(
                            f"Rate limit excedido para {func.__name__}: "
                            f"{len(call_times)}/{max_calls} llamadas en {time_window} {unit}. "
                            f"Esperando {wait_time:.1f} segundos..."
                        )
                        time.sleep(wait_time)
                        
                        # Limpiar nuevamente después de esperar
                        now = time.time()
                        while call_times and call_times[0] <= now - window_seconds:
                            call_times.popleft()
                
                # Registrar esta llamada
                call_times.append(now)
            
            # Ejecutar la función original
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Rate limit OK para {func.__name__}: {len(call_times)}/{max_calls} llamadas")
                return result
                
            except Exception as e:
                # Si hay un error de API que indique rate limiting, esperar más tiempo
                error_message = str(e).lower()
                if any(phrase in error_message for phrase in ["rate limit", "too many requests", "429"]):
                    logger.warning(f"Error de rate limit detectado en API: {e}")
                    logger.info("Esperando 60 segundos adicionales por precaución...")
                    time.sleep(60)
                    
                    # Intentar una vez más
                    logger.info(f"Reintentando {func.__name__}...")
                    return func(*args, **kwargs)
                else:
                    # Re-lanzar otros errores
                    raise
        
        # Actualizar docstring
        rate_info = f"⚡ RATE LIMITED: {max_calls} llamadas por {time_window} {unit}"
        if wrapper.__doc__:
            wrapper.__doc__ = f"{rate_info}\n{wrapper.__doc__}"
        else:
            wrapper.__doc__ = rate_info
            
        return wrapper
    return decorator


def high_rate_limit(func: Callable[P, R]) -> Callable[P, R]:
    """Decorador preconfigurado para endpoints de alto límite (100/hora)"""
    return rate_limit(100, 1, "hora")(func)

def medium_rate_limit(func: Callable[P, R]) -> Callable[P, R]:
    """Decorador preconfigurado para endpoints de límite medio (10/minuto)"""
    return rate_limit(10, 1, "minuto")(func)


def low_rate_limit(func: Callable[P, R]) -> Callable[P, R]:
    """Decorador preconfigurado para endpoints de límite bajo (5/minuto)"""
    return rate_limit(5, 1, "minuto")(func)


def burst_rate_limit(func: Callable[P, R]) -> Callable[P, R]:
    """Decorador preconfigurado para endpoints de ráfaga (5/segundo)"""
    return rate_limit(5, 1, "segundo")(func)