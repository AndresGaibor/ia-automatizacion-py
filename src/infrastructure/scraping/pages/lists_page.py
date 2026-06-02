"""
ListsPage — página de gestión de listas de Acumbamail.

Navega a la sección de listas y encapsula:
- navegación inicial (url_base + url)
- autenticación via LoginPage
- click en link "Listas"
"""

from playwright.sync_api import Page
from src.infrastructure.scraping.pages.base_page import BasePage
from src.infrastructure.scraping.pages.login_page import LoginPage
from src.shared.logging.logger import get_logger

logger = get_logger()


class ListsPage(BasePage):
    def __init__(self, page: Page, base_url: str, url: str):
        super().__init__(page, url)
        self._base_url = base_url
        self._url = url
        self._login_page = LoginPage(page, base_url)

    def navigate_to_lists(self) -> bool:
        """
        Navega a la sección de listas:
        1. Navega a url_base
        2. Navega a url (página principal de newsletters)
        3. Hace click en el link "Listas"

        Returns:
            True si la navegación fue exitosa
        """
        try:
            logger.info("🌐 Navegando a la sección de listas")

            logger.info(f"   → Navegando a URL base: {self._base_url}")
            self._page.goto(self._base_url, wait_until="domcontentloaded", timeout=60000)

            logger.info(f"   → Navegando a URL principal: {self._url}")
            self._page.goto(self._url, wait_until="domcontentloaded", timeout=60000)

            logger.info("   → Click en link 'Listas'")
            self._page.get_by_role("link", name="Listas").first.click()
            self._page.wait_for_load_state("domcontentloaded", timeout=30000)

            logger.info("✅ Navegación a sección de listas completada")
            return True

        except Exception as e:
            logger.error(f"❌ Error navegando a la sección de listas: {e}")
            return False

    def authenticate(self) -> bool:
        """
        Ejecuta el proceso de autenticación usando LoginPage POM.

        Returns:
            True si la autenticación fue exitosa
        """
        from src.autentificacion import login
        from playwright.sync_api import BrowserContext

        try:
            logger.info("🔐 Iniciando autenticación")
            context = self._page.context
            login(self._page, context)
            logger.info("✅ Autenticación exitosa")
            return True
        except Exception as e:
            logger.error(f"❌ Error en autenticación: {e}")
            return False