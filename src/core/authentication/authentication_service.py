"""Servicio de autenticación mejorado con manejo de errores y gestión de sesiones."""
import logging
from typing import Protocol
from playwright.sync_api import BrowserContext
from pathlib import Path

from ..errors import ErrorAutenticacion, ErrorConfiguracion
from ..config.config_manager import GestorConfiguracion
from src.infrastructure.scraping.flows.auth_flow import AuthFlow
try:
    from ...shared.logging.logger import get_logger
    from ...shared.utils.legacy_utils import notify
except ImportError:
    try:
        from ..shared.logging.logger import get_logger
        from ..shared.utils.legacy_utils import notify
    except ImportError:
        from src.shared.logging.logger import get_logger
        from src.shared.utils.legacy_utils import notify


logger = get_logger()


class AlmacenamientoSesion(Protocol):
    """Protocolo para operaciones de almacenamiento de sesión."""

    def guardar_sesion(self, contexto: BrowserContext) -> None:
        """Guarda estado del navegador."""
        ...

    def obtener_ruta_sesion(self) -> str:
        """Obtiene ruta del archivo de sesión."""
        ...


class AlmacenamientoSesionArchivo:
    """Implementación de almacenamiento de sesión basado en archivos."""

    def __init__(self, ruta_sesion: str):
        self.ruta_sesion = ruta_sesion

    def guardar_sesion(self, contexto: BrowserContext) -> None:
        """Guarda sesión en archivo."""
        try:
            Path(self.ruta_sesion).parent.mkdir(parents=True, exist_ok=True)
            contexto.storage_state(path=self.ruta_sesion)
        except Exception as e:
            raise ErrorAutenticacion(
                "Error guardando estado de sesión",
                contexto={"ruta_sesion": self.ruta_sesion, "error": str(e)}
            ) from e

    def obtener_ruta_sesion(self) -> str:
        """Obtiene ruta de archivo de sesión."""
        return self.ruta_sesion


class ServicioAutenticacion:
    """Servicio de autenticación mejorado que delega a AuthFlow/POM."""

    def __init__(
        self,
        gestor_config: GestorConfiguracion,
        almacenamiento_sesion: AlmacenamientoSesion
    ):
        self.gestor_config = gestor_config
        self.almacenamiento_sesion = almacenamiento_sesion

    def autenticar(self, page, contexto: BrowserContext) -> None:
        """Flujo de autenticación principal delegando a AuthFlow."""
        logger.info("🔐 Iniciando proceso de autenticación completo")
        logger.debug("📋 Parámetros de autenticación", tiene_contexto=bool(contexto))

        try:
            logger.debug("🔧 PASO 1: Cargando configuración")
            config = self.gestor_config.obtener_config()
            logger.debug("✅ Configuración cargada exitosamente")

            logger.debug("🔍 PASO 2: Validando credenciales")
            self._validar_credenciales(config)
            logger.debug("✅ Credenciales validadas correctamente")

            username = config["user"]
            password = config["password"]
            url = config["url"]
            url_base = config["url_base"]

            logger.info(f"🔑 Iniciando login para usuario: {username}")
            logger.debug("🌐 URLs configuradas", login_url=url, base_url=url_base)

            logger.debug("🔧 PASO 3-8: Delegando a AuthFlow para autenticación")
            auth_flow = AuthFlow(page, contexto)
            auth_flow.ensure_authenticated()

            logger.info("💾 PASO 9: Guardando estado de sesión...")
            logger.debug("📁 Ruta de sesión", path=self.almacenamiento_sesion.obtener_ruta_sesion())
            self.almacenamiento_sesion.guardar_sesion(contexto)
            logger.debug("✅ Estado de sesión guardado en disco")
            logger.info("✅ Estado de sesión guardado correctamente")
            logger.success("🎉 Proceso de autenticación completado exitosamente")

        except Exception as e:
            logger.error(f"❌ Autenticación fallida: {e}")
            if isinstance(e, (ErrorAutenticacion, ErrorConfiguracion)):
                raise
            raise ErrorAutenticacion(
                "Proceso de autenticación fallido",
                contexto={"error": str(e)}
            ) from e

    def _validar_credenciales(self, config: dict) -> None:
        """Valida que las credenciales estén correctamente configuradas."""
        logger.debug("🔍 Validando credenciales de configuración")
        username = config.get("user", "")
        password = config.get("password", "")

        logger.debug("📧 Usuario encontrado en config",
                    username=username if username and username != "usuario@correo.com" else "[NO CONFIGURADO]",
                    tiene_password=bool(password and password != "clave"))

        if not username or username == "usuario@correo.com":
            logger.error(f"❌ Usuario no configurado en config.yaml", valor_configurado=username)
            notify(
                "Error de Configuración",
                "Error: Usuario no configurado. Editar config.yaml con email de Acumbamail.",
                "error"
            )
            raise ErrorConfiguracion(
                "Usuario no configurado en config.yaml",
                contexto={"usuario_configurado": username}
            )

        if not password or password == "clave":
            logger.error(f"❌ Contraseña no configurada en config.yaml", username=username)
            notify(
                "Error de Configuración",
                "Error: Contraseña no configurada. Editar config.yaml con contraseña de Acumbamail.",
                "error"
            )
            raise ErrorConfiguracion("Contraseña no configurada en config.yaml")

        logger.debug("✅ Credenciales válidas encontradas", username=username)

    def refrescar_sesion(self, page, contexto: BrowserContext) -> bool:
        """Refresca la sesión re-autenticando cuando expire."""
        try:
            logger.warning("🔄 Sesión expirada, iniciando re-autenticación...")
            self.autenticar(page, contexto)
            logger.success("✅ Sesión refrescada exitosamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error refrescando sesión: {e}")
            notify("Error de Sesión", f"Error refrescando sesión: {e}", "error")
            return False
AuthenticationService = ServicioAutenticacion
