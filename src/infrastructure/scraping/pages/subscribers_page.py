"""
SubscribersPage — página de detalle de suscriptores de una campaña.

Navega a /report/campaign/{id}/subscribers/ y encapsula:
- navegación a detalle
- espera de tabla de suscriptores
- acceso a filas via SubscriberRowComponent
"""

from playwright.sync_api import Page
from src.infrastructure.scraping.pages.base_page import BasePage
from src.infrastructure.scraping.components.subscriber_row import SubscriberRowComponent
from src.infrastructure.scraping.utils.selectors import SubscriberSelectors
from src.shared.logging.logger import get_logger

logger = get_logger()


class SubscribersPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page, url="")
        self._selectors = SubscriberSelectors()
        self._subscribers_url_template = "{base}/report/campaign/{id}/subscribers/"

    def navigate_to_detail(self, campaign_id: int, base_url: str = "https://acumbamail.com") -> bool:
        try:
            detail_url = f"{base_url}/report/campaign/{campaign_id}/"
            self._page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
            self._page.wait_for_load_state("domcontentloaded", timeout=20000)

            link = self._page.get_by_role("link", name="Detalles suscriptores")
            link.wait_for(timeout=15000)
            link.click()
            self._page.wait_for_load_state("domcontentloaded", timeout=20000)
            self._page.wait_for_timeout(2000)
            return True
        except Exception as e:
            logger.error(f"Error navigating to subscriber detail: {e}")
            return False

    def navigate_to_subscribers(self, campaign_id: int, base_url: str = "https://acumbamail.com") -> bool:
        url = self._subscribers_url_template.format(base=base_url, id=campaign_id)
        try:
            self._page.goto(url, wait_until="networkidle", timeout=60000)
            self._page.wait_for_load_state("networkidle", timeout=30000)
            self._page.wait_for_timeout(2000)
            return True
        except Exception as e:
            logger.error(f"Error navigating to subscribers page: {e}")
            return False

    def wait_for_table(self) -> bool:
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=20000)
            self._page.wait_for_timeout(3000)
            tabla = self._page.locator("ul").filter(
                has=self._page.locator("li", has_text=self._selectors.subscriber_table_header_text)
            )
            if tabla.count() == 0:
                logger.warning("Subscriber table not found")
                return False
            return True
        except Exception as e:
            logger.error(f"Error waiting for subscriber table: {e}")
            return False

    def get_row_count(self) -> int:
        tabla = self._page.locator("ul").filter(
            has=self._page.locator("li", has_text=self._selectors.subscriber_table_header_text)
        )
        rows = tabla.locator(self._selectors.subscriber_row_li)
        return max(0, rows.count() - 1)

    def extract_all_rows(self) -> list[SubscriberRowComponent]:
        tabla = self._page.locator("ul").filter(
            has=self._page.locator("li", has_text=self._selectors.subscriber_table_header_text)
        )
        rows_locator = tabla.locator(self._selectors.subscriber_row_li)
        total = rows_locator.count()
        result = []

        for i in range(1, total):
            element = rows_locator.nth(i)
            row = SubscriberRowComponent(element, self._page)
            if row.is_valid_row():
                result.append(row)

        logger.debug(f"Extracted {len(result)} valid subscriber rows")
        return result

    def navigate_to_next_page(self, current_page: int) -> bool:
        from src.shared.utils.legacy_utils import navegar_siguiente_pagina

        return navegar_siguiente_pagina(self._page, current_page)

    def get_total_pages(self) -> int:
        from src.shared.utils.legacy_utils import obtener_total_paginas

        return obtener_total_paginas(self._page)

    def get_campaign_email_url(self, campaign_id: int) -> str:
        """
        Obtiene la URL del correo de una campaña (botón "Ver email").
        Retorna la URL de clickacm.com o string vacío si no se encuentra.
        """
        import re
        try:
            url = f"https://acumbamail.com/report/campaign/{campaign_id}/subscribers/"
            self._page.goto(url, wait_until="networkidle", timeout=60000)
            self._page.wait_for_load_state("networkidle", timeout=30000)
            self._page.wait_for_timeout(2000)

            from src.shared.utils.legacy_utils import is_on_login_page
            if is_on_login_page(self._page):
                logger.warning(f"Sesión expirada al obtener URL de correo de campaña {campaign_id}")
                return ""

            try:
                email_link = self._page.get_by_text("Ver email").get_attribute("href", timeout=5000)
                if email_link and "clickacm.com" in email_link:
                    return email_link
            except Exception:
                pass

            page_content = self._page.content()
            pattern = r'(https://clickacm\.com/show/[a-zA-Z0-9-]+/)'
            matches = re.findall(pattern, page_content)
            if matches:
                return matches[0]

            return ""

        except Exception as e:
            logger.error(f"Error extrayendo URL de email de campaña {campaign_id}: {e}")
            return ""
