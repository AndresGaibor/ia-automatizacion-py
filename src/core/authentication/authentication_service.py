"""Enhanced authentication service with proper error handling and session management."""
import logging
from typing import Protocol
from playwright.sync_api import BrowserContext
from pathlib import Path

from ..errors import AuthenticationError, ConfigurationError
from ..config.config_manager import ConfigManager
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


class SessionStorage(Protocol):
    """Protocol for session storage operations."""

    def save_session(self, context: BrowserContext) -> None:
        """Save browser session state."""
        ...

    def get_session_path(self) -> str:
        """Get session storage file path."""
        ...


class FileSessionStorage:
    """File-based session storage implementation."""

    def __init__(self, session_path: str):
        self.session_path = session_path

    def save_session(self, context: BrowserContext) -> None:
        """Save session to file."""
        try:
            Path(self.session_path).parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=self.session_path)
        except Exception as e:
            raise AuthenticationError(
                "Failed to save session state",
                context={"session_path": self.session_path, "error": str(e)}
            ) from e

    def get_session_path(self) -> str:
        """Get session file path."""
        return self.session_path


class AuthenticationService:
    """Enhanced authentication service delegating to AuthFlow/POM."""

    def __init__(
        self,
        config_manager: ConfigManager,
        session_storage: SessionStorage
    ):
        self.config_manager = config_manager
        self.session_storage = session_storage

    def authenticate(self, page, context: BrowserContext) -> None:
        """Main authentication flow delegating to AuthFlow."""
        logger.info("🔐 Iniciando proceso de autenticación completo")
        logger.debug("📋 Parámetros de autenticación",
                    has_context=bool(context))

        try:
            logger.debug("🔧 PASO 1: Cargando configuración")
            config = self.config_manager.get_config()
            logger.debug("✅ Configuración cargada exitosamente")

            logger.debug("🔍 PASO 2: Validando credenciales")
            self._validate_credentials(config)
            logger.debug("✅ Credenciales validadas correctamente")

            username = config["user"]
            password = config["password"]
            url = config["url"]
            url_base = config["url_base"]

            logger.info(f"🔑 Iniciando login para usuario: {username}")
            logger.debug("🌐 URLs configuradas", login_url=url, base_url=url_base)

            logger.debug("🔧 PASO 3-8: Delegando a AuthFlow para autenticación")
            auth_flow = AuthFlow(page, context)
            auth_flow.ensure_authenticated()

            logger.info("💾 PASO 9: Guardando estado de sesión...")
            logger.debug("📁 Ruta de sesión", path=self.session_storage.get_session_path())
            self.session_storage.save_session(context)
            logger.debug("✅ Estado de sesión guardado en disco")
            logger.info("✅ Estado de sesión guardado correctamente")
            logger.success("🎉 Proceso de autenticación completado exitosamente")

        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            if isinstance(e, (AuthenticationError, ConfigurationError)):
                raise
            raise AuthenticationError(
                "Authentication process failed",
                context={"error": str(e)}
            ) from e

    def _validate_credentials(self, config: dict) -> None:
        """Validate that credentials are properly configured."""
        logger.debug("🔍 Validando credenciales de configuración")
        username = config.get("user", "")
        password = config.get("password", "")

        logger.debug("📧 Usuario encontrado en config",
                    username=username if username and username != "usuario@correo.com" else "[NO CONFIGURADO]",
                    has_password=bool(password and password != "clave"))

        if not username or username == "usuario@correo.com":
            logger.error(f"❌ Usuario no configurado en config.yaml",
                        configured_value=username)
            notify(
                "Configuration Error",
                "Error: User not configured. Edit config.yaml with your Acumbamail email.",
                "error"
            )
            raise ConfigurationError(
                "User not configured in config.yaml",
                context={"configured_user": username}
            )

        if not password or password == "clave":
            logger.error(f"❌ Contraseña no configurada en config.yaml",
                        username=username)
            notify(
                "Configuration Error",
                "Error: Password not configured. Edit config.yaml with your Acumbamail password.",
                "error"
            )
            raise ConfigurationError("Password not configured in config.yaml")

        logger.debug("✅ Credenciales válidas encontradas", username=username)

    def refresh_session(self, page, context: BrowserContext) -> bool:
        """
        Refresh the session by re-authenticating when session expires.

        Args:
            page: Playwright page object
            context: Browser context to save updated session

        Returns:
            True if session was refreshed successfully, False otherwise
        """
        try:
            logger.warning("🔄 Sesión expirada, iniciando re-autenticación...")
            self.authenticate(page, context)
            logger.success("✅ Sesión refrescada exitosamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error refrescando sesión: {e}")
            notify("Session Error", f"Failed to refresh session: {e}", "error")
            return False