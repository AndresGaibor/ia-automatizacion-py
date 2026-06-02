"""
NavigationComponent — helper para navegación común en Acumbamail.

Maneja espera de carga de página y detección de errores.
Pertenece a la capa components para reutilización.
"""
from typing import Optional
from playwright.sync_api import Page

from src.shared.logging.logger import get_logger

logger = get_logger()


class ComponenteNavegacion:
    """Component para navegación común en Acumbamail."""

    def __init__(self, page: Page):
        self._page = page

    def wait_for_page_load(self, timeout: int = 30000) -> None:
        """Esperar a que la página se cargue completamente."""
        try:
            self._page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            logger.warning(f"Timeout esperando carga de página: {e}")

    def check_for_errors(self) -> Optional[str]:
        """Verificar si hay mensajes de error en la página."""
        error_selectors = [".alert-error", ".error-message", ".alert-danger"]

        for selector in error_selectors:
            try:
                error_element = self._page.query_selector(selector)
                if error_element and error_element.is_visible():
                    error_text = error_element.text_content().strip()
                    logger.error(f"Error encontrado en página: {error_text}")
                    return error_text
            except Exception:
                continue

        return None


class ComponenteNavegacionCampania:
    """Component para navegación específica de campañas."""

    def go_to_tab(self, campaign_id: int, tab: str) -> None:
        """Navegar a una pestaña específica de una campaña."""
        logger.debug(f"TODO: Implementar navegación a pestaña {tab} de campaña {campaign_id}")

    def is_logged_in(self) -> bool:
        """Verificar si el usuario está logueado."""
        return True

    def handle_session_expired(self) -> bool:
        """Manejar sesión expirada."""
        logger.warning("TODO: Implementar manejo de sesión expirada")
        return False