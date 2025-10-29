"""
Servicio híbrido que combina API y scraping para obtener datos completos
"""
from playwright.sync_api import Page
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from pathlib import Path
import sys

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from .infrastructure.api import API
from .infrastructure.api.models.campanias import CampaignBasicInfo
from .scrapping import (
    SubscriberDetailsService,
    ScrapingResult,
    ScrapingSession
)
from .shared.logging.logger import get_logger
from .shared.utils.retry_utils import retry_with_backoff, is_connection_error


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

            # 1. Obtener datos básicos de API (rápido y confiable) con reintentos
            def get_basic_info_with_retry():
                basic_info = self.api.campaigns.get_basic_info(campaign_id)
                if not basic_info:
                    raise Exception(f"No se pudieron obtener datos básicos de la campaña {campaign_id}. Verifique la configuración de API en config.yaml")
                return basic_info

            campaign_basic = retry_with_backoff(
                func=get_basic_info_with_retry,
                max_retries=2,
                initial_delay=1.5,
                backoff_factor=1.5,
                logger=self.logger
            )

            # 2. Obtener datos detallados con reintentos individuales (más resiliente)
            campaign_detailed = retry_with_backoff(
                lambda: self.api.campaigns.get_total_info(campaign_id),
                max_retries=2,
                initial_delay=1.5,
                logger=self.logger
            )

            campaign_clicks = retry_with_backoff(
                lambda: self.api.campaigns.get_clicks(campaign_id),
                max_retries=2,
                initial_delay=1.5,
                logger=self.logger
            )

            campaign_openers = retry_with_backoff(
                lambda: self.api.campaigns.get_openers(campaign_id),
                max_retries=2,
                initial_delay=1.5,
                logger=self.logger
            )

            campaign_soft_bounces = retry_with_backoff(
                lambda: self.api.campaigns.get_soft_bounces(campaign_id),
                max_retries=2,
                initial_delay=1.5,
                logger=self.logger
            )

            all_lists = retry_with_backoff(
                lambda: self.api.suscriptores.get_lists(),
                max_retries=2,
                initial_delay=1.5,
                logger=self.logger
            )

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
        Extrae datos por scraping que no están disponibles en la API.
        Incluye reintentos automáticos con re-autenticación si la sesión expira.
        """
        max_retries = 2
        retry_count = 0

        while retry_count < max_retries:
            try:
                if not self.scraping_service:
                    return None

                self.logger.start_timer("extract_scraping_data")

                # Espera adicional antes de scraping para asegurar estabilidad
                import time
                time.sleep(1.5)

                # Extraer hard bounces (no disponible en API)
                hard_bounces = self.scraping_service.extract_hard_bounces(campaign, campaign_id)

                # Verificar si fue exitoso o si devolvió lista vacía por sesión expirada
                # Si navigate_to_subscriber_details retornó False, hard_bounces será []
                # En ese caso, intentar validar y refrescar sesión

                # Extraer no abiertos (no disponible en API)
                no_opens = self.scraping_service.extract_no_opens(campaign, campaign_id)

                # Si ambos están vacíos y es el primer intento, puede ser sesión expirada
                if retry_count == 0 and len(hard_bounces) == 0 and len(no_opens) == 0:
                    # Verificar si el scraping_service tiene acceso a page
                    if hasattr(self.scraping_service, 'page'):
                        try:
                            from .shared.utils.legacy_utils import is_on_login_page
                            if is_on_login_page(self.scraping_service.page):
                                self.logger.warning(f"⚠️ Sesión expirada detectada durante scraping de campaña {campaign_id}")
                                retry_count += 1
                                if retry_count < max_retries:
                                    self.logger.info(f"🔄 Intento {retry_count}/{max_retries} - Re-autenticando...")
                                    # Aquí se necesitaría re-autenticar
                                    # Por ahora, continuar para no romper el flujo
                                    continue
                        except ImportError:
                            pass

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
                error_msg = str(e).lower()

                # Verificar si es error de sesión expirada
                if "sesión expirada" in error_msg or "session expired" in error_msg or "login" in error_msg:
                    retry_count += 1
                    if retry_count < max_retries:
                        self.logger.warning(f"⚠️ Sesión expirada en intento {retry_count}/{max_retries}")
                        self.logger.info("🔄 Nota: La re-autenticación debe hacerse a nivel de flujo principal")
                        # Continuar al siguiente intento
                        continue
                    else:
                        self.logger.error(f"❌ Máximo de reintentos alcanzado para campaña {campaign_id}")
                        return None

                # Si es un error crítico (campaña no existe), propagar el error
                if any(keyword in error_msg for keyword in ["timeout", "no existe", "not found", "página no existe"]):
                    self.logger.error(f"Error crítico en campaña {campaign_id}: {e}")
                    raise Exception(f"Campaña {campaign_id} no disponible: {e}")
                else:
                    # Otros errores menos críticos, continuar sin scraping
                    self.logger.error(f"Error en extracción por scraping: {e}")
                    return None

        # Si llegamos aquí, se agotaron los reintentos
        self.logger.error(f"❌ No se pudo extraer datos de scraping para campaña {campaign_id} después de {max_retries} intentos")
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
                    if complete_data and complete_data.get("scraping_result"):
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

    def validate_scraping_data(self, campaign_id: int) -> Dict[str, Any]:
        """
        Valida los datos de scraping comparando con lo que muestra la interfaz web
        Retorna un reporte detallado de validación
        """
        from .shared.utils.legacy_utils import cargar_campanias_a_buscar
        from .infrastructure.api.models.campanias import CampaignBasicInfo
        from .scrapping.endpoints.subscriber_details import SubscriberDetailsService
        from .shared.logging.logger import get_logger

        logger = get_logger()
        validation_report = {
            "campaign_id": campaign_id,
            "timestamp": datetime.now(),
            "validation_results": {
                "no_abiertos": {
                    "web_count": 0,
                    "extracted_count": 0,
                    "match": False,
                    "sample_web_data": [],
                    "sample_extracted_data": []
                },
                "hard_bounces": {
                    "web_count": 0,
                    "extracted_count": 0,
                    "match": False,
                    "sample_web_data": [],
                    "sample_extracted_data": []
                }
            },
            "errors": [],
            "success": False
        }

        try:
            logger.info(f"🔍 Iniciando validación de scraping para campaña {campaign_id}")

            # Obtener conteos desde la interfaz web
            if self.scraping_service:
                logger.info("📊 Obteniendo conteos desde la interfaz web...")

                # Navegar a página principal de suscriptores para obtener conteos
                if self.scraping_service.navigate_to_subscriber_details(campaign_id, filter_index=0):
                    logger.info("✅ Navegación a página de suscriptores exitosa")

                    # Extraer conteos de los elementos visibles
                    web_counts = self._extract_web_counts()
                    validation_report["validation_results"]["no_abiertos"]["web_count"] = web_counts.get("no_abiertos", 0)
                    validation_report["validation_results"]["hard_bounces"]["web_count"] = web_counts.get("hard_bounces", 0)

                    logger.info(f"📈 Conteos desde web: No abiertos={web_counts.get('no_abiertos', 0)}, Hard bounces={web_counts.get('hard_bounces', 0)}")
                else:
                    logger.warning("⚠️ No se pudo navegar a la página de suscriptores")
                    validation_report["errors"].append("No se pudo navegar a la página de suscriptores")

                # Crear campaña básica para extraer datos
                campaign_basic = CampaignBasicInfo(
                    id=campaign_id,
                    name=f"Campaign {campaign_id}",
                    subject="",
                    status="sent",  # Campo requerido
                    date="2025-01-01 00:00:00",  # Campo requerido
                    date_sent="2025-01-01",  # Campo requerido
                    lists=[]
                )

                # Extraer datos usando scraping
                logger.info("🔄 Extrayendo datos de No abiertos...")
                no_opens = self.scraping_service.extract_no_opens(campaign_basic, campaign_id)
                validation_report["validation_results"]["no_abiertos"]["extracted_count"] = len(no_opens)

                if no_opens:
                    validation_report["validation_results"]["no_abiertos"]["sample_extracted_data"] = [
                        {"email": no_open.email, "lista": no_open.lista, "estado": str(no_open.estado)}
                        for no_open in no_opens[:5]
                    ]
                    logger.info(f"✅ Se extrajeron {len(no_opens)} No abiertos")
                else:
                    logger.warning("⚠️ No se extrajeron datos de No abiertos")

                logger.info("🔄 Extrayendo datos de Hard bounces...")
                hard_bounces = self.scraping_service.extract_hard_bounces(campaign_basic, campaign_id)
                validation_report["validation_results"]["hard_bounces"]["extracted_count"] = len(hard_bounces)

                if hard_bounces:
                    validation_report["validation_results"]["hard_bounces"]["sample_extracted_data"] = [
                        {"email": hb.email, "lista": hb.lista, "estado": str(hb.estado)}
                        for hb in hard_bounces[:5]
                    ]
                    logger.info(f"✅ Se extrajeron {len(hard_bounces)} Hard bounces")
                else:
                    logger.warning("⚠️ No se extrajeron datos de Hard bounces")

                # Validar coincidencias
                no_abiertos_match = (
                    validation_report["validation_results"]["no_abiertos"]["web_count"] ==
                    validation_report["validation_results"]["no_abiertos"]["extracted_count"]
                )
                validation_report["validation_results"]["no_abiertos"]["match"] = no_abiertos_match

                hard_bounces_match = (
                    validation_report["validation_results"]["hard_bounces"]["web_count"] ==
                    validation_report["validation_results"]["hard_bounces"]["extracted_count"]
                )
                validation_report["validation_results"]["hard_bounces"]["match"] = hard_bounces_match

                validation_report["success"] = no_abiertos_match and hard_bounces_match

                logger.info(f"📊 Resultados de validación:")
                logger.info(f"   • No abiertos: Web={validation_report['validation_results']['no_abiertos']['web_count']}, Extraídos={validation_report['validation_results']['no_abiertos']['extracted_count']}, Match={no_abiertos_match}")
                logger.info(f"   • Hard bounces: Web={validation_report['validation_results']['hard_bounces']['web_count']}, Extraídos={validation_report['validation_results']['hard_bounces']['extracted_count']}, Match={hard_bounces_match}")

            else:
                validation_report["errors"].append("Servicio de scraping no disponible")
                logger.error("❌ Servicio de scraping no disponible para validación")

        except Exception as e:
            error_msg = f"Error en validación: {e}"
            logger.error(f"❌ {error_msg}")
            validation_report["errors"].append(error_msg)

        return validation_report

    def _extract_web_counts(self) -> Dict[str, int]:
        """
        Extrae los conteos mostrados en la interfaz web
        """
        counts = {
            "no_abiertos": 0,
            "hard_bounces": 0
        }

        try:
            # Buscar los elementos que muestran los conteos
            # Basado en la estructura observada con BrowserMCP
            filter_elements = self.scraping_service.page.locator('ul').filter(
                has=self.scraping_service.page.locator("li", has_text="No abiertos")
            ).locator('> li')

            # Buscar cada tipo de suscriptor y su conteo
            for i in range(filter_elements.count()):
                try:
                    element = filter_elements.nth(i)
                    text = element.inner_text()

                    if "No abiertos" in text:
                        # Buscar el número que acompaña a "No abiertos"
                        import re
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            counts["no_abiertos"] = int(numbers[-1])  # Tomar el último número encontrado

                    elif "Hard bounces" in text:
                        import re
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            counts["hard_bounces"] = int(numbers[-1])
                except Exception:
                    continue

        except Exception as e:
            self.logger.warning(f"Error extrayendo conteos web: {e}")

        return counts