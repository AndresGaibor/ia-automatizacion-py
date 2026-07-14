# Wrapper delgado - código real en src/core/authentication/autentificacion.py
from src.core.authentication.autentificacion import *

# Re-exportar funciones públicas
from src.core.authentication.autentificacion import (
    aceptar_cookies,
    manejar_popup_cookies,
    autenticado,
    login
)

__all__ = ['aceptar_cookies', 'manejar_popup_cookies', 'autenticado', 'login']
