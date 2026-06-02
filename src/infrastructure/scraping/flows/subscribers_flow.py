"""
SubscribersFlow — flujo de extracción paginada de suscriptores.

Orquesta extracción completa de un filtro de suscriptores:
1. Navega a la página de suscriptores
2. Aplica el filtro (Hard bounces o No abiertos)
3. Itera por todas las páginas extrayendo filas
4. Usa reintentos con recovery de sesión
"""

from playwright.sync_api import Page
from src.infrastructure.scraping.pages.subscribers_page import PaginaSuscriptores
from src.infrastructure.scraping.components.filter_selector import ComponenteSelectorFiltro
from src.infrastructure.scraping.models.suscriptores import (
    DatosScrapingSuscriptor,
    DatosTablaSuscriptor,
    ResultadoFiltroSuscriptor,
    InformeSubscriptorCampania,
    ScrapingSession,
    SubscriberExtractionConfig,
)
from src.infrastructure.api.models.campanias import CampaignBasicInfo
from src.shared.logging.logger import get_logger

logger = get_logger()


class FlujoSuscriptores:
    def __init__(self, page: Page):
        self._page = page
        self._subscribers_page = PaginaSuscriptores(page)
        self._filter_selector = ComponenteSelectorFiltro(page)

    def extract_filter(
        self, campaign: CampaignBasicInfo, campaign_id: int, filter_type: str, config: SubscriberExtractionConfig = None
    ) -> ResultadoFiltroSuscriptor:
        if config is None:
            config = SubscriberExtractionConfig()
        if not config.extract_hard_bounces and not config.extract_no_abiertos:
            return ResultadoFiltroSuscriptor(filter_type=filter_type)

        filter_label_map = {
            "Hard bounces": self._filter_selector.select_hard_bounces,
            "No abiertos": self._filter_selector.select_no_abiertos,
            "Abiertos": self._filter_selector.select_abiertos,
        }

        select_fn = filter_label_map.get(filter_type)
        if not select_fn:
            logger.error(f"Unknown filter type: {filter_type}")
            return ResultadoFiltroSuscriptor(filter_type=filter_type)

        # Apply the selected filter before starting pagination
        logger.info(f"Applying filter: {filter_type}")
        filter_applied = select_fn()
        if not filter_applied:
            logger.warning(f"Filter '{filter_type}' could not be applied, continuing anyway")

        all_subscribers = []
        total_pages = 0
        try:
            # After filter is applied, wait for the table to update
            self._subscribers_page.wait_for_table()
            total_pages = self._subscribers_page.get_total_pages()
            logger.info(f"Extracting {filter_type}: {total_pages} pages")

            for page_num in range(1, total_pages + 1):
                rows = self._subscribers_page.extract_all_rows()
                for row in rows:
                    table_data = row.extract_table_data()
                    all_subscribers.append(
                        DatosScrapingSuscriptor(
                            proyecto=campaign.name or "",
                            lista=table_data.lista,
                            correo=table_data.correo,
                            lista2=table_data.lista,
                            estado=table_data.estado,
                            calidad=table_data.calidad,
                        )
                    )

                if page_num < total_pages:
                    if not self._subscribers_page.navigate_to_next_page(page_num):
                        logger.warning(f"Failed to navigate to page {page_num + 1}")
                        break

        except Exception as e:
            logger.error(f"Error extracting {filter_type}: {e}")

        return ResultadoFiltroSuscriptor(
            filter_type=filter_type,
            subscribers=all_subscribers,
            total_pages=total_pages,
            total_subscribers=len(all_subscribers),
        )

    def extract_hard_bounces_and_no_abiertos(
        self, campaign: CampaignBasicInfo, campaign_id: int, config: SubscriberExtractionConfig = None
    ) -> InformeSubscriptorCampania:
        if config is None:
            config = SubscriberExtractionConfig()

        session = ScrapingSession(session_id=f"campaign_{campaign_id}", campaign_ids=[campaign_id])

        report = InformeSubscriptorCampania(
            campaign_id=campaign_id, campaign_name=campaign.name or "", fecha_envio=campaign.date_sent or ""
        )

        if not self._subscribers_page.navigate_to_detail(campaign_id):
            logger.error(f"Failed to navigate to subscriber detail for campaign {campaign_id}")
            session.complete_session()
            return report

        # Mirrors original logic: use_optimized determines single-pass vs two-pass,
        # but extract_* flags gate whether each filter actually runs
        if config.use_optimized_extraction:
            if config.extract_hard_bounces:
                hard_result = self.extract_filter(campaign, campaign_id, "Hard bounces", config)
                report.hard_bounces = hard_result.subscribers
                logger.info(f"Hard bounces: {len(hard_result.subscribers)} extracted")
            if config.extract_no_abiertos:
                no_open_result = self.extract_filter(campaign, campaign_id, "No abiertos", config)
                report.no_abiertos = no_open_result.subscribers
                logger.info(f"No abiertos: {len(no_open_result.subscribers)} extracted")
        else:
            if config.extract_hard_bounces:
                hard_result = self.extract_filter(campaign, campaign_id, "Hard bounces", config)
                report.hard_bounces = hard_result.subscribers
                logger.info(f"Hard bounces: {len(hard_result.subscribers)} extracted")
            if config.extract_no_abiertos:
                no_open_result = self.extract_filter(campaign, campaign_id, "No abiertos", config)
                report.no_abiertos = no_open_result.subscribers
                logger.info(f"No abiertos: {len(no_open_result.subscribers)} extracted")

        session.total_subscribers_extracted = report.total_subscribers
        session.complete_session()
        return report
