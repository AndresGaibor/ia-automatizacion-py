"""
ListsPage — fachada para página de gestión de listas.

Delega a:
- ListsNavigationPage para navegación y creación de listas
- ListUploadPage para subida de archivos y mapeo de columnas

Este archivo solo orquesta, no hace scraping directo.
"""
from playwright.sync_api import Page

from src.infrastructure.scraping.pages.base_page import PaginaBase
from src.infrastructure.scraping.pages.lists_navigation_page import PaginaNavegacionListas
from src.infrastructure.scraping.pages.list_upload_page import PaginaSubidaListas
from src.infrastructure.scraping.models.listas import ListUploadColumn
from src.shared.logging.logger import get_logger

logger = get_logger()


class PaginaListas(PaginaBase):
    """Fachada para gestión de listas - delega a pages específicas."""

    def __init__(self, page: Page, base_url: str, url: str):
        super().__init__(page, url)
        self._base_url = base_url
        self._url = url
        self._nav_page = PaginaNavegacionListas(page, base_url, url)
        self._upload_page = PaginaSubidaListas(page)

    def navigate_to_lists(self) -> bool:
        """Navega a la sección de listas."""
        return self._nav_page.navigate_to_lists()

    def authenticate(self) -> bool:
        """Ejecuta autenticación."""
        return self._nav_page.authenticate()

    def crear_lista(self, nombre_lista: str) -> bool:
        """Crea una nueva lista."""
        return self._nav_page.crear_lista(nombre_lista)

    def subir_archivo(self, archivo_csv: str) -> bool:
        """Sube archivo CSV."""
        return self._upload_page.subir_archivo(archivo_csv)

    def mapear_columna(self, columna: ListUploadColumn) -> bool:
        """Mapea una columna."""
        return self._upload_page.mapear_columna(columna)

    def click_siguiente(self) -> bool:
        """Click en siguiente."""
        return self._upload_page.click_siguiente()

    def verificar_mensaje_exito(self) -> bool:
        """Verifica mensaje de éxito."""
        return self._upload_page.verificar_mensaje_exito()

    def detectar_columnas_disponibles(self, total: int) -> list[int]:
        """Detecta columnas disponibles."""
        return self._upload_page.detectar_columnas_disponibles(total)
ListsPage = PaginaListas
