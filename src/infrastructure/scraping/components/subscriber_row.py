"""
SubscriberRowComponent — extracción de fila individual de la tabla de suscriptores.

Encapsula el acceso nth() a los 4 campos de la fila:
[correo, lista, estado, calidad].
El único lugar donde se usa nth() en la capa de suscriptores.
"""

from playwright.sync_api import Page, Locator
from src.infrastructure.scraping.models.suscriptores import SubscriberTableData
from src.infrastructure.scraping.utils.selectors import SubscriberSelectors
from src.shared.logging.logger import get_logger

logger = get_logger()


class SubscriberRowComponent:
    def __init__(self, element: Locator, page: Page):
        self._element = element
        self._page = page
        self._selectors = SubscriberSelectors()

    def is_valid_row(self) -> bool:
        try:
            first_div = self._element.locator("> div").first
            text = first_div.inner_text()
            return bool(text and "@" in text)
        except Exception:
            return False

    def extract_table_data(self) -> SubscriberTableData:
        field_divs = self._element.locator("> div")
        count = field_divs.count()

        correo = self._get_text(field_divs, self._selectors.field_correo_index)
        lista = self._get_text(field_divs, self._selectors.field_lista_index)
        estado = self._get_text(field_divs, self._selectors.field_estado_index)
        calidad = self._get_text(field_divs, self._selectors.field_calidad_index)

        return SubscriberTableData(correo=correo, lista=lista, estado=estado, calidad=calidad)

    def _get_text(self, field_divs: Locator, index: int) -> str:
        try:
            if index < field_divs.count():
                return field_divs.nth(index).inner_text().strip()
        except Exception:
            pass
        return ""
