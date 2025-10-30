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
        logger.info("🔐 Iniciando proceso de autenticación completo")
        logger.debug("📋 Parámetros de autenticación",
                    page_url=page.url if page else "No page",
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

            # Navigate to login page
            logger.debug("🔧 PASO 3: Navegando a página de login")
            self._navigate_to_login_page(page, url)
            logger.debug("✅ Navegación completada", current_url=page.url)

            # Check if already authenticated
            logger.debug("🔍 PASO 4: Verificando si ya está autenticado")
            if self._is_already_authenticated(page, url_base):
                logger.info("✅ Ya autenticado - usuario ya tiene sesión activa")
                logger.debug("💾 Guardando estado de sesión existente")
                self.session_storage.save_session(context)
                logger.success("✅ Autenticación completada (sesión existente)")
                return

            # Accept cookies if present
            logger.debug("🔧 PASO 5: Intentando aceptar cookies")
            self._accept_cookies_if_present(page)

            # Perform login if needed
            logger.debug("🔍 PASO 6: Verificando estado de autenticación")
            if not self._check_authentication_status(page):
                logger.info("🔐 No autenticado - procediendo con login")
                logger.debug("🔧 PASO 7: Ejecutando proceso de login")
                self._perform_login(page, username, password)
                logger.info("✅ Login completado exitosamente")
                logger.success("✅ Credenciales aceptadas por Acumbamail")
                # notify("Authentication", "Login completed successfully", "info")
            else:
                logger.info("✅ Ya autenticado - detectado durante verificación")
                # notify("Session", "Already authenticated in Acumbamail", "info")

            # Save session state
            logger.info("💾 PASO 8: Guardando estado de sesión...")
            logger.debug("📁 Ruta de sesión", path=self.session_storage.get_session_path())
            # notify("Session", "Saving session state", "info")
            self.session_storage.save_session(context)
            logger.debug("✅ Estado de sesión guardado en disco")

            # Additional wait to ensure session is fully established
            logger.debug("⏳ Esperando estabilización final de sesión (3s)...")
            page.wait_for_timeout(3000)
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

    def _navigate_to_login_page(self, page: Page, url: str) -> None:
        """Navigate to the login page."""
        logger.debug("🌐 Navegando a página de login", url=url, timeout="60s")
        try:
            logger.debug("⏳ Ejecutando page.goto()...")
            page.goto(url, timeout=60_000)
            logger.debug("✅ Navegación inicial completada", current_url=page.url)

            logger.debug("⏳ Esperando carga completa de página...")
            self._wait_for_page_load(page)
            logger.info(f"✅ Navegación a página de login exitosa", url=url)
        except Exception as e:
            logger.error(f"❌ Error conectando a Acumbamail",
                        url=url,
                        error=str(e),
                        error_type=type(e).__name__)
            notify("Connection Error", f"Error: Could not connect to Acumbamail: {e}", "error")
            raise AuthenticationError(
                f"Failed to connect to Acumbamail: {e}",
                context={"url": url}
            ) from e

    def _is_already_authenticated(self, page: Page, url_base: str) -> bool:
        """Check if user is already authenticated with multiple verification methods."""
        current_url = page.url
        logger.debug("🔍 Verificando autenticación múltiple", current_url=current_url)

        # Method 1: URL verification
        is_not_login_page = not ("login" in current_url.lower())

        # Method 2: Look for authenticated user elements
        has_user_elements = False
        try:
            # Look for elements that only appear when authenticated
            user_indicators = [
                page.get_by_text("Mi cuenta"),
                page.get_by_text("Cerrar sesión"),
                page.get_by_text("Ir a la herramienta"),
                page.locator(".user-menu"),
                page.locator("[data-testid*='user']"),
                page.locator(".username")
            ]

            for indicator in user_indicators:
                if indicator.is_visible(timeout=2000):
                    has_user_elements = True
                    logger.debug(f"✅ Indicador de autenticación encontrado: {indicator}")
                    break

        except Exception as e:
            logger.debug(f"⚠️ Error verificando indicadores de usuario: {e}")

        # Method 3: Check for dashboard/main content
        has_dashboard_content = False
        try:
            dashboard_indicators = [
                page.get_by_text("Panel de control"),
                page.get_by_text("Newsletter"),
                page.get_by_text("Campañas"),
                page.get_by_text("Estadísticas"),
                page.locator(".dashboard"),
                page.locator(".main-content")
            ]

            for indicator in dashboard_indicators:
                if indicator.is_visible(timeout=2000):
                    has_dashboard_content = True
                    logger.debug(f"✅ Indicador de dashboard encontrado: {indicator}")
                    break

        except Exception as e:
            logger.debug(f"⚠️ Error verificando dashboard: {e}")

        # Combine all methods
        is_authenticated = is_not_login_page and (has_user_elements or has_dashboard_content)

        logger.debug("🔍 Resultados verificación autenticación",
                    current_url=current_url,
                    is_not_login_page=is_not_login_page,
                    has_user_elements=has_user_elements,
                    has_dashboard_content=has_dashboard_content,
                    is_authenticated=is_authenticated)

        if is_authenticated:
            logger.info("✅ Usuario ya autenticado (múltiples indicadores positivos)")
        else:
            logger.debug("⚠️ Usuario no autenticado o verificación fallida")

        return is_authenticated

    def _accept_cookies_if_present(self, page: Page) -> None:
        """Enhanced cookie acceptance focusing on Usercentrics (Acumbamail's cookie system)."""
        logger.info("🍪 Intentando aceptar cookies de Usercentrics")

        # Wait a brief moment for cookie popup to appear
        logger.debug("⏳ Esperando popup de cookies (1s)...")
        page.wait_for_timeout(1000)

        # Strategy 1: Usercentrics specific selectors (Acumbamail uses Usercentrics)
        usercentrics_selectors = [
            # Usercentrics standard buttons
            'button[data-testid="uc-accept-all-button"]',
            'button[id*="accept-all"]',
            'button[class*="accept-all"]',
            '#usercentrics-root button:has-text("Aceptar todas")',
            '#usercentrics-root button:has-text("Accept all")',
            'button:has-text("Aceptar todas las cookies")',
            'button:has-text("Accept all cookies")',
        ]

        # Try Usercentrics specific selectors first (most likely)
        for selector in usercentrics_selectors:
            try:
                logger.debug(f"🔍 Probando selector Usercentrics: {selector}")
                element = page.locator(selector).first

                if element.is_visible(timeout=2000):
                    logger.debug(f"✅ Botón Usercentrics encontrado: {selector}")
                    element.click(timeout=5000)
                    logger.info(f"✅ Cookies Usercentrics aceptadas con: {selector}")
                    page.wait_for_timeout(1000)
                    logger.success("🎉 Popup de cookies manejado exitosamente")
                    return

            except Exception as e:
                logger.debug(f"⚠️ Selector Usercentrics falló: {selector} - {type(e).__name__}")
                continue

        # Strategy 2: Generic role-based selectors (backup)
        generic_selectors = [
            ("button", "Aceptar todas"),
            ("button", "Accept all"),
            ("button", "Aceptar"),
        ]

        for selector_type, selector_value in generic_selectors:
            try:
                logger.debug(f"🔍 Probando selector genérico: {selector_type}='{selector_value}'")
                element = page.get_by_role(selector_type, name=selector_value).first

                if element.is_visible(timeout=2000):
                    logger.debug(f"✅ Botón genérico encontrado: {selector_value}")
                    element.click(timeout=5000)
                    logger.info(f"✅ Cookies aceptadas con selector genérico: {selector_value}")
                    page.wait_for_timeout(1000)
                    logger.success("🎉 Popup de cookies manejado exitosamente")
                    return

            except Exception as e:
                logger.debug(f"⚠️ Selector genérico falló: {selector_value} - {type(e).__name__}")
                continue

        # Strategy 3: Try ESC key to dismiss
        logger.debug("🔍 Intentando cerrar con ESC...")
        try:
            page.keyboard.press('Escape')
            page.wait_for_timeout(500)
        except:
            pass

        # Log final status
        logger.info("ℹ️ No se encontró popup de cookies visible")
        logger.debug("ℹ️ Esto es normal si las cookies ya fueron aceptadas")
        logger.info("🔓 Continuando con el flujo de autenticación")

    def _check_authentication_status(self, page: Page) -> bool:
        """Check if user is already authenticated."""
        logger.info("🔐 Verificando estado de autenticación")
        logger.debug("🌐 URL actual al verificar", url=page.url)
        try:
            # Look for navigation with tools link
            logger.debug("🔍 Buscando enlace 'Ir a la herramienta' en navegación")
            nav_element = page.get_by_role("navigation")
            btn_tools = nav_element.get_by_role("link", name="Ir a la herramienta")

            # Verify the element is visible before clicking
            logger.debug("⏳ Verificando visibilidad del enlace (timeout: 10s)")
            is_visible = btn_tools.is_visible(timeout=10000)
            if not is_visible:
                logger.info("🔓 Enlace 'Ir a la herramienta' no visible - no autenticado")
                return False

            logger.debug("✅ Enlace 'Ir a la herramienta' encontrado, haciendo clic...")
            self._wait_for_page_load(page)
            btn_tools.click(timeout=30_000)
            logger.debug("⏳ Esperando carga después del clic...")
            self._wait_for_page_load(page)
            logger.info("✅ Usuario ya autenticado - navegación exitosa")
            logger.debug("🌐 URL después de clic", url=page.url)
            return True

        except PWTimeoutError as e:
            logger.info("⏱️ Timeout verificando autenticación",
                       error=str(e),
                       timeout="10s")
            logger.info("🔓 Botón 'Ir a la herramienta' no encontrado - no autenticado")
            return False
        except Exception as e:
            logger.error(f"❌ Error inesperado verificando autenticación",
                        error=str(e),
                        error_type=type(e).__name__)
            logger.info("🔓 Asumiendo no autenticado, procediendo con login")
            return False

    def _perform_login(self, page: Page, username: str, password: str) -> None:
        """Perform the actual login process."""
        logger.info("🔐 No autenticado. Procediendo con login...")
        logger.debug("👤 Login para usuario", username=username)
        # notify("Authentication", "Credentials required, starting login", "info")

        try:
            # Step 1: Click login button
            logger.info("📌 PASO 1: Localizando y haciendo clic en botón 'Entra'")
            logger.debug("🌐 URL actual antes de buscar botón", url=page.url)
            try:
                logger.debug("🔍 Buscando botón 'Entra' con timeout de 10s...")
                login_btn = page.get_by_role("link", name="Entra")

                # Verify button is visible
                logger.debug("⏳ Verificando visibilidad del botón...")
                is_visible = login_btn.is_visible(timeout=10000)
                if not is_visible:
                    logger.error("❌ ERROR PASO 1: Botón 'Entra' no visible")
                    raise AuthenticationError("Login button not found or not visible")

                logger.debug("✅ Botón 'Entra' encontrado y visible, haciendo clic...")
                login_btn.click()
                logger.debug("⏳ Esperando carga domcontentloaded después del clic...")
                page.wait_for_load_state("domcontentloaded", timeout=15000)
                logger.debug("✅ Click en 'Entra' realizado, DOM cargado")
                logger.debug("🌐 URL después de clic", url=page.url)

                # Check for cookie popups after clicking login button
                logger.debug("🍪 Verificando popups de cookies después de clic en 'Entra'")
                self._accept_cookies_if_present(page)
                logger.debug("✅ Cookies manejadas, continuando...")

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

            # Additional cookie check before form filling
            logger.debug("🍪 Verificación adicional de cookies antes de llenar formulario")
            self._accept_cookies_if_present(page)

            try:
                logger.debug("🔍 Buscando campo 'Correo electrónico' (timeout: 10s)...")
                email_input = page.get_by_role("textbox", name="Correo electrónico")
                email_input.wait_for(state="visible", timeout=10000)
                logger.debug(f"✅ Campo email encontrado, llenando con: {username}")
                email_input.fill(username)
                logger.debug("✅ Correo electrónico llenado correctamente")

                logger.debug("🔍 Buscando campo 'Contraseña' (timeout: 10s)...")
                password_input = page.get_by_role("textbox", name="Contraseña")
                password_input.wait_for(state="visible", timeout=10000)
                logger.debug("✅ Campo contraseña encontrado, llenando...")
                password_input.fill(password)
                logger.debug("✅ Contraseña llenada correctamente")

                logger.debug("🔍 Buscando checkbox 'Mantener sesión iniciada' (timeout: 5s)...")
                keepme_checkbox = page.locator('label[for="keepme-logged"]')
                keepme_checkbox.wait_for(state="visible", timeout=5000)
                if keepme_checkbox.is_visible():
                    logger.debug("✅ Checkbox encontrado, marcando...")
                    keepme_checkbox.click()
                    logger.debug("✅ Checkbox 'Mantener sesión iniciada' marcado")
                else:
                    logger.warning("⚠️ Checkbox 'Mantener sesión iniciada' no encontrado")
                    logger.debug("ℹ️ Continuando sin marcar checkbox")

                logger.info("✅ Formulario de login completado exitosamente")
                logger.debug("📋 Resumen del formulario", username=username, keep_session=keepme_checkbox.is_visible() if keepme_checkbox else False)

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
                logger.debug("🔍 Buscando botón 'Entrar' (timeout: 10s)...")
                submit_btn = page.get_by_role("button", name="Entrar")
                submit_btn.wait_for(state="visible", timeout=10000)
                logger.debug("✅ Botón 'Entrar' encontrado y visible")
                logger.debug("⏳ Preparando envío de formulario...")

                # Use expect_navigation for robust navigation handling
                logger.debug("🔄 Ejecutando submit con expect_navigation...")
                with page.expect_navigation(wait_until="domcontentloaded"):
                    submit_btn.click()
                    logger.debug("✅ Click en 'Entrar' ejecutado")
                    logger.debug("⏳ Esperando navegación post-submit...")
                    self._wait_for_page_load(page)

                logger.info("✅ Formulario de login enviado exitosamente")
                logger.debug("🌐 URL después de login", url=page.url)
                logger.success("🎉 Login completado - usuario autenticado")

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
            logger.info("🎉 Proceso de login completado exitosamente")
            logger.success("✅ Usuario autenticado en Acumbamail", username=username)
            # notify("Authentication", "Login completed successfully", "info")

        except AuthenticationError:
            # Re-raise AuthenticationError as is
            logger.error("❌ Error de autenticación capturado, propagando...")
            raise
        except Exception as e:
            logger.error(f"❌ ERROR INESPERADO en proceso de login",
                        error=str(e),
                        error_type=type(e).__name__,
                        username=username)
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

    def refresh_session(self, page: Page, context: BrowserContext) -> bool:
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
            # notify("Session", "Session expired, re-authenticating...", "warning")

            # Call the main authenticate method to re-login
            self.authenticate(page, context)

            logger.success("✅ Sesión refrescada exitosamente")
            # notify("Session", "Session refreshed successfully", "info")
            return True

        except Exception as e:
            logger.error(f"❌ Error refrescando sesión: {e}")
            notify("Session Error", f"Failed to refresh session: {e}", "error")
            return False


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