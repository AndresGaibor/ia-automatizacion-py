"""
ListsNavigationPage — Page Object para navegación a sección de listas.

Maneja:
- Navegación inicial (url_base + url)
- Autenticación via LoginPage
- Click en link "Listas"
- Creación de listas
"""
from playwright.sync_api import Page

from src.infrastructure.scraping.pages.base_page import PaginaBase
from src.infrastructure.scraping.pages.login_page import PaginaLogin
from src.shared.logging.logger import get_logger

logger = get_logger()


class PaginaNavegacionListas(PaginaBase):
    """Page Object para navegación a sección de listas."""

    def __init__(self, page: Page, base_url: str, url: str):
        super().__init__(page, url)
        self._base_url = base_url
        self._url = url

    def navigate_to_lists(self) -> bool:
        """Navega a la sección de listas."""
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
        """Ejecuta el proceso de autenticación."""
        try:
            logger.info("🔐 Iniciando autenticación")
            context = self._page.context
            from src.autentificacion import login
            login(self._page, context)
            logger.info("✅ Autenticación exitosa")
            return True

        except Exception as e:
            logger.error(f"❌ Error en autenticación: {e}")
            return False

    def click_nueva_lista(self) -> bool:
        """Hace click en el botón 'Nueva Lista'."""
        try:
            btn_nueva_lista = self._page.locator(
                "a.font-color-white-1", has_text="Nueva Lista"
            )
            btn_nueva_lista.wait_for(state="visible", timeout=10000)
            btn_nueva_lista.click()
            return True
        except Exception as e:
            logger.error(f"❌ Error click en 'Nueva Lista': {e}")
            return False

    def fill_nombre_lista(self, nombre_lista: str) -> bool:
        """Llena el campo de nombre de lista."""
        try:
            name_input = self._page.locator("#name")
            name_input.wait_for(state="visible", timeout=10000)
            name_input.fill("")
            name_input.fill(nombre_lista)
            return True
        except Exception as e:
            logger.error(f"❌ Error rellenando nombre de lista: {e}")
            return False

    def click_crear_lista(self) -> bool:
        """Hace click en el botón 'Crear' para crear la lista."""
        try:
            self._page.get_by_role("button", name="Crear").click()
            return True
        except Exception as e:
            logger.error(f"❌ Error click en 'Crear': {e}")
            return False

    def crear_lista(self, nombre_lista: str) -> bool:
        """Crea una nueva lista en Acumbamail."""
        try:
            logger.info(f"📝 Creando lista: '{nombre_lista}'")

            if not self.click_nueva_lista():
                return False

            logger.info(f"   ✏️  Ingresando nombre: '{nombre_lista}'")
            if not self.fill_nombre_lista(nombre_lista):
                return False

            logger.info("   🖱️  Click en 'Crear'")
            if not self.click_crear_lista():
                return False

            logger.success(f"✅ Lista '{nombre_lista}' creada exitosamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error creando lista: {e}")
            return False