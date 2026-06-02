"""
Scraper para endpoints de campañas que NO existen en la API de Acumbamail

Este archivo mantiene la fachada CampaignsScraper para compatibilidad.
La lógica real está en flows/ y pages/.
"""
from typing import List, Optional, Dict
from playwright.sync_api import Page
import time
from datetime import datetime

from ..base import BaseScraper, ScrapingConfig
from ..models.campanias import (
    ScrapedNoAbridor,
    ScrapedReboteDuro,
    ScrapedEstadisticasCampania,
    ScrapedEstadisticasGeograficas,
    ScrapedEstadisticasDispositivo,
    ScrapedCampaignData,
    ScrapedCampaignUrl
)
from ..utils.selectors import CampaignSelectors, CommonSelectors
from ..utils.navigation import NavigationHelper
from src.shared.logging.logger import get_logger

logger = get_logger()


class ScraperCampanias(BaseScraper):
    """
    Fachada para endpoints de campañas que no existen en API.
    
    La lógica real está en:
    - CampaignUrlsFlow (para URLs de campaña)
    - Pages/Components (para navegación y extracción)
    """
    
    def __init__(self, page: Page, config: Optional[ScrapingConfig] = None):
        super().__init__(page, config)
        self.selectors = CampaignSelectors()
        self.common = CommonSelectors()
        self.navigation = NavigationHelper(page)
        self._base_url = "https://acumbamail.com"
    
    def navigate_to_campaign(self, campaign_id: int, report_type: str = "summary") -> None:
        """Navega a la página de reporte de campaña."""
        url = f"{self._base_url}/report/campaign/{campaign_id}/{report_type}/"
        self.page.goto(url, wait_until="networkidle", timeout=60000)
        self.page.wait_for_load_state("networkidle", timeout=30000)
        self.page.wait_for_timeout(1000)
    
    # === MÉTODO PRINCIPAL: NO-OPENERS ===
    def get_non_openers(self, campaign_id: int) -> List[ScrapedNoAbridor]:
        """
        ⭐ MÉTODO PRIORITARIO: Obtener suscriptores que NO abrieron la campaña
        
        Returns:
            Lista de suscriptores que no abrieron el email
        """
        logger.info(f"🔍 Iniciando scraping de no-openers para campaña {campaign_id}")
        start_time = time.time()
        
        def _scrape_non_openers():
            self.navigate_to_campaign(campaign_id)
            all_non_openers = []
            logger.warning("⚠️  get_non_openers() NO IMPLEMENTADO - retornando lista vacía")
            return all_non_openers
        
        return self.wait_and_retry(_scrape_non_openers)
    
    # === MÉTODO SECUNDARIO: HARD BOUNCES ===
    def get_hard_bounces(self, campaign_id: int) -> List[ScrapedReboteDuro]:
        """Obtener hard bounces detallados de la campaña."""
        logger.info(f"🔍 Iniciando scraping de hard bounces para campaña {campaign_id}")
        
        def _scrape_hard_bounces():
            self.navigate_to_campaign(campaign_id)
            all_hard_bounces = []
            logger.warning("⚠️  get_hard_bounces() NO IMPLEMENTADO - retornando lista vacía")
            return all_hard_bounces
        
        return self.wait_and_retry(_scrape_hard_bounces)
    
    # === MÉTODO AVANZADO: ESTADÍSTICAS EXTENDIDAS ===
    def get_extended_stats(self, campaign_id: int) -> ScrapedEstadisticasCampania:
        """Obtener estadísticas avanzadas no disponibles en API."""
        logger.info(f"📊 Iniciando scraping de estadísticas extendidas para campaña {campaign_id}")
        start_time = time.time()
        
        def _scrape_extended_stats():
            self.navigate_to_campaign(campaign_id)
            stats = ScrapedEstadisticasCampania(campaign_id=campaign_id)
            stats.scraped_at = datetime.now().isoformat()
            stats.scraping_duration = time.time() - start_time
            logger.warning("⚠️  get_extended_stats() NO IMPLEMENTADO - retornando stats vacías")
            return stats
        
        return self.wait_and_retry(_scrape_extended_stats)
    
    # === MÉTODO: URLS DE CAMPAÑA ===
    def get_campaign_urls(self, campaign_id: int) -> List[ScrapedCampaignUrl]:
        """
        🔗 Obtener URLs de la campaña con estadísticas de clics.
        
        Delegado a CampaignUrlsFlow.
        """
        from ..flows.campaign_urls_flow import FlujoUrlsCampania
        flow = FlujoUrlsCampania(self.page)
        return flow.scrape(campaign_id)

    # === MÉTODO COMBINADO ===
    def get_complete_campaign_data(self, campaign_id: int,
                                 include_non_openers: bool = True,
                                 include_hard_bounces: bool = True,
                                 include_extended_stats: bool = False,
                                 include_campaign_urls: bool = True) -> ScrapedCampaignData:
        """Obtener todos los datos scrapeados de una campaña."""
        logger.info(f"🎯 Iniciando scraping completo de campaña {campaign_id}")
        start_time = time.time()
        
        campaign_data = ScrapedCampaignData(
            campaign_id=campaign_id,
            scraped_at=datetime.now().isoformat()
        )
        
        if include_non_openers:
            try:
                campaign_data.non_openers = self.get_non_openers(campaign_id)
                campaign_data.scraping_methods.append("get_non_openers")
            except Exception as e:
                logger.error(f"❌ Error obteniendo no-openers: {e}")
        
        if include_hard_bounces:
            try:
                campaign_data.hard_bounces = self.get_hard_bounces(campaign_id)
                campaign_data.scraping_methods.append("get_hard_bounces")
            except Exception as e:
                logger.error(f"❌ Error obteniendo hard bounces: {e}")

        if include_campaign_urls:
            try:
                campaign_data.campaign_urls = self.get_campaign_urls(campaign_id)
                campaign_data.scraping_methods.append("get_campaign_urls")
            except Exception as e:
                logger.error(f"❌ Error obteniendo URLs de campaña: {e}")

        if include_extended_stats:
            try:
                campaign_data.extended_stats = self.get_extended_stats(campaign_id)
                campaign_data.scraping_methods.append("get_extended_stats")
            except Exception as e:
                logger.error(f"❌ Error obteniendo estadísticas extendidas: {e}")

        duration = time.time() - start_time
        logger.info(f"🎉 Scraping completo finalizado en {duration:.1f}s")
        logger.info(f"📊 Resumen: {campaign_data.summary}")

        return campaign_data
    
    # === MÉTODOS AUXILIARES ===
    def _get_text_content(self, selector: str, default: str = "0") -> str:
        try:
            return self.page.locator(selector).inner_text()
        except Exception:
            return default
    
    def _extract_date_sent(self, element) -> Optional[str]:
        return None
    
    def _extract_subscriber_name(self, element) -> Optional[str]:
        return None
    
    def _extract_list_name(self, element) -> Optional[str]:
        return None
    
    def _scrape_geographic_stats(self) -> List[ScrapedEstadisticasGeograficas]:
        logger.warning("⚠️  _scrape_geographic_stats() NO IMPLEMENTADO")
        return []
    
    def _scrape_device_stats(self) -> List[ScrapedEstadisticasDispositivo]:
        logger.warning("⚠️  _scrape_device_stats() NO IMPLEMENTADO")
        return []
    
    def _scrape_hourly_stats(self) -> Dict[str, int]:
        logger.warning("⚠️  _scrape_hourly_stats() NO IMPLEMENTADO")
        return {}
    
    def _scrape_daily_stats(self) -> Dict[str, int]:
        logger.warning("⚠️  _scrape_daily_stats() NO IMPLEMENTADO")
        return {}
CampaignsScraper = ScraperCampanias
