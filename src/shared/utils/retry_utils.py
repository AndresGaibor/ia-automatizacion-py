"""
Utilidades de reintento con backoff exponencial para operaciones propensas a fallos por conexión lenta
"""
import time
import logging
from typing import Callable, TypeVar, Any, Optional
from functools import wraps

T = TypeVar('T')

def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 2,
    initial_delay: float = 2.0,
    backoff_factor: float = 1.5,
    logger: Optional[logging.Logger] = None
) -> T:
    """
    Reintenta una función con backoff exponencial en caso de fallo.

    Args:
        func: Función a ejecutar
        max_retries: Número máximo de reintentos (por defecto 2)
        initial_delay: Delay inicial en segundos (por defecto 2.0)
        backoff_factor: Factor de multiplicación para el delay (por defecto 1.5)
        logger: Logger opcional para registrar reintentos

    Returns:
        Resultado de la función si tiene éxito

    Raises:
        La última excepción si todos los reintentos fallan

    Example:
        >>> result = retry_with_backoff(lambda: api.get_campaign(123), max_retries=3)
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            if logger and attempt > 0:
                logger.info(f"🔄 Reintento {attempt}/{max_retries} después de {delay:.1f}s")

            result = func()

            if logger and attempt > 0:
                logger.success(f"✅ Operación exitosa en intento {attempt + 1}")

            return result

        except Exception as e:
            last_exception = e

            if attempt < max_retries:
                if logger:
                    logger.warning(f"⚠️ Intento {attempt + 1} falló: {e}. Reintentando en {delay:.1f}s...")
                time.sleep(delay)
                delay *= backoff_factor
            else:
                if logger:
                    logger.error(f"❌ Todos los reintentos fallaron después de {max_retries + 1} intentos")

    # Si llegamos aquí, todos los reintentos fallaron
    raise last_exception  # type: ignore


def retry_decorator(
    max_retries: int = 2,
    initial_delay: float = 2.0,
    backoff_factor: float = 1.5
):
    """
    Decorador para agregar reintentos automáticos a una función.

    Args:
        max_retries: Número máximo de reintentos
        initial_delay: Delay inicial en segundos
        backoff_factor: Factor de multiplicación para el delay

    Example:
        >>> @retry_decorator(max_retries=3)
        ... def get_campaign_data(campaign_id):
        ...     return api.campaigns.get_basic_info(campaign_id)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                initial_delay=initial_delay,
                backoff_factor=backoff_factor
            )
        return wrapper
    return decorator


def retry_on_condition(
    func: Callable[..., T],
    condition: Callable[[Exception], bool],
    max_retries: int = 2,
    initial_delay: float = 2.0,
    backoff_factor: float = 1.5,
    logger: Optional[logging.Logger] = None
) -> T:
    """
    Reintenta una función solo si la excepción cumple una condición específica.

    Args:
        func: Función a ejecutar
        condition: Función que recibe la excepción y retorna True si debe reintentar
        max_retries: Número máximo de reintentos
        initial_delay: Delay inicial en segundos
        backoff_factor: Factor de multiplicación para el delay
        logger: Logger opcional

    Returns:
        Resultado de la función si tiene éxito

    Raises:
        La excepción inmediatamente si no cumple la condición, o la última excepción si todos los reintentos fallan

    Example:
        >>> def should_retry(e):
        ...     return "timeout" in str(e).lower() or "connection" in str(e).lower()
        >>>
        >>> result = retry_on_condition(
        ...     lambda: api.get_campaign(123),
        ...     condition=should_retry,
        ...     max_retries=3
        ... )
    """
    last_exception = None
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            if logger and attempt > 0:
                logger.info(f"🔄 Reintento condicional {attempt}/{max_retries} después de {delay:.1f}s")

            result = func()

            if logger and attempt > 0:
                logger.success(f"✅ Operación exitosa en intento {attempt + 1}")

            return result

        except Exception as e:
            last_exception = e

            # Verificar si debemos reintentar basado en la condición
            if not condition(e):
                if logger:
                    logger.warning(f"⚠️ Excepción no cumple condición de reintento: {e}")
                raise  # Re-lanzar inmediatamente si no cumple la condición

            if attempt < max_retries:
                if logger:
                    logger.warning(f"⚠️ Intento {attempt + 1} falló con condición válida: {e}. Reintentando en {delay:.1f}s...")
                time.sleep(delay)
                delay *= backoff_factor
            else:
                if logger:
                    logger.error(f"❌ Todos los reintentos condicionales fallaron después de {max_retries + 1} intentos")

    # Si llegamos aquí, todos los reintentos fallaron
    raise last_exception  # type: ignore


def is_connection_error(exception: Exception) -> bool:
    """
    Determina si una excepción es un error de conexión que debería reintentarse.

    Args:
        exception: Excepción a evaluar

    Returns:
        True si es un error de conexión que debería reintentarse
    """
    error_msg = str(exception).lower()
    connection_keywords = [
        "timeout",
        "connection",
        "network",
        "no disponible",
        "not available",
        "refused",
        "timed out",
        "unreachable"
    ]

    return any(keyword in error_msg for keyword in connection_keywords)
