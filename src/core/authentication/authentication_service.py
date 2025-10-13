"""Enhanced authentication service with proper error handling and session management."""
import logging
from typing import Protocol
from playwright.sync_api import Page, BrowserContext, TimeoutError as PWTimeoutError
from pathlib import Path

from ..errors import AuthenticationError, ConfigurationError
from ..config.config_manager import ConfigManager
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


class AuthenticationService:
    """Enhanced authentication service with proper separation of concerns."""

    def __init__(
        self,
        config_manager: ConfigManager,
        session_storage: SessionStorage
    ):
        self.config_manager = config_manager
        self.session_storage = session_storage

    def authenticate(self, page: Page, context: BrowserContext) -> None:
        """Main authentication flow."""
        logger.info("🔐 Starting authentication process")

        try:
            config = self.config_manager.get_config()
            self._validate_credentials(config)

            username = config["user"]
            password = config["password"]
            url = config["url"]
            url_base = config["url_base"]

            logger.info(f"🔑 Starting login process for user: {username}")

            # Navigate to login page
            self._navigate_to_login_page(page, url)

            # Check if already authenticated
            if self._is_already_authenticated(page, url_base):
                logger.info("✅ Already authenticated")
                self.session_storage.save_session(context)
                return

            # Accept cookies if present
            self._accept_cookies_if_present(page)

            # Perform login if needed
            if not self._check_authentication_status(page):
                self._perform_login(page, username, password)
                logger.info("✅ Login completed successfully")
                notify("Authentication", "Login completed successfully", "info")
            else:
                logger.info("✅ Already authenticated")
                notify("Session", "Already authenticated in Acumbamail", "info")

            # Save session state
            logger.info("💾 Saving session state...")
            notify("Session", "Saving session state", "info")
            self.session_storage.save_session(context)

            # Additional wait to ensure session is fully established
            page.wait_for_timeout(3000)
            logger.info("✅ Session state saved correctly")

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
        username = config.get("user", "")
        password = config.get("password", "")

        if not username or username == "usuario@correo.com":
            logger.error(f"❌ User not configured in config.yaml - user: {username}")
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
            logger.error(f"❌ Password not configured in config.yaml - user: {username}")
            notify(
                "Configuration Error",
                "Error: Password not configured. Edit config.yaml with your Acumbamail password.",
                "error"
            )
            raise ConfigurationError("Password not configured in config.yaml")

    def _navigate_to_login_page(self, page: Page, url: str) -> None:
        """Navigate to the login page."""
        try:
            logger.info(f"🌐 Navigating to URL: {url}")
            page.goto(url, timeout=60_000)
            self._wait_for_page_load(page)
        except Exception as e:
            logger.error(f"❌ Error connecting to Acumbamail: {e} - url: {url}")
            notify("Connection Error", f"Error: Could not connect to Acumbamail: {e}", "error")
            raise AuthenticationError(
                f"Failed to connect to Acumbamail: {e}",
                context={"url": url}
            ) from e

    def _is_already_authenticated(self, page: Page, url_base: str) -> bool:
        """Check if user is already on the main page (authenticated)."""
        return f"{url_base}/" != page.url

    def _accept_cookies_if_present(self, page: Page) -> None:
        """Try to accept cookies if the button is present."""
        logger.info("🍪 Trying to accept cookies")
        try:
            page.get_by_role("button", name="Aceptar todas").click(timeout=30_000)
            logger.info("✅ Cookies accepted successfully")
        except PWTimeoutError:
            logger.info("⏱️ Timeout accepting cookies, button not found or not responding")
            logger.info("🔓 Continuing without accepting cookies")
        except Exception as e:
            logger.warning(f"⚠️ Unexpected error accepting cookies: {e}")
            logger.info("🔓 Continuing without accepting cookies")

    def _check_authentication_status(self, page: Page) -> bool:
        """Check if user is already authenticated."""
        logger.info("🔐 Checking authentication status")
        try:
            # Look for navigation with tools link
            logger.debug("🔍 Looking for 'Ir a la herramienta' link in navigation")
            nav_element = page.get_by_role("navigation")
            btn_tools = nav_element.get_by_role("link", name="Ir a la herramienta")

            # Verify the element is visible before clicking
            is_visible = btn_tools.is_visible(timeout=10000)
            if not is_visible:
                logger.info("🔓 'Ir a la herramienta' link not visible, assuming not authenticated")
                return False

            logger.debug("✅ Found 'Ir a la herramienta' link, clicking...")
            self._wait_for_page_load(page)
            btn_tools.click(timeout=30_000)
            self._wait_for_page_load(page)
            logger.info("✅ User already authenticated")
            return True

        except PWTimeoutError as e:
            logger.info("⏱️ Timeout checking authentication status: {e}")
            logger.info("🔓 'Ir a la herramienta' button not found or not responding, assuming not authenticated")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error checking authentication: {e}")
            logger.error(f"Tipo de error: {type(e).__name__}")
            logger.info("🔓 Assuming not authenticated and proceeding with login")
            return False

    def _perform_login(self, page: Page, username: str, password: str) -> None:
        """Perform the actual login process."""
        logger.info("🔐 Not authenticated. Proceeding to login...")
        notify("Authentication", "Credentials required, starting login", "info")

        try:
            # Step 1: Click login button
            logger.info("📌 PASO 1: Localizando y haciendo clic en botón 'Entra'")
            try:
                logger.debug("🔍 Buscando botón 'Entra'...")
                login_btn = page.get_by_role("link", name="Entra")

                # Verify button is visible
                is_visible = login_btn.is_visible(timeout=10000)
                if not is_visible:
                    logger.error("❌ ERROR PASO 1: Botón 'Entra' no visible")
                    raise AuthenticationError("Login button not found or not visible")

                logger.debug("✅ Botón 'Entra' encontrado, haciendo clic...")
                login_btn.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                logger.debug("✅ Click en 'Entra' realizado, página cargando...")

            except PWTimeoutError as e:
                logger.error(f"❌ ERROR PASO 1 - Timeout: {e}")
                raise AuthenticationError(
                    "Login button timeout",
                    context={"username": username, "error": str(e)}
                ) from e
            except Exception as e:
                logger.error(f"❌ ERROR PASO 1 - Error: {e}")
                logger.error(f"Tipo de error: {type(e).__name__}")
                raise AuthenticationError(
                    "Login button interaction failed",
                    context={"username": username, "error": str(e)}
                ) from e

            # Step 2: Fill login form
            logger.info("📌 PASO 2: Completando formulario de login")
            try:
                logger.debug("🔍 Buscando campo 'Correo electrónico'...")
                email_input = page.get_by_role("textbox", name="Correo electrónico")
                email_input.wait_for(state="visible", timeout=10000)
                email_input.fill(username)
                logger.debug("✅ Correo electrónico llenado")

                logger.debug("🔍 Buscando campo 'Contraseña'...")
                password_input = page.get_by_role("textbox", name="Contraseña")
                password_input.wait_for(state="visible", timeout=10000)
                password_input.fill(password)
                logger.debug("✅ Contraseña llenada")

                logger.debug("🔍 Buscando checkbox 'Mantener sesión iniciada'...")
                keepme_checkbox = page.locator('label[for="keepme-logged"]')
                keepme_checkbox.wait_for(state="visible", timeout=5000)
                if keepme_checkbox.is_visible():
                    keepme_checkbox.click()
                    logger.debug("✅ Checkbox 'Mantener sesión iniciada' marcado")
                else:
                    logger.warning("⚠️ Checkbox 'Mantener sesión iniciada' no encontrado, continuando...")

                logger.info("✅ Formulario de login completado")

            except PWTimeoutError as e:
                logger.error(f"❌ ERROR PASO 2 - Timeout en formulario: {e}")
                raise AuthenticationError(
                    "Login form timeout",
                    context={"username": username, "error": str(e)}
                ) from e
            except Exception as e:
                logger.error(f"❌ ERROR PASO 2 - Error en formulario: {e}")
                logger.error(f"Tipo de error: {type(e).__name__}")
                raise AuthenticationError(
                    "Login form filling failed",
                    context={"username": username, "error": str(e)}
                ) from e

            # Step 3: Submit form
            logger.info("📌 PASO 3: Enviando formulario de login")
            try:
                logger.debug("🔍 Buscando botón 'Entrar'...")
                submit_btn = page.get_by_role("button", name="Entrar")
                submit_btn.wait_for(state="visible", timeout=10000)
                logger.debug("✅ Botón 'Entrar' encontrado, enviando formulario...")

                # Use expect_navigation for robust navigation handling
                with page.expect_navigation(wait_until="domcontentloaded"):
                    submit_btn.click()
                    logger.debug("✅ Formulario enviado, esperando navegación...")
                    self._wait_for_page_load(page)

                logger.info("✅ Formulario de login enviado exitosamente")

            except PWTimeoutError as e:
                logger.error(f"❌ ERROR PASO 3 - Timeout enviando formulario: {e}")
                raise AuthenticationError(
                    "Login form submission timeout",
                    context={"username": username, "error": str(e)}
                ) from e
            except Exception as e:
                logger.error(f"❌ ERROR PASO 3 - Error enviando formulario: {e}")
                logger.error(f"Tipo de error: {type(e).__name__}")
                raise AuthenticationError(
                    "Login form submission failed",
                    context={"username": username, "error": str(e)}
                ) from e

            # Success
            logger.info("🎉 Login process completed successfully")
            notify("Authentication", "Login completed successfully", "info")

        except AuthenticationError:
            # Re-raise AuthenticationError as is
            raise
        except Exception as e:
            logger.error(f"❌ ERROR INESPERADO en proceso de login: {e}")
            logger.error(f"Tipo de error: {type(e).__name__}")
            raise AuthenticationError(
                "Login process failed unexpectedly",
                context={"username": username, "error": str(e)}
            ) from e

    def _wait_for_page_load(self, page: Page, timeout: int = 60_000) -> None:
        """Wait for page to load completely with timeout handling."""
        logger.info(f"⏳ Waiting for page load - timeout: {timeout}ms")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
            page.wait_for_load_state("networkidle", timeout=timeout)
            # Additional wait to ensure page is completely loaded
            page.wait_for_timeout(2000)
            logger.info("✅ Page loaded successfully")
        except Exception as e:
            logger.warning(f"Page took time to load: {e}. Continuing... - error: {str(e)}")


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