"""
Endpoint para scraping de detalles de suscriptores
Contiene la lógica extraída de demo.py con mejores prácticas aplicadas
"""
from playwright.sync_api import Page, TimeoutError as PWTimeoutError
from typing import List, Optional
import time
import re

from src.shared.utils.legacy_utils import obtener_total_paginas, navegar_siguiente_pagina, load_config
from src.shared.logging.logger import get_logger
from src.structured_logger import (
    log_success, log_error, log_warning, log_info, log_browser_action, log_data_extraction, log_operation, timer_decorator
)
from src.infrastructure.api.models.campanias import CampaignBasicInfo
from ..models import (
    HardBounceSubscriber,
    NoOpenSubscriber,
    FilterInfo,
    SubscriberStatus,
    SubscriberQuality
)


class SubscriberDetailsService:
    """Servicio para extraer detalles de suscriptores por scraping"""

    def __init__(self, page: Page):
        self.page = page
        self.logger = get_logger()
        self.config = load_config()

        # Configuración de timeouts muy largos para conexiones lentas
        self.timeouts = {
            'navigation': 300000,  # 5 minutos para navegación (aumentado de 3min)
            'element_wait': 120000,  # 2 minutos para elementos (aumentado de 1min)
            'network_idle': 90000,  # 1.5 minutos para network idle (aumentado de 45s)
            'table_extraction': 240000,  # 4 minutos para extracción de tabla (aumentado de 2min)
            'page_load': 180000   # 3 minutos para carga de página (aumentado de 1.5min)
        }
        
        log_info("SubscriberDetailsService inicializado", 
                timeouts=self.timeouts, 
                service_version="1.0.0")

    def navigate_to_subscriber_details(self, campaign_id: int, filter_index: int = 0) -> bool:
        """
        Navega a la sección de detalles de suscriptores de la campaña con filtro específico.
        Aplica mejores prácticas de Playwright y optimiza elementos por página automáticamente.

        Args:
            campaign_id: ID de la campaña
            filter_index: Índice del filtro (0=Abiertos, 1=Hard bounces, 5=No abiertos, etc.)
        """
        with log_operation("navegacion_detalles_suscriptores", campaign_id=campaign_id):
            try:
                url_base = self.config.get("url_base", "")
                # Navegar directamente con el filtro aplicado (la página ignora items_per_page en URL)
                url = f"{url_base}/report/campaign/{campaign_id}/subscribers/?filter_index={filter_index}"

                log_browser_action("navegacion_con_filtro", url, campaign_id=campaign_id, filter_index=filter_index)
                # Usar navegación con timeout configurado
                self.page.goto(url, timeout=self.timeouts['navigation'])

                # Esperar a que la página esté cargada (domcontentloaded es más rápido que networkidle)
                self.page.wait_for_load_state("domcontentloaded", timeout=self.timeouts['page_load'])

                log_success("Navegación completada con filtro aplicado", campaign_id=campaign_id, filter_index=filter_index, url=url)
                return True

            except PWTimeoutError as e:
                log_error("Timeout navegando a detalles de suscriptores",
                         campaign_id=campaign_id, timeout_ms=self.timeouts['navigation'], error=str(e))
                # Los timeouts generalmente indican que la página no existe
                raise Exception(f"Campaña {campaign_id} no existe o no está disponible: timeout navegando")
            except Exception as e:
                log_error("Error navegando a detalles de suscriptores",
                         campaign_id=campaign_id, error_type=type(e).__name__, error=str(e))
                # Otros errores de navegación también indican problemas críticos
                raise Exception(f"Campaña {campaign_id} no disponible: {e}")

    def _get_total_from_page(self) -> Optional[int]:
        """
        Extrae el total de elementos del texto 'de X elementos' en la paginación.
        """
        try:
            elementos_text = self.page.locator("text=/de \\d+ elementos/i")
            if elementos_text.count() > 0:
                text_content = elementos_text.first.inner_text(timeout=3000)
                match = re.search(r'de\s+(\d+)\s+elementos', text_content, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            return None
        except:
            return None

    def _get_filter_total_results(self) -> Optional[int]:
        """Intenta obtener el total de resultados del filtro actual"""
        try:
            # Buscar elementos que pueden contener el total
            # Adaptar según la estructura real de la página
            total_elements = self.page.locator(".total-results, .pagination-info").all()
            for element in total_elements:
                text = element.text_content()
                if text and any(char.isdigit() for char in text):
                    # Extraer número del texto
                    numbers = ''.join(filter(str.isdigit, text))
                    if numbers:
                        return int(numbers)
            return None
        except:
            return None

    @timer_decorator("extract_subscribers_table")
    def extract_subscribers_from_table(self, expected_columns: int = 4) -> List[List[str]]:
        """
        Extrae datos de suscriptores de la tabla actual de forma optimizada.
        """
        try:
            log_info("Iniciando extracción de datos de tabla", expected_columns=expected_columns)

            # Esperar a que la página esté lista (domcontentloaded es más rápido que networkidle)
            self.page.wait_for_load_state("domcontentloaded", timeout=30000)

            # Localizador más específico usando la estructura conocida de la tabla
            # Buscar la lista de suscriptores (ul que contiene los li con datos)
            tabla_locator = self.page.locator('ul').filter(
                has=self.page.locator("li", has_text="Correo electrónico")
            )

            if tabla_locator.count() == 0:
                log_warning("No se encontró tabla de suscriptores")
                return []

            filas = tabla_locator.locator('> li')
            filas_total = filas.count()

            log_info("Tabla localizada", filas_totales=filas_total, expected_columns=expected_columns)

            suscriptores = []

            # Empezar desde 1 para saltar el header (primera fila)
            for fila_i in range(1, filas_total):
                try:
                    # Obtener todos los divs de la fila
                    campos = filas.nth(fila_i).locator("> div, > a")
                    campos_disponibles = campos.count()

                    # Extraer textos de los primeros expected_columns elementos
                    campos_arr = []
                    for i in range(0, min(campos_disponibles, expected_columns)):
                        try:
                            campo_text = campos.nth(i).inner_text().strip()
                            campos_arr.append(campo_text)
                        except Exception:
                            campos_arr.append("")

                    # Completar con vacíos si faltan
                    while len(campos_arr) < expected_columns:
                        campos_arr.append("")

                    # Agregar solo si tiene al menos un campo no vacío
                    if any(campo.strip() for campo in campos_arr):
                        suscriptores.append(campos_arr)

                except Exception as e:
                    log_warning(f"Error extrayendo fila {fila_i}",
                              fila_index=fila_i, error_type=type(e).__name__, error=str(e))
                    continue

            log_data_extraction("suscriptores", len(suscriptores), "scraping_table",
                              filas_procesadas=filas_total-1, filas_exitosas=len(suscriptores))
            return suscriptores

        except Exception as e:
            log_error("Error extrayendo suscriptores de tabla",
                     expected_columns=expected_columns, error_type=type(e).__name__, error=str(e))
            return []

    def _parse_subscriber_quality(self, quality_text: str) -> SubscriberQuality:
        """Convierte texto de calidad a enum"""
        quality_map = {
            "excelente": SubscriberQuality.EXCELLENT,
            "buena": SubscriberQuality.GOOD,
            "regular": SubscriberQuality.REGULAR,
            "pobre": SubscriberQuality.POOR,
        }
        return quality_map.get(quality_text.lower(), SubscriberQuality.UNKNOWN)

    def _parse_subscriber_status(self, status_text: str) -> SubscriberStatus:
        """Convierte texto de estado a enum"""
        status_map = {
            "activo": SubscriberStatus.ACTIVE,
            "inactivo": SubscriberStatus.INACTIVE,
            "rebotado": SubscriberStatus.BOUNCED,
            "dado de baja": SubscriberStatus.UNSUBSCRIBED,
        }
        return status_map.get(status_text.lower(), SubscriberStatus.UNKNOWN)

    def extract_hard_bounces(self, campaign: CampaignBasicInfo, campaign_id: int) -> List[HardBounceSubscriber]:
        """
        Extrae Hard bounces de la campaña usando scraping con mejores prácticas.
        """
        suscriptores: List[HardBounceSubscriber] = []

        with log_operation("extraccion_hard_bounces",
                          campaign_id=campaign_id, campaign_name=campaign.name):
            try:
                # Navegar directamente con el filtro Hard bounces (filter_index=1)
                if not self.navigate_to_subscriber_details(campaign_id, filter_index=1):
                    return suscriptores

                # Obtener total de elementos de la página
                total_elements = self._get_total_from_page()
                log_info("Filtro Hard bounces aplicado",
                        total_results=total_elements, campaign_id=campaign_id)

                # Obtener información de paginación y optimizar items por página
                total_pages = obtener_total_paginas(self.page)
                log_info("Información de paginación obtenida",
                        total_pages=total_pages, campaign_id=campaign_id)

                # Procesar todas las páginas
                for page_number in range(1, total_pages + 1):
                    try:
                        log_info(f"Procesando página {page_number}/{total_pages}", 
                               page_number=page_number, total_pages=total_pages, campaign_id=campaign_id)

                        # Extraer datos de la página actual
                        raw_data = self.extract_subscribers_from_table(4)
                        log_data_extraction("hard_bounces_raw", len(raw_data), "scraping", 
                                          page_number=page_number, campaign_id=campaign_id)

                        # Convertir datos raw a objetos tipados (sin validación estricta como el original)
                        page_successes = 0
                        for subscriber_data in raw_data:
                            try:
                                # Asegurar que tenemos al menos 4 campos, completar con vacío si falta
                                while len(subscriber_data) < 4:
                                    subscriber_data.append("")

                                email = subscriber_data[0]
                                lista = subscriber_data[1]
                                estado_text = subscriber_data[2]
                                calidad_text = subscriber_data[3]

                                # Solo procesar si tenemos al menos email
                                if email.strip():
                                    hard_bounce = HardBounceSubscriber(
                                        email=email,
                                        lista=lista,
                                        estado=self._parse_subscriber_status(estado_text),
                                        calidad=self._parse_subscriber_quality(calidad_text),
                                        proyecto=campaign.name or "",
                                        page_number=page_number,
                                        bounce_reason="Hard bounce"  # Agregar el parámetro faltante
                                    )
                                    suscriptores.append(hard_bounce)
                                    page_successes += 1
                            except Exception as e:
                                log_warning("Error procesando registro hard bounce", 
                                          subscriber_data=str(subscriber_data)[:100], 
                                          error_type=type(e).__name__, 
                                          page_number=page_number, 
                                          campaign_id=campaign_id)
                                continue

                        log_success(f"Página {page_number} procesada", 
                                  page_number=page_number, 
                                  registros_procesados=page_successes, 
                                  campaign_id=campaign_id)

                        # Navegar a siguiente página si no es la última
                        if page_number < total_pages:
                            log_browser_action("navegar_siguiente_pagina", f"página {page_number + 1}", 
                                             page_number=page_number + 1, campaign_id=campaign_id)
                            if not navegar_siguiente_pagina(self.page, page_number):
                                log_warning(f"No se pudo navegar a página {page_number + 1}", 
                                          page_number=page_number + 1, campaign_id=campaign_id)
                                break

                            # Pequeña pausa para evitar sobrecargar el servidor
                            time.sleep(0.5)

                    except Exception as e:
                        log_error(f"Error procesando página {page_number}", 
                                page_number=page_number, error_type=type(e).__name__, 
                                campaign_id=campaign_id, error=str(e))
                        continue

                log_success("Extracción de hard bounces completada", 
                          total_hard_bounces=len(suscriptores), 
                          pages_processed=total_pages, 
                          campaign_id=campaign_id)

            except Exception as e:
                log_error("Error extrayendo hard bounces", 
                         campaign_id=campaign_id, error_type=type(e).__name__, error=str(e))
                # Si es un error crítico (campaña no existe), propagar el error
                if any(keyword in str(e).lower() for keyword in ["timeout", "no existe", "not found"]):
                    raise Exception(f"Campaña {campaign_id} no disponible para extracción: {e}")
                # Otros errores menos críticos, continuar devolviendo lista vacía

        return suscriptores

    def extract_no_opens(self, campaign: CampaignBasicInfo, campaign_id: int) -> List[NoOpenSubscriber]:
        """
        Extrae suscriptores que no abrieron el email usando scraping con mejores prácticas.
        Navega directamente al filtro de No abiertos.
        """
        suscriptores: List[NoOpenSubscriber] = []

        with log_operation("extraccion_no_abiertos",
                          campaign_id=campaign_id, campaign_name=campaign.name):
            try:
                # Navegar directamente con el filtro No abiertos (filter_index=5)
                if not self.navigate_to_subscriber_details(campaign_id, filter_index=5):
                    return suscriptores

                # Obtener total de elementos de la página
                total_elements = self._get_total_from_page()
                log_info("Filtro No abiertos aplicado",
                        total_results=total_elements, campaign_id=campaign_id)

                # Obtener información de paginación y optimizar items por página
                total_pages = obtener_total_paginas(self.page)
                log_info("Información de paginación obtenida",
                        total_pages=total_pages, campaign_id=campaign_id)

                # Procesar todas las páginas
                for page_number in range(1, total_pages + 1):
                    try:
                        log_info(f"Procesando página {page_number}/{total_pages}", 
                               page_number=page_number, total_pages=total_pages, campaign_id=campaign_id)

                        # Extraer datos de la página actual
                        raw_data = self.extract_subscribers_from_table(4)
                        log_data_extraction("no_abiertos_raw", len(raw_data), "scraping", 
                                          page_number=page_number, campaign_id=campaign_id)

                        # Convertir datos raw a objetos tipados (sin validación estricta como el original)
                        page_successes = 0
                        page_discarded = 0
                        for subscriber_data in raw_data:
                            try:
                                # Asegurar que tenemos al menos 4 campos, completar con vacío si falta
                                while len(subscriber_data) < 4:
                                    subscriber_data.append("")

                                email = subscriber_data[0]
                                lista = subscriber_data[1]
                                estado_text = subscriber_data[2]
                                calidad_text = subscriber_data[3]

                                # Solo procesar si tenemos al menos email
                                if email.strip():
                                    no_open = NoOpenSubscriber(
                                        email=email,
                                        lista=lista,
                                        estado=self._parse_subscriber_status(estado_text),
                                        calidad=self._parse_subscriber_quality(calidad_text),
                                        proyecto=campaign.name or "",
                                        page_number=page_number,
                                        days_since_sent=0,  # Agregar parámetros faltantes
                                        previous_opens=0
                                    )
                                    suscriptores.append(no_open)
                                    page_successes += 1
                                else:
                                    page_discarded += 1
                                    if page_number == total_pages:  # Solo loggear en la última página para debug
                                        log_warning("Registro descartado por falta de email", 
                                                  subscriber_data=str(subscriber_data)[:100], 
                                                  page_number=page_number,
                                                  campaign_id=campaign_id)
                            except Exception as e:
                                log_warning("Error procesando registro no abierto", 
                                          subscriber_data=str(subscriber_data)[:100], 
                                          error_type=type(e).__name__, 
                                          page_number=page_number, 
                                          campaign_id=campaign_id)
                                continue

                        log_success(f"Página {page_number} procesada", 
                                  page_number=page_number, 
                                  registros_procesados=page_successes, 
                                  campaign_id=campaign_id)

                        # Navegar a siguiente página si no es la última
                        if page_number < total_pages:
                            log_browser_action("navegar_siguiente_pagina", f"página {page_number + 1}", 
                                             page_number=page_number + 1, campaign_id=campaign_id)
                            if not navegar_siguiente_pagina(self.page, page_number):
                                log_warning(f"No se pudo navegar a página {page_number + 1}", 
                                          page_number=page_number + 1, campaign_id=campaign_id)
                                break

                            # Pequeña pausa para evitar sobrecargar el servidor
                            time.sleep(0.5)

                    except Exception as e:
                        log_error(f"Error procesando página {page_number}", 
                                page_number=page_number, error_type=type(e).__name__, 
                                campaign_id=campaign_id, error=str(e))
                        continue

                log_success("Extracción de no abiertos completada", 
                          total_no_abiertos=len(suscriptores), 
                          pages_processed=total_pages, 
                          campaign_id=campaign_id)

            except Exception as e:
                log_error("Error extrayendo no abiertos", 
                         campaign_id=campaign_id, error_type=type(e).__name__, error=str(e))
                # Si es un error crítico (campaña no existe), propagar el error
                if any(keyword in str(e).lower() for keyword in ["timeout", "no existe", "not found"]):
                    raise Exception(f"Campaña {campaign_id} no disponible para extracción: {e}")
                # Otros errores menos críticos, continuar devolviendo lista vacía

        return suscriptores