import logging
from playwright.sync_api import BrowserContext, Page
from .utils import load_config, storage_state_path
from .shared.logging.logger import get_logger
from .core.authentication.exceptions import CookiePopupError, AuthenticationFailedError, SessionSaveError
from .infrastructure.scraping.pages.login_page import LoginPage

logger = get_logger()


def esperar_carga_pagina(page: Page, timeout: int = 45_000, use_networkidle: bool = False):
    """
    Espera a que la página cargue completamente.

    Args:
        page: Página de Playwright
        timeout: Timeout en milisegundos
        use_networkidle: Si True, espera networkidle además de domcontentloaded (más lento pero más seguro)
    """
    logger.info("⏳ Esperando carga de página", timeout=timeout, networkidle=use_networkidle)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)

        if use_networkidle:
            page.wait_for_load_state("networkidle", timeout=timeout)
            logger.success("✅ Página cargada exitosamente (con networkidle)")
        else:
            logger.success("✅ Página cargada exitosamente")
    except Exception as e:
        logger.warning(f"Página tardó en cargar: {e}. Continuando...", error=str(e))


def aceptar_cookies(page: Page):
    """Acepta el popup de cookies usando la capa POM."""
    try:
        login_page = LoginPage(page, "")
        login_page.handle_cookies(agresivo=True)
    except Exception as e:
        logger.info(f"No se encontró el botón de cookies: {e}. Continuando...", error=str(e))


def autenticado(page: Page) -> bool:
    """Verifica si el usuario ya está autenticado usando la capa POM."""
    logger.info("🔐 Verificando estado de autenticación")
    try:
        login_page = LoginPage(page, "")
        return login_page.is_logged_in()
    except Exception as e:
        logger.error("❌ Error en verificación de autenticación", error=str(e))
        return False


def login(page: Page, context: BrowserContext):
    """Realiza login usando la capa POM (LoginPage)."""
    logger.info("🔐 Iniciando proceso de autenticación")
    config = load_config()
    username = config.get("user", "")
    password = config.get("password", "")
    url = config.get("url", "")
    url_base = config.get("url_base", "")

    if not username or username == "usuario@correo.com":
        logger.error("❌ Usuario no configurado en config.yaml", user=username)
        raise ValueError("Usuario no configurado en config.yaml")

    if not password or password == "clave":
        logger.error("❌ Contraseña no configurada en config.yaml", user=username)
        raise ValueError("Contraseña no configurada en config.yaml")

    logger.info(f"🔑 Iniciando proceso de login para usuario: {username}")

    try:
        logger.info(f"🌐 Navegando a URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        logger.info("✅ Navegación inicial completada (domcontentloaded)")
        esperar_carga_pagina(page, timeout=45_000, use_networkidle=True)
    except Exception as e:
        logger.error(f"❌ Error conectando a Acumbamail: {e}", url=url, error=str(e))
        raise

    login_page = LoginPage(page, url_base)

    if f"{url_base}/" != page.url:
        logger.info("🔍 Verificando que la sesión existente sea válida...")
        if login_page.is_logged_in():
            logger.success("✅ Sesión existente verificada correctamente")
            logger.info("💾 Guardando estado de sesión verificada...")
            try:
                context.storage_state(path=storage_state_path())
                logger.success("✅ Estado de sesión existente guardado correctamente")
                return
            except Exception as e:
                logger.error("❌ Error guardando estado de sesión existente", error=str(e))
                raise SessionSaveError(f"No se pudo guardar la sesión existente: {e}")
        else:
            logger.warning("⚠️ Sesión existente no válida, se requiere nuevo login")

    login_page.handle_cookies(agresivo=True)

    if login_page.is_logged_in():
        logger.success("✅ Ya estás autenticado y verificado.")
        logger.info("💾 Guardando estado de sesión ya autenticado...")
        try:
            context.storage_state(path=storage_state_path())
            logger.success("✅ Estado de sesión autenticado guardado correctamente")
            return
        except Exception as e:
            logger.error("❌ Error guardando estado de sesión autenticado", error=str(e))
            raise SessionSaveError(f"No se pudo guardar la sesión autenticada: {e}")

    logger.info("🔐 No estás autenticado. Procediendo con login...")

    login_page.do_login(username, password)

    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(2000)
    logger.success("✅ Sesión estabilizada")

    if not login_page.is_logged_in():
        logger.error("❌ Login no pudo ser verificado exitosamente", url=page.url)
        raise AuthenticationFailedError("Login completado pero verificación falló")

    logger.info("💾 Guardando estado de sesión verificado...")
    try:
        context.storage_state(path=storage_state_path())
        logger.success("✅ Estado de sesión verificado guardado correctamente")
    except Exception as e:
        logger.error("❌ Error guardando estado de sesión verificado", error=str(e))
        raise SessionSaveError(f"No se pudo guardar la sesión verificada: {e}")

    logger.success("✅ Proceso de autenticación completado y verificado")
