"""
ReportsPage - Page Object para la página de reportes de Acumbamail.

Encapsula paginación (optimizar items/página, calcular total páginas, navegar siguiente)
y acceso a filas de campañas válidas.
"""

import re
from playwright.sync_api import Page, Locator, TimeoutError as PWTimeoutError
from src.infrastructure.scraping.pages.base_page import BasePage
from src.infrastructure.scraping.components.campaign_row import CampaignRow
from src.infrastructure.scraping.utils.selectors import ReportPageSelectors
from src.shared.logging.logger import get_logger

logger = get_logger()


class ReportsPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page, url="")
        self._selectors = ReportPageSelectors()

    def navigate_to(self) -> None:
        """Navega a la sección de reportes."""
        self._page.click(self._selectors.reports_link)
        self._page.wait_for_load_state("networkidle", timeout=60000)
        self._page.wait_for_timeout(2000)

    def optimize_items_per_page(self) -> None:
        """Optimiza a máximo items por página (200) para reducir páginas a procesar."""
        try:
            items_selector = self._page.locator("select").filter(has=self._page.locator("option", has_text="15"))
            if items_selector.count() > 0:
                ultimo_option = items_selector.locator("option").last
                value_ultimo = ultimo_option.get_attribute("value")
                items_selector.select_option(value=value_ultimo)
                self._page.wait_for_load_state("domcontentloaded", timeout=15000)
                self._page.wait_for_timeout(2000)
                logger.debug(f"✅ Items/página optimizado a: {value_ultimo}")
        except Exception as e:
            logger.warning(f"⚠️ Error optimizando items/página: {e}")

    def get_total_pages(self) -> int:
        """Calcula total de páginas desde "de X elementos" o fallback a navegación."""
        # Intentar desde "de X elementos"
        try:
            elementos_info = self._page.locator("span.font-color-darkblue-1").filter(
                has_text=re.compile(r"elementos", re.IGNORECASE)
            )
            if elementos_info.count() > 0:
                target = elementos_info.last if elementos_info.count() > 1 else elementos_info.first
                texto = target.inner_text(timeout=5000)
                numeros = re.findall(r"\d[\d\.,]*", texto)
                if numeros:
                    total_elementos = int(numeros[-1].replace(".", "").replace(",", ""))
                    items_por_pagina = self._detect_items_per_page()
                    total_paginas = (total_elementos + items_por_pagina - 1) // items_por_pagina
                    logger.debug(f"📊 {total_elementos} elementos, {items_por_pagina}/pág = {total_paginas} páginas")
                    return max(1, total_paginas)
        except Exception as e:
            logger.debug(f"⚠️ Error calculando páginas desde elementos: {e}")

        # Fallback: navegación
        try:
            navegacion = self._page.locator("ul").filter(has=self._page.locator("li").locator("a", has_text="1")).last
            if navegacion.count() > 0:
                texto = navegacion.locator("li").last.inner_text(timeout=5000)
                if texto.isdigit():
                    return int(texto)
        except Exception:
            pass

        logger.debug("⚠️ No se pudo determinar total de páginas, asumiendo 1")
        return 1

    def get_valid_campaign_rows(self) -> list[CampaignRow]:
        """Retorna lista de CampaignRow válidos en la página actual.

        Filtra elementos por criterios de campaña real (fecha, números, longitud, saltos).
        """
        self._page.wait_for_selector("ul li", timeout=15000)
        self._page.wait_for_timeout(1000)

        all_items = self._page.locator("li").filter(has=self._page.locator('a[href*="/report/campaign/"]'))
        count = all_items.count()
        logger.debug(f"📋 Total elementos con links de campañas: {count}")

        valid_rows = []
        for i in range(count):
            element = all_items.nth(i)
            row = CampaignRow(element, self._page)
            if row.is_valid_row():
                valid_rows.append(row)
                logger.debug(f"✅ Campaña válida en índice {i}")

        logger.debug(f"✅ Filas válidas encontradas: {len(valid_rows)}")
        return valid_rows

    def navigate_to_next_page(self, current_page: int) -> bool:
        """Navega a la siguiente página. Retorna True si exitoso."""
        siguiente = current_page + 1
        try:
            navegacion = (
                self._page.locator("ul").filter(has=self._page.locator("li").locator("a", has_text=f"{siguiente}")).last
            )
            enlace = navegacion.locator("a", has_text=f"{siguiente}").first

            if enlace.count() > 0:
                enlace.wait_for(timeout=8000)
                enlace.click()
                self._page.wait_for_load_state("domcontentloaded", timeout=15000)
                self._page.wait_for_timeout(2000)
                logger.debug(f"➡️ Navegado a página {siguiente}")
                return True
        except Exception as e:
            logger.warning(f"❌ Error navegando a página {siguiente}: {e}")
        return False

    # --- Private helpers ---

    def _detect_items_per_page(self) -> int:
        """Detecta items por página actual desde el valor seleccionado del <select>."""
        try:
            select = (
                self._page.locator("select").filter(has=self._page.locator("option", has_text=re.compile(r"\d+"))).first
            )
            if select.count() > 0:
                selected = select.input_value()
                if "items_per_page=" in selected:
                    return int(selected.split("items_per_page=")[1].split("&")[0])
        except Exception:
            pass

        # Fallback: contar campañas visibles
        try:
            visible = self._page.locator("li").filter(has=self._page.locator('a[href*="/report/campaign/"]')).count()
            if visible > 0:
                return visible
        except Exception:
            pass

        return 15  # Default de Acumbamail

    def extract_email_url_quick(self, campaign_id: int) -> str:
        """Extrae la URL del correo de una campaña de forma ultra-rápida.

        Navega sin esperar networkidle, apenas cargue extrae la URL del regex.

        Args:
            campaign_id: ID de la campaña

        Returns:
            URL del correo clickacm.com o string vacío si no se encuentra.
        """
        import re

        try:
            url = f"https://acumbamail.com/report/campaign/{campaign_id}/subscribers/"

            self._page.goto(url, wait_until="commit", timeout=30000)

            try:
                email_link = self._page.get_by_text("Ver email").get_attribute("href", timeout=3000)
                if email_link and "clickacm.com" in email_link:
                    return email_link
            except PWTimeoutError:
                pass

            try:
                page_content = self._page.content()
                pattern = r"(https://clickacm\.com/show/[a-zA-Z0-9-]+/)"
                matches = re.findall(pattern, page_content)
                if matches:
                    return matches[0]
            except Exception:
                pass

            return ""

        except Exception:
            return ""
