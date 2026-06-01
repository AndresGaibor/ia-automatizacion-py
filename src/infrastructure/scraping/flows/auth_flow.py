from playwright.sync_api import Page, BrowserContext
from src.utils import load_config, storage_state_path
from src.infrastructure.scraping.pages.login_page import LoginPage
from src.infrastructure.scraping.pages.reports_page import ReportsPage
from src.shared.logging.logger import get_logger
from src.core.authentication.exceptions import AuthenticationFailedError, SessionSaveError

logger = get_logger()


class AuthFlow:
    def __init__(self, page: Page, context: BrowserContext):
        self._page = page
        self._context = context

    def ensure_authenticated(self) -> None:
        config = load_config()
        username = config.get("user", "")
        password = config.get("password", "")
        url = config.get("url", "")
        url_base = config.get("url_base", "")

        if not username or username == "usuario@correo.com":
            raise ValueError("Usuario no configurado en config.yaml")
        if not password or password == "clave":
            raise ValueError("Contraseña no configurada en config.yaml")

        logger.info("Iniciando proceso de autenticación", user=username)
        self._navigate_to_home(url)

        if f"{url_base}/" != self._page.url:
            if self._try_restore_existing_session():
                return
        else:
            login_page = LoginPage(self._page, url_base)
            login_page.handle_cookies(agresivo=True)
            if login_page.is_logged_in():
                self._save_session()
                return

        self._perform_login(username, password, url_base)

    def _navigate_to_home(self, url: str) -> None:
        self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        self._page.wait_for_load_state("domcontentloaded", timeout=45_000)
        self._page.wait_for_load_state("networkidle", timeout=45_000)

    def _try_restore_existing_session(self) -> bool:
        logger.info("Verificando sesión existente")
        login_page = LoginPage(self._page, "")
        resultado = login_page.session_guard.verify_login()

        if resultado["success"]:
            logger.info("Sesión existente válida", metodo=resultado["method"])
            self._save_session()
            return True
        logger.warning("Sesión existente no válida")
        return False

    def _perform_login(self, username: str, password: str, url_base: str) -> None:
        login_page = LoginPage(self._page, url_base)
        login_page.handle_cookies(agresivo=True)

        if login_page.is_logged_in():
            self._save_session()
            return

        logger.info("No autenticado, procediendo con login")
        login_page.do_login(username, password)
        self._page.wait_for_load_state("networkidle", timeout=30_000)

        resultado = login_page.session_guard.verify_login()
        if not resultado["success"]:
            raise AuthenticationFailedError(f"Login completado pero verificación falló: {resultado['details']}")

        self._save_session()
        logger.info("Proceso de autenticación completado")

    def _save_session(self) -> None:
        try:
            self._context.storage_state(path=storage_state_path())
            logger.info("Estado de sesión guardado")
        except Exception as e:
            raise SessionSaveError(f"No se pudo guardar la sesión: {e}")


class ScrapingSession:
    def __init__(self, max_retries: int = 2):
        self._max_retries = max_retries

    def run_with_recovery(self, page: Page, config, operation_fn):
        from src.shared.utils.legacy_utils import is_on_login_page
        from src.autentificacion import login
        from src.infrastructure.scraping.pages.reports_page import ReportsPage

        last_exception = None
        for attempt in range(self._max_retries + 1):
            try:
                if attempt > 0 and is_on_login_page(page):
                    logger.warning("Sesión expirada, re-autenticando", intento=attempt + 1)
                    login(page, page.context)
                    ReportsPage(page).navigate_to()

                result = operation_fn(page)
                if attempt > 0:
                    logger.info("Operación recuperada", reintentos=attempt)
                return result
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                is_session_error = (
                    "session expired" in error_msg
                    or "login" in error_msg
                    or "unauthorized" in error_msg
                    or "timeout" in error_msg
                    or is_on_login_page(page)
                )
                if is_session_error and attempt < self._max_retries:
                    logger.warning("Error de sesión, reintentando", intento=attempt + 1)
                    continue
                break

        raise last_exception
