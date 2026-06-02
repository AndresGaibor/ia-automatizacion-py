"""
Servicio híbrido que combina API y scraping para obtener datos completos
"""
from playwright.sync_api import Page
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import sys

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from .infrastructure.api import API
from .infrastructure.api.models.campanias import CampaignBasicInfo
from .shared.utils.legacy_utils import is_on_login_page
from .scrapping import (
    SubscriberDetailsService,
    ScrapingResult
)
from .shared.logging.logger import get_logger
from .shared.utils.retry_utils import retry_with_backoff, is_connection_error
from .autentificacion import manejar_popup_cookies


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
            self.logger.info(f"🔄 Iniciando extracción de datos completos", campaign_id=campaign_id)
            self.logger.start_timer("get_complete_campaign_data")

            # 1. Obtener datos básicos de API (rápido y confiable) con reintentos
            self.logger.debug(f"📊 PASO 1: Obteniendo datos básicos de API", campaign_id=campaign_id)
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
            self.logger.info(f"✅ Datos básicos obtenidos", campaign_name=campaign_basic.name if campaign_basic else "Unknown")

            # 2. Obtener datos detallados con reintentos individuales (más resiliente)
            self.logger.debug(f"📊 PASO 2: Obteniendo datos detallados de API", campaign_id=campaign_id)

            self.logger.debug("📈 Obteniendo información total de campaña...")
            campaign_detailed = retry_with_backoff(
                lambda: self.api.campaigns.get_total_info(campaign_id),
                max_retries=2,
                initial_delay=1.5,
                logger=self.logger
            )

            self.logger.debug("👆 Obteniendo clics de campaña...")
            campaign_clicks = retry_with_backoff(
                lambda: self.api.campaigns.get_clicks(campaign_id),
                max_retries=2,
                initial_delay=1.5,
                logger=self.logger
            )
            self.logger.debug(f"  Clics obtenidos: {len(campaign_clicks) if campaign_clicks else 0}")

            self.logger.debug("📧 Obteniendo abiertos de campaña...")
            campaign_openers = retry_with_backoff(
                lambda: self.api.campaigns.get_openers(campaign_id),
                max_retries=2,
                initial_delay=1.5,
                logger=self.logger
            )
            self.logger.debug(f"  Abiertos obtenidos: {len(campaign_openers) if campaign_openers else 0}")

            self.logger.debug("⚠️ Obteniendo soft bounces de campaña...")
            campaign_soft_bounces = retry_with_backoff(
                lambda: self.api.campaigns.get_soft_bounces(campaign_id),
                max_retries=2,
                initial_delay=1.5,
                logger=self.logger
            )
            self.logger.debug(f"  Soft bounces obtenidos: {len(campaign_soft_bounces) if campaign_soft_bounces else 0}")

            self.logger.debug("📋 Obteniendo listas de suscriptores...")
            all_lists = retry_with_backoff(
                lambda: self.api.suscriptores.get_lists(),
                max_retries=2,
                initial_delay=1.5,
                logger=self.logger
            )
            self.logger.info(f"✅ Datos de API obtenidos exitosamente",
                           clics=len(campaign_clicks) if campaign_clicks else 0,
                           abiertos=len(campaign_openers) if campaign_openers else 0,
                           soft_bounces=len(campaign_soft_bounces) if campaign_soft_bounces else 0)

            # 2. Datos de scraping (información no disponible en API)
            self.logger.debug(f"📊 PASO 3: Extrayendo datos por scraping", campaign_id=campaign_id)
            scraping_data = None
            if self.scraping_service:
                self.logger.debug("🔍 Servicio de scraping disponible, iniciando extracción...")
                scraping_data = self._extract_scraping_data(campaign_basic, campaign_id)
                if scraping_data:
                    self.logger.info(f"✅ Datos de scraping extraídos",
                                   hard_bounces=len(scraping_data.hard_bounces) if scraping_data else 0,
                                   no_opens=len(scraping_data.no_opens) if scraping_data else 0)
                else:
                    self.logger.warning("⚠️ No se pudieron extraer datos de scraping")
            else:
                self.logger.warning("⚠️ Servicio de scraping no disponible - saltando extracción")

            # 3. Combinar datos
            self.logger.debug("🔄 Combinando datos de API y scraping...")
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
            self.logger.success(f"✅ Extracción de datos completos finalizada", campaign_id=campaign_id)

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

        self.logger.info(f"🔍 Iniciando extracción de datos por scraping", campaign_id=campaign_id, max_retries=max_retries)

        while retry_count < max_retries:
            try:
                if not self.scraping_service:
                    self.logger.warning("⚠️ Servicio de scraping no disponible")
                    return None

                self.logger.debug(f"🔄 Intento {retry_count + 1}/{max_retries} de scraping", campaign_id=campaign_id)
                self.logger.start_timer("extract_scraping_data")

                # Validación de sesión antes de cada intento de scraping
                if hasattr(self.scraping_service, 'page') and self.scraping_service.page:
                    page = self.scraping_service.page

                    # Verificar si estamos en página de login
                    if is_on_login_page(page):
                        self.logger.warning(f"⚠️ Sesión expirada detectada antes del scraping (intentando {retry_count + 1})", campaign_id=campaign_id)
                        raise Exception(f"Sesión expirada detectada en página {page.url} durante scraping de campaña {campaign_id}")

                    # Manejar popup de cookies agresivamente antes del scraping
                    try:
                        self.logger.debug("🍪 Manejando popup de cookies antes del scraping...")
                        manejar_popup_cookies(page, agresivo=True)
                        self.logger.debug("✅ Popup de cookies manejado antes del scraping")
                    except Exception as cookie_error:
                        self.logger.debug(f"No se pudo manejar popup de cookies: {cookie_error}")
                        # Continuar con el scraping

                # Espera adicional antes de scraping para asegurar estabilidad
                self.logger.debug("⏳ Espera de estabilización (1.5s)...")
                import time
                time.sleep(1.5)

                # Extraer hard bounces (no disponible en API)
                self.logger.debug("💥 Extrayendo hard bounces...")
                hard_bounces = self.scraping_service.extract_hard_bounces(campaign, campaign_id)
                self.logger.debug(f"  Hard bounces extraídos: {len(hard_bounces)}")

                # Validación de sesión después de extraer hard bounces
                if hasattr(self.scraping_service, 'page') and self.scraping_service.page:
                    if is_on_login_page(self.scraping_service.page):
                        self.logger.warning(f"⚠️ Redirección a login detectada después de extraer hard bounces", campaign_id=campaign_id)
                        raise Exception(f"Sesión expirada durante extracción de hard bounces para campaña {campaign_id}")

                # Extraer no abiertos (no disponible en API)
                self.logger.debug("📭 Extrayendo no abiertos...")
                no_opens = self.scraping_service.extract_no_opens(campaign, campaign_id)
                self.logger.debug(f"  No abiertos extraídos: {len(no_opens)}")

                # Validación final de sesión
                if hasattr(self.scraping_service, 'page') and self.scraping_service.page:
                    if is_on_login_page(self.scraping_service.page):
                        self.logger.warning(f"⚠️ Redirección a login detectada después de extraer no abiertos", campaign_id=campaign_id)
                        raise Exception(f"Sesión expirada durante extracción de no abiertos para campaña {campaign_id}")

                # Si ambos están vacíos y es el primer intento, puede ser sesión expirada
                if retry_count == 0 and len(hard_bounces) == 0 and len(no_opens) == 0:
                    self.logger.warning(f"⚠️ Ambos resultados vacíos en primer intento - posible sesión expirada", campaign_id=campaign_id)
                    # Verificación adicional de sesión
                    if hasattr(self.scraping_service, 'page') and self.scraping_service.page:
                        if is_on_login_page(self.scraping_service.page):
                            self.logger.warning(f"⚠️ Sesión expirada confirmada durante scraping de campaña {campaign_id}")
                            raise Exception(f"Sesión expirada confirmada durante scraping de campaña {campaign_id}")
                        else:
                            self.logger.info("ℹ️ Sesión parece válida pero no se obtuvieron datos - puede ser campaña sin datos", campaign_id=campaign_id)

                # Crear resultado de scraping
                self.logger.debug("📦 Creando resultado de scraping...",
                                hard_bounces=len(hard_bounces),
                                no_opens=len(no_opens),
                                total=len(hard_bounces) + len(no_opens))
                scraping_result = ScrapingResult(
                    campaign_id=campaign_id,
                    campaign_name=campaign.name or "",
                    hard_bounces=hard_bounces,
                    no_opens=no_opens,
                    total_processed=len(hard_bounces) + len(no_opens)
                )

                self.logger.end_timer("extract_scraping_data",
                                    f"Hard bounces: {len(hard_bounces)}, No opens: {len(no_opens)}")
                self.logger.success(f"✅ Extracción por scraping exitosa", campaign_id=campaign_id)

                return scraping_result

            except Exception as e:
                error_msg = str(e).lower()
                self.logger.error(f"❌ Error en intento {retry_count + 1}/{max_retries}", error=str(e), campaign_id=campaign_id)

                # Verificar si es error de sesión expirada
                if "sesión expirada" in error_msg or "session expired" in error_msg or "login" in error_msg:
                    self.logger.warning(f"⚠️ Error de sesión expirada detectado en error", campaign_id=campaign_id)
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
                    self.logger.error(f"Error en extracción por scraping (no crítico): {e}", campaign_id=campaign_id)
                    return None

        # Si llegamos aquí, se agotaron los reintentos
        self.logger.error(f"❌ No se pudo extraer datos de scraping para campaña {campaign_id} después de {max_retries} intentos")
        return None

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