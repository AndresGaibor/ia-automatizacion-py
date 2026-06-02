"""
FilterSelectorComponent — selector de filtro #query-filter en página de suscriptores.

Encapsula selección de filtro (Abiertos, Hard bounces, No abiertos)
y espera de actualización de la tabla después de la selección.
"""

from playwright.sync_api import Page
from src.infrastructure.scraping.utils.selectors import SubscriberSelectors
from src.shared.logging.logger import get_logger

logger = get_logger()


class ComponenteSelectorFiltro:
    def __init__(self, page: Page):
        self._page = page
        self._selectors = SubscriberSelectors()

    def select_filter(self, label: str) -> bool:
        try:
            select_filtro = self._page.locator(self._selectors.filter_select)
            select_filtro.wait_for(timeout=10000)
            select_filtro.select_option(label=label)
            self._page.wait_for_load_state("domcontentloaded", timeout=15000)
            self._page.wait_for_timeout(2000)
            logger.debug(f"✅ Filter '{label}' selected")
            return True
        except Exception as e:
            logger.error(f"Error selecting filter '{label}': {e}")
            return False

    def select_hard_bounces(self) -> bool:
        return self.select_filter(self._selectors.filter_option_hard_bounces)

    def select_no_abiertos(self) -> bool:
        return self.select_filter(self._selectors.filter_option_no_abiertos)

    def select_abiertos(self) -> bool:
        return self.select_filter(self._selectors.filter_option_abiertos)
