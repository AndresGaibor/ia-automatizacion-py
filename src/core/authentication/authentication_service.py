"""Enhanced authentication service with proper error handling and session management."""
from typing import Protocol, Optional
from playwright.sync_api import Page, BrowserContext, TimeoutError as PWTimeoutError
from pathlib import Path

from ..errors import AuthenticationError, ConfigurationError
from ..config.config_manager import ConfigManager
try:
    from ...shared.logging import get_logger
    from ...shared.utils import notify
except ImportError:
    from src.shared.logging import get_logger
    from src.shared.utils import notify


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
                logger.success("✅ Already authenticated")
                self.session_storage.save_session(context)
                return

            # Accept cookies if present
            self._accept_cookies_if_present(page)

            # Perform login if needed
            if not self._check_authentication_status(page):
                self._perform_login(page, username, password)
                logger.success("✅ Login completed successfully")
                notify("Authentication", "Login completed successfully", "info")
            else:
                logger.success("✅ Already authenticated")
                notify("Session", "Already authenticated in Acumbamail", "info")

            # Save session state
            logger.info("💾 Saving session state...")
            notify("Session", "Saving session state", "info")
            self.session_storage.save_session(context)

            # Additional wait to ensure session is fully established
            page.wait_for_timeout(3000)
            logger.success("✅ Session state saved correctly")

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
            logger.error("❌ User not configured in config.yaml", user=username)
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
            logger.error("❌ Password not configured in config.yaml", user=username)
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
            logger.error(f"❌ Error connecting to Acumbamail: {e}", url=url)
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
            logger.success("✅ Cookies accepted successfully")
        except Exception as e:
            logger.info(f"Cookie button not found: {e}. Continuing...", error=str(e))

    def _check_authentication_status(self, page: Page) -> bool:
        """Check if user is already authenticated."""
        logger.info("🔐 Checking authentication status")
        try:
            btn_tools = page.get_by_role("navigation").get_by_role("link", name="Ir a la herramienta")
            self._wait_for_page_load(page)
            btn_tools.click(timeout=30_000)
            self._wait_for_page_load(page)
            logger.success("✅ User already authenticated")
            return True
        except PWTimeoutError:
            logger.info("🔓 'Entra' button not found, assuming not authenticated")
            return False

    def _perform_login(self, page: Page, username: str, password: str) -> None:
        """Perform the actual login process."""
        logger.info("🔐 Not authenticated. Proceeding to login...")
        notify("Authentication", "Credentials required, starting login", "info")

        try:
            # Click login button
            logger.info("🖱️ Clicking login button")
            login_btn = page.get_by_role("link", name="Entra")
            login_btn.click()
            page.wait_for_load_state("networkidle")

            # Fill login form
            logger.info("📝 Filling login form...")
            page.get_by_role("textbox", name="Correo electrónico").fill(username)
            page.get_by_role("textbox", name="Contraseña").fill(password)
            page.locator('label[for="keepme-logged"]').click()

            # Submit form
            logger.info("🚀 Submitting login form...")
            with page.expect_navigation(wait_until="domcontentloaded"):
                page.get_by_role("button", name="Entrar").click()
                self._wait_for_page_load(page)

        except Exception as e:
            logger.error(f"❌ Error during login: {e}", error=str(e))
            notify("Login Error", f"Error during login: {e}. Check your credentials.", "error")
            raise AuthenticationError(
                f"Login process failed: {e}",
                context={"username": username}
            ) from e

    def _wait_for_page_load(self, page: Page, timeout: int = 60_000) -> None:
        """Wait for page to load completely with timeout handling."""
        logger.info("⏳ Waiting for page load", timeout=timeout)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
            page.wait_for_load_state("networkidle", timeout=timeout)
            # Additional wait to ensure page is completely loaded
            page.wait_for_timeout(2000)
            logger.success("✅ Page loaded successfully")
        except Exception as e:
            logger.warning(f"Page took time to load: {e}. Continuing...", error=str(e))


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