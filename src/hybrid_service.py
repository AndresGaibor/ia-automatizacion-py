"""
Servicio híbrido que combina API y scraping para obtener datos completos
"""
from playwright.sync_api import Page
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from .api import API
from .api.models.campanias import CampaignBasicInfo, CampaignDetailedInfo
from .api.models.suscriptores import ListSummary
from .scrapping import (
    SubscriberDetailsService,
    HardBounceSubscriber,
    NoOpenSubscriber,
    SoftBounceSubscriber,
    ScrapingResult,
    ScrapingSession
)
from .logger import get_logger


class HybridDataService:
    """
    Servicio híbrido que combina datos de API y scraping para obtener información completa
    """

    def __init__(self, page: Optional[Page] = None):
        self.api = API()
        self.scraping_service = SubscriberDetailsService(page) if page else None
        self.logger = get_logger()

    def get_complete_campaign_data(self, campaign_id: int) -> Dict[str, Any]:
        """
        Obtiene datos completos de una campaña combinando API y scraping
        """
        try:
            self.logger.start_timer("get_complete_campaign_data")

            # 1. Obtener datos básicos de API (rápido y confiable)
            campaign_basic = self.api.campaigns.get_basic_info(campaign_id)
            campaign_detailed = self.api.campaigns.get_total_info(campaign_id)
            campaign_clicks = self.api.campaigns.get_clicks(campaign_id)
            campaign_openers = self.api.campaigns.get_openers(campaign_id)
            campaign_soft_bounces = self.api.campaigns.get_soft_bounces(campaign_id)
            all_lists = self.api.suscriptores.get_lists()

            # 2. Datos de scraping (información no disponible en API)
            scraping_data = None
            if self.scraping_service:
                scraping_data = self._extract_scraping_data(campaign_basic, campaign_id)

            # 3. Combinar datos
            complete_data = {
                # Datos de API
                "campaign_basic": campaign_basic,
                "campaign_detailed": campaign_detailed,
                "clicks": campaign_clicks,
                "openers": campaign_openers,
                "soft_bounces": campaign_soft_bounces,
                "lists": all_lists,

                # Datos de scraping
                "scraping_result": scraping_data,

                # Metadatos
                "data_sources": {
                    "api": True,
                    "scraping": scraping_data is not None
                },
                "extraction_timestamp": datetime.now()
            }

            self.logger.end_timer("get_complete_campaign_data",
                                f"Campaign {campaign_id} - API: ✓, Scraping: {'✓' if scraping_data else '✗'}")

            return complete_data

        except Exception as e:
            error_msg = f"Error obteniendo datos completos para campaña {campaign_id}: {e}"
            self.logger.error(error_msg)
            raise

    def _extract_scraping_data(self, campaign: CampaignBasicInfo, campaign_id: int) -> Optional[ScrapingResult]:
        """
        Extrae datos por scraping que no están disponibles en la API
        """
        try:
            if not self.scraping_service:
                return None

            self.logger.start_timer("extract_scraping_data")

            # Extraer hard bounces (no disponible en API)
            hard_bounces = self.scraping_service.extract_hard_bounces(campaign, campaign_id)

            # Extraer no abiertos (no disponible en API)
            no_opens = self.scraping_service.extract_no_opens(campaign, campaign_id)

            # Crear resultado de scraping
            scraping_result = ScrapingResult(
                campaign_id=campaign_id,
                campaign_name=campaign.name or "",
                hard_bounces=hard_bounces,
                no_opens=no_opens,
                total_processed=len(hard_bounces) + len(no_opens)
            )

            self.logger.end_timer("extract_scraping_data",
                                f"Hard bounces: {len(hard_bounces)}, No opens: {len(no_opens)}")

            return scraping_result

        except Exception as e:
            self.logger.error(f"Error en extracción por scraping: {e}")
            return None

    def process_multiple_campaigns(self, campaign_ids: List[int]) -> ScrapingSession:
        """
        Procesa múltiples campañas y retorna una sesión completa
        """
        session = ScrapingSession(
            session_id=f"hybrid_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )

        try:
            self.logger.start_timer("process_multiple_campaigns")

            for campaign_id in campaign_ids:
                try:
                    # Obtener datos completos para cada campaña
                    complete_data = self.get_complete_campaign_data(campaign_id)

                    # Agregar resultado a la sesión
                    if complete_data.get("scraping_result"):
                        session.add_campaign_result(complete_data["scraping_result"])

                except Exception as e:
                    error_msg = f"Error procesando campaña {campaign_id}: {e}"
                    self.logger.error(error_msg)
                    # Continuar con la siguiente campaña

            # Finalizar sesión
            session.finish_session()

            self.logger.end_timer("process_multiple_campaigns",
                                f"Processed {len(campaign_ids)} campaigns, Success rate: {session.success_rate:.1f}%")

            return session

        except Exception as e:
            self.logger.error(f"Error en procesamiento múltiple: {e}")
            session.finish_session()
            return session

    def get_api_only_data(self, campaign_id: int) -> Dict[str, Any]:
        """
        Obtiene solo datos de API (más rápido, para cuando no se necesita scraping)
        """
        try:
            self.logger.start_timer("get_api_only_data")

            campaign_basic = self.api.campaigns.get_basic_info(campaign_id)
            campaign_detailed = self.api.campaigns.get_total_info(campaign_id)
            campaign_clicks = self.api.campaigns.get_clicks(campaign_id)
            campaign_openers = self.api.campaigns.get_openers(campaign_id)
            campaign_soft_bounces = self.api.campaigns.get_soft_bounces(campaign_id)
            all_lists = self.api.suscriptores.get_lists()

            data = {
                "campaign_basic": campaign_basic,
                "campaign_detailed": campaign_detailed,
                "clicks": campaign_clicks,
                "openers": campaign_openers,
                "soft_bounces": campaign_soft_bounces,
                "lists": all_lists,
                "data_sources": {"api": True, "scraping": False},
                "extraction_timestamp": datetime.now()
            }

            self.logger.end_timer("get_api_only_data", f"Campaign {campaign_id}")
            return data

        except Exception as e:
            error_msg = f"Error obteniendo datos de API para campaña {campaign_id}: {e}"
            self.logger.error(error_msg)
            raise

    def get_availability_status(self) -> Dict[str, bool]:
        """
        Retorna el estado de disponibilidad de los servicios
        """
        status = {
            "api_available": False,
            "scraping_available": False
        }

        try:
            # Probar API
            self.api.campaigns.get_campaigns()
            status["api_available"] = True
        except:
            pass

        try:
            # Probar scraping
            if self.scraping_service:
                status["scraping_available"] = True
        except:
            pass

        return status

    def set_scraping_page(self, page: Page):
        """
        Configura la página de Playwright para scraping
        """
        self.scraping_service = SubscriberDetailsService(page)

    def generate_data_summary(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera un resumen de los datos obtenidos
        """
        summary = {
            "campaign_id": None,
            "campaign_name": "",
            "data_sources_used": [],
            "totals": {
                "emails_sent": 0,
                "opens": 0,
                "clicks": 0,
                "soft_bounces": 0,
                "hard_bounces": 0,
                "no_opens": 0
            },
            "rates": {
                "open_rate": 0.0,
                "click_rate": 0.0,
                "bounce_rate": 0.0
            }
        }

        try:
            # Información básica
            if campaign_data.get("campaign_basic"):
                basic = campaign_data["campaign_basic"]
                summary["campaign_id"] = getattr(basic, 'id', None)
                summary["campaign_name"] = getattr(basic, 'name', '')

            # Información detallada
            if campaign_data.get("campaign_detailed"):
                detailed = campaign_data["campaign_detailed"]
                summary["totals"]["emails_sent"] = getattr(detailed, 'total_delivered', 0)
                summary["totals"]["opens"] = getattr(detailed, 'opened', 0)
                summary["totals"]["soft_bounces"] = getattr(detailed, 'soft_bounces', 0)

            # Clics
            if campaign_data.get("clicks"):
                summary["totals"]["clicks"] = len(campaign_data["clicks"])

            # Datos de scraping
            if campaign_data.get("scraping_result"):
                scraping = campaign_data["scraping_result"]
                summary["totals"]["hard_bounces"] = len(getattr(scraping, 'hard_bounces', []))
                summary["totals"]["no_opens"] = len(getattr(scraping, 'no_opens', []))

            # Calcular tasas
            emails_sent = summary["totals"]["emails_sent"]
            if emails_sent > 0:
                summary["rates"]["open_rate"] = (summary["totals"]["opens"] / emails_sent) * 100
                summary["rates"]["click_rate"] = (summary["totals"]["clicks"] / emails_sent) * 100
                total_bounces = summary["totals"]["soft_bounces"] + summary["totals"]["hard_bounces"]
                summary["rates"]["bounce_rate"] = (total_bounces / emails_sent) * 100

            # Fuentes de datos utilizadas
            data_sources = campaign_data.get("data_sources", {})
            if data_sources.get("api"):
                summary["data_sources_used"].append("API")
            if data_sources.get("scraping"):
                summary["data_sources_used"].append("Scraping")

        except Exception as e:
            self.logger.error(f"Error generando resumen: {e}")

        return summary