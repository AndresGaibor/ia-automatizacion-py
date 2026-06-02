"""Excepciones personalizadas para autenticación y gestión de sesiones."""

class ErrorAutenticacion(Exception):
    """Excepción base para todos los errores de autenticación."""
    pass


class ErrorPopupCookies(ErrorAutenticacion):
    """Popup de cookies detectado pero no pudo ser manejado."""

    def __init__(self, mensaje="Popup de cookies detectado pero no pudo ser cerrado"):
        super().__init__(mensaje)
        self.mensaje = mensaje


class ErrorSesionExpirada(ErrorAutenticacion):
    """Validación de sesión fallida - usuario necesita re-autenticarse."""

    def __init__(self, mensaje="Sesión expirada y requiere re-autenticación"):
        super().__init__(mensaje)
        self.mensaje = mensaje


class ErrorAutenticacionFallida(ErrorAutenticacion):
    """Login fallido después de máximo número de reintentos."""

    def __init__(self, mensaje="Autenticación fallida después de máximo de reintentos"):
        super().__init__(mensaje)
        self.mensaje = mensaje


class ErrorGuardarSesion(ErrorAutenticacion):
    """Error al guardar o cargar estado de sesión."""

    def __init__(self, mensaje="Error al guardar estado de sesión"):
        super().__init__(mensaje)
        self.mensaje = mensaje


class ErrorRedireccionURL(ErrorAutenticacion):
    """Redirección inesperada de URL detectada (probablemente a página de login)."""

    def __init__(self, url_actual: str, url_esperada: str | None = None):
        mensaje = f"Redirección inesperada a {url_actual}"
        if url_esperada:
            mensaje += f" (esperada {url_esperada})"
        super().__init__(mensaje)
        self.url_actual = url_actual
        self.url_esperada = url_esperada
        self.mensaje = mensaje


CookiePopupError = ErrorPopupCookies
AuthenticationFailedError = ErrorAutenticacionFallida
SessionSaveError = ErrorGuardarSesion
SessionExpiredError = ErrorSesionExpirada