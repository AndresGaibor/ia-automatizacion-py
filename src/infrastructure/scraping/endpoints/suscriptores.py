"""
SubscribersScraper — scraper de suscriptores refactorizado hacia POM.

Delega a componentes POM (SubscribersPage, FilterSelectorComponent, SubscriberRowComponent)
para selector selection, table extraction y pagination.
Mantiene la API pública original para compatibilidad.
"""

from playwright.sync_api import Page
from typing import List, Tuple, Optional
from datetime import datetime

from ..models.suscriptores import (
    SubscriberScrapingData,
    SubscriberTableData,
    SubscriberFilterResult,
    CampaignSubscriberReport,
    ScrapingSession,
    SubscriberExtractionConfig,
)
from src.infrastructure.api.models.campanias import CampaignBasicInfo
from src.infrastructure.scraping.pages.subscribers_page import SubscribersPage
from src.infrastructure.scraping.components.filter_selector import FilterSelectorComponent
from src.infrastructure.scraping.flows.subscribers_flow import SubscribersFlow
from src.shared.utils.legacy_utils import obtener_total_paginas, navegar_siguiente_pagina, load_config
from src.shared.logging.logger import get_logger


class SubscribersScraper:
    def __init__(self, page: Optional[Page] = None):
        self.logger = get_logger()
        self.config = load_config()
        self._page = page
        self._subscribers_page = SubscribersPage(page) if page else None
        self._filter_selector = FilterSelectorComponent(page) if page else None

    def seleccionar_filtro(self, page: Page, label: str) -> bool:
        try:
            select_filtro = page.locator("#query-filter")
            select_filtro.wait_for(timeout=10000)
            select_filtro.select_option(label=label)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            return True
        except Exception as e:
            self.logger.error(f"Error selecting filter '{label}': {e}")
            return False

    def extraer_suscriptores_tabla(self, page: Page, cantidad_campos: int = 4) -> List[SubscriberTableData]:
        if self._subscribers_page:
            self._subscribers_page._page = page
        suscriptores = []
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)

        try:
            tabla_suscriptores = page.locator("ul").filter(has=page.locator("li", has_text="Correo electrónico"))
            suscriptores_elementos = tabla_suscriptores.locator("> li")
            cantidad_suscriptores = suscriptores_elementos.count()

            if cantidad_suscriptores == 0:
                self.logger.warning("No subscriber elements found")
                return suscriptores

            for i in range(1, cantidad_suscriptores):
                try:
                    datos_suscriptor = suscriptores_elementos.nth(i).locator("> div")
                    count = datos_suscriptor.count()
                    correo = datos_suscriptor.nth(0).inner_text().strip() if count > 0 else ""
                    lista = datos_suscriptor.nth(1).inner_text().strip() if count > 1 else ""
                    estado = datos_suscriptor.nth(2).inner_text().strip() if count > 2 else ""
                    calidad = datos_suscriptor.nth(3).inner_text().strip() if count > 3 else ""

                    if correo:
                        suscriptores.append(
                            SubscriberTableData(correo=correo, lista=lista, estado=estado, calidad=calidad)
                        )
                except Exception as e:
                    self.logger.error(f"Error processing element {i}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Critical error extracting subscriber table: {e}")

        self.logger.info(f"{len(suscriptores)} subscribers extracted from table")
        return suscriptores

    def navegar_a_detalle_suscriptores(self, page: Page, campaign_id: int) -> bool:
        try:
            url_base = self.config.get("url_base", "")
            url = f"{url_base}/report/campaign/{campaign_id}/"
            page.goto(url, timeout=30000)

            detalles_link = page.get_by_role("link", name="Detalles suscriptores")
            detalles_link.wait_for(timeout=15000)
            detalles_link.click()
            page.wait_for_load_state("domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)
            return True
        except Exception as e:
            self.logger.error(f"Error navigating to subscriber detail: {e}")
            return False

    def extraer_datos_filtro(self, page: Page, campania: CampaignBasicInfo, filter_type: str) -> SubscriberFilterResult:
        flow = SubscribersFlow(page)
        return flow.extract_filter(campania, 0, filter_type)

    def extraer_hard_bounces(
        self, page: Page, campania: CampaignBasicInfo, campaign_id: int
    ) -> List[SubscriberScrapingData]:
        flow = SubscribersFlow(page)
        self.navegar_a_detalle_suscriptores(page, campaign_id)
        return flow.extract_filter(campania, campaign_id, "Hard bounces").subscribers

    def extraer_no_abiertos(
        self, page: Page, campania: CampaignBasicInfo, campaign_id: int
    ) -> List[SubscriberScrapingData]:
        flow = SubscribersFlow(page)
        self.navegar_a_detalle_suscriptores(page, campaign_id)
        return flow.extract_filter(campania, campaign_id, "No abiertos").subscribers

    def extraer_suscriptores_optimizado(
        self, page: Page, campania: CampaignBasicInfo, campaign_id: int
    ) -> Tuple[List[SubscriberScrapingData], List[SubscriberScrapingData]]:
        # Delegates to flow; adapts CampaignSubscriberReport return to original (hb, no_abiertos) tuple
        config = SubscriberExtractionConfig(
            use_optimized_extraction=True, extract_hard_bounces=True, extract_no_abiertos=True
        )
        flow = SubscribersFlow(page)
        report = flow.extract_hard_bounces_and_no_abiertos(campania, campaign_id, config)
        return report.hard_bounces, report.no_abiertos

    def extraer_suscriptores_completos(
        self,
        page: Page,
        campania: CampaignBasicInfo,
        campaign_id: int,
        config: Optional[SubscriberExtractionConfig] = None,
    ) -> CampaignSubscriberReport:
        if config is None:
            config = SubscriberExtractionConfig()

        # Delegate to POM-based flow — the filter is applied inside extract_filter
        flow = SubscribersFlow(page)
        return flow.extract_hard_bounces_and_no_abiertos(campania, campaign_id, config)
