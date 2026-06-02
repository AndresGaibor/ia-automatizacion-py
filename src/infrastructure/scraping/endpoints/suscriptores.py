"""
SubscribersScraper — fachada para scraping de suscriptores.

Delega a components/flows POM:
- ComponenteSelectorFiltro para selección de filtro
- PaginaSuscriptores para navegación y extracción de tabla
- FlujoSuscriptores para flujos multi-página

Mantiene API pública original para compatibilidad.
"""
from playwright.sync_api import Page
from typing import List, Tuple, Optional

from ..models.suscriptores import (
    DatosScrapingSuscriptor,
    DatosTablaSuscriptor,
    ResultadoFiltroSuscriptor,
    InformeSubscriptorCampania,
    SubscriberExtractionConfig,
)
from src.infrastructure.api.models.campanias import CampaignBasicInfo
from src.infrastructure.scraping.pages.subscribers_page import PaginaSuscriptores
from src.infrastructure.scraping.components.filter_selector import ComponenteSelectorFiltro
from src.infrastructure.scraping.flows.subscribers_flow import FlujoSuscriptores
from src.shared.utils.legacy_utils import load_config
from src.shared.logging.logger import get_logger

logger = get_logger()


class ScraperSuscriptores:
    """Fachada para scraping de suscriptores - delega a POM."""

    def __init__(self, page: Optional[Page] = None):
        self.logger = get_logger()
        self.config = load_config()
        self._page = page
        self._subscribers_page = PaginaSuscriptores(page) if page else None
        self._filter_selector = ComponenteSelectorFiltro(page) if page else None

    def seleccionar_filtro(self, page: Page, label: str) -> bool:
        """Selecciona filtro por label - delegado a ComponenteSelectorFiltro."""
        filter_comp = ComponenteSelectorFiltro(page)
        return filter_comp.select_filter(label)

    def extraer_suscriptores_tabla(self, page: Page, cantidad_campos: int = 4) -> List[DatosTablaSuscriptor]:
        """Extrae tabla de suscriptores - delegado a PaginaSuscriptores."""
        subs_page = PaginaSuscriptores(page)
        subs_page.wait_for_table()
        rows = subs_page.extract_all_rows()
        return [row.extract_table_data() for row in rows if row.is_valid_row()]

    def navegar_a_detalle_suscriptores(self, page: Page, campaign_id: int) -> bool:
        """Navega a detalle de suscriptores - delegado a PaginaSuscriptores."""
        subs_page = PaginaSuscriptores(page)
        return subs_page.navigate_to_detail(campaign_id)

    def extraer_datos_filtro(self, page: Page, campania: CampaignBasicInfo, filter_type: str) -> ResultadoFiltroSuscriptor:
        """Extrae datos de un filtro específico - delegado a FlujoSuscriptores."""
        flow = FlujoSuscriptores(page)
        return flow.extract_filter(campania, 0, filter_type)

    def extraer_hard_bounces(
        self, page: Page, campania: CampaignBasicInfo, campaign_id: int
    ) -> List[DatosScrapingSuscriptor]:
        """Extrae hard bounces - delegado a FlujoSuscriptores."""
        flow = FlujoSuscriptores(page)
        self.navegar_a_detalle_suscriptores(page, campaign_id)
        return flow.extract_filter(campania, campaign_id, "Hard bounces").subscribers

    def extraer_no_abiertos(
        self, page: Page, campania: CampaignBasicInfo, campaign_id: int
    ) -> List[DatosScrapingSuscriptor]:
        """Extrae no abiertos - delegado a FlujoSuscriptores."""
        flow = FlujoSuscriptores(page)
        self.navegar_a_detalle_suscriptores(page, campaign_id)
        return flow.extract_filter(campania, campaign_id, "No abiertos").subscribers

    def extraer_suscriptores_optimizado(
        self, page: Page, campania: CampaignBasicInfo, campaign_id: int
    ) -> Tuple[List[DatosScrapingSuscriptor], List[DatosScrapingSuscriptor]]:
        """Extrae ambos (hard bounces y no abiertos) optimizado - delegado a FlujoSuscriptores."""
        config = SubscriberExtractionConfig(
            use_optimized_extraction=True, extract_hard_bounces=True, extract_no_abiertos=True
        )
        flow = FlujoSuscriptores(page)
        report = flow.extract_hard_bounces_and_no_abiertos(campania, campaign_id, config)
        return report.hard_bounces, report.no_abiertos

    def extraer_suscriptores_completos(
        self,
        page: Page,
        campania: CampaignBasicInfo,
        campaign_id: int,
        config: Optional[SubscriberExtractionConfig] = None,
    ) -> InformeSubscriptorCampania:
        """Extrae subscribers completos - delegado a FlujoSuscriptores."""
        if config is None:
            config = SubscriberExtractionConfig()
        flow = FlujoSuscriptores(page)
        return flow.extract_hard_bounces_and_no_abiertos(campania, campaign_id, config)