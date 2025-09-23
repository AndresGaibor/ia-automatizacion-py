"""
Endpoint para scraping de detalles de suscriptores
Contiene la lógica extraída de demo.py con mejores prácticas aplicadas
"""
from playwright.sync_api import Page, TimeoutError as PWTimeoutError
from typing import List, Optional, Dict, Any
import time

from ...utils import obtener_total_paginas, navegar_siguiente_pagina, load_config
from ...logger import get_logger
from ...api.models.campanias import CampaignBasicInfo
from ..models import (
    HardBounceSubscriber,
    NoOpenSubscriber,
    ScrapingPaginationInfo,
    FilterInfo,
    ScrapingError,
    SubscriberStatus,
    SubscriberQuality
)


class SubscriberDetailsService:
    """Servicio para extraer detalles de suscriptores por scraping"""

    def __init__(self, page: Page):
        self.page = page
        self.logger = get_logger()
        self.config = load_config()

        # Configuración de timeouts para mejores prácticas
        self.timeouts = {
            'navigation': 60000,  # 60 segundos para navegación
            'element_wait': 20000,  # 20 segundos para elementos
            'network_idle': 15000   # 15 segundos para network idle
        }

    def navigate_to_subscriber_details(self, campaign_id: int) -> bool:
        """
        Navega a la sección de detalles de suscriptores de la campaña.
        Aplica mejores prácticas de Playwright.
        """
        try:
            self.logger.start_timer("navigate_to_subscriber_details")

            url_base = self.config.get("url_base", "")
            url = f"{url_base}/report/campaign/{campaign_id}/"

            # Usar navegación con timeout configurado
            self.page.goto(url, timeout=self.timeouts['navigation'])

            # Usar localizador basado en rol y texto (mejores prácticas)
            details_link = self.page.get_by_role("link", name="Detalles suscriptores")
            details_link.click(timeout=self.timeouts['element_wait'])

            # Esperar a que la página esté completamente cargada
            self.page.wait_for_load_state("networkidle", timeout=self.timeouts['network_idle'])

            self.logger.end_timer("navigate_to_subscriber_details", f"Campaign {campaign_id}")
            return True

        except PWTimeoutError as e:
            error_msg = f"Timeout navegando a detalles de suscriptores para campaña {campaign_id}: {e}"
            self.logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Error navegando a detalles de suscriptores para campaña {campaign_id}: {e}"
            self.logger.error(error_msg)
            return False

    def select_filter(self, filter_name: str) -> FilterInfo:
        """
        Selecciona un filtro en el selector de la página actual.
        Retorna información sobre el filtro aplicado.
        """
        try:
            self.logger.start_timer("select_filter")

            # Usar localizador más específico
            select_filtro = self.page.locator("#query-filter")

            # Esperar a que el selector esté disponible
            select_filtro.wait_for(state="visible", timeout=self.timeouts['element_wait'])

            self.logger.info(f"🔄 Seleccionando filtro: {filter_name}")
            select_filtro.select_option(label=filter_name, timeout=self.timeouts['element_wait'])

            # Esperar a que la página se actualice
            self.page.wait_for_load_state("networkidle", timeout=self.timeouts['network_idle'])

            # Intentar obtener el total de resultados si está disponible
            total_results = self._get_filter_total_results()

            filter_info = FilterInfo(
                filter_name=filter_name,
                total_results=total_results
            )

            self.logger.end_timer("select_filter", f"Filter: {filter_name}, Results: {total_results}")
            return filter_info

        except Exception as e:
            error_msg = f"Error seleccionando filtro '{filter_name}': {e}"
            self.logger.error(error_msg)
            # No lanzar excepción, solo retornar FilterInfo con error
            return FilterInfo(
                filter_name=filter_name,
                total_results=0
            )

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

    def extract_subscribers_from_table(self, expected_columns: int = 4) -> List[List[str]]:
        """
        Extrae datos de suscriptores de la tabla actual.
        Restaurada la lógica original que funcionaba.
        """
        try:
            self.logger.start_timer("extract_subscribers_table")

            # Esperar a que la tabla esté visible
            self.page.wait_for_load_state("networkidle", timeout=self.timeouts['network_idle'])

            # Localizador idéntico al original
            contenedor_tabla = self.page.locator("div").filter(
                has_text="Abiertos No abiertos Clics"
            ).nth(1)

            filas = contenedor_tabla.locator("ul > li")
            filas_total = filas.count()

            self.logger.info(f"📊 Procesando tabla: {filas_total} filas totales")

            suscriptores = []

            # Lógica original: empezar desde 1 para saltar el header
            for fila_i in range(1, filas_total):
                try:
                    campos = filas.nth(fila_i).locator("> div")
                    campos_arr = []

                    # Lógica original: range(0, cantidad_campos - 1)
                    for i in range(0, expected_columns - 1):
                        try:
                            campo_text = campos.nth(i).inner_text().strip()
                            campos_arr.append(campo_text)
                        except Exception:
                            # Si no hay más campos, agregar vacío
                            campos_arr.append("")

                    # Agregar la fila sin validación mínima (como el original)
                    if campos_arr:  # Solo verificar que no esté vacía
                        suscriptores.append(campos_arr)

                except Exception as e:
                    self.logger.warning(f"Error extrayendo fila {fila_i}: {e}")
                    continue

            self.logger.end_timer("extract_subscribers_table", f"Extracted {len(suscriptores)} rows from {filas_total} total")
            return suscriptores

        except Exception as e:
            error_msg = f"Error extrayendo suscriptores de tabla: {e}"
            self.logger.error(error_msg)
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

        try:
            self.logger.start_timer("extract_hard_bounces")

            # Navegar a detalles si no estamos ya allí
            if not self.navigate_to_subscriber_details(campaign_id):
                return suscriptores

            # Seleccionar filtro de hard bounces
            filter_info = self.select_filter("Hard bounces")

            # Obtener información de paginación
            total_pages = obtener_total_paginas(self.page)
            pagination_info = ScrapingPaginationInfo(
                current_page=1,
                total_pages=total_pages,
                has_next=total_pages > 1
            )

            # Procesar todas las páginas
            for page_number in range(1, total_pages + 1):
                try:
                    pagination_info.current_page = page_number

                    # Extraer datos de la página actual
                    raw_data = self.extract_subscribers_from_table(4)
                    self.logger.info(f"📝 Hard bounces Página {page_number}: {len(raw_data)} registros extraídos")

                    # Convertir datos raw a objetos tipados (sin validación estricta como el original)
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
                                    page_number=page_number
                                )
                                suscriptores.append(hard_bounce)
                        except Exception as e:
                            self.logger.warning(f"Error procesando registro hard bounce: {subscriber_data}, error: {e}")
                            continue

                    # Navegar a siguiente página si no es la última
                    if page_number < total_pages:
                        if not navegar_siguiente_pagina(self.page, page_number):
                            self.logger.warning(f"No se pudo navegar a página {page_number + 1}")
                            break

                        # Pequeña pausa para evitar sobrecargar el servidor
                        time.sleep(0.5)

                except Exception as e:
                    self.logger.error(f"Error procesando página {page_number}: {e}")
                    continue

            self.logger.end_timer("extract_hard_bounces",
                                f"Campaign {campaign_id}: {len(suscriptores)} hard bounces extracted")

        except Exception as e:
            error_msg = f"Error extrayendo hard bounces para campaña {campaign_id}: {e}"
            self.logger.error(error_msg)

        return suscriptores

    def extract_no_opens(self, campaign: CampaignBasicInfo, campaign_id: int) -> List[NoOpenSubscriber]:
        """
        Extrae suscriptores que no abrieron el email usando scraping con mejores prácticas.
        Asume que ya estamos en la vista de 'Detalles suscriptores' de la campaña.
        """
        suscriptores: List[NoOpenSubscriber] = []

        try:
            self.logger.start_timer("extract_no_opens")

            # Seleccionar filtro de no abiertos
            filter_info = self.select_filter("No abiertos")

            # Obtener información de paginación
            total_pages = obtener_total_paginas(self.page)
            pagination_info = ScrapingPaginationInfo(
                current_page=1,
                total_pages=total_pages,
                has_next=total_pages > 1
            )

            # Procesar todas las páginas
            for page_number in range(1, total_pages + 1):
                try:
                    pagination_info.current_page = page_number

                    # Extraer datos de la página actual
                    raw_data = self.extract_subscribers_from_table(4)
                    self.logger.info(f"📝 No opens Página {page_number}: {len(raw_data)} registros extraídos")

                    # Convertir datos raw a objetos tipados (sin validación estricta como el original)
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
                                    page_number=page_number
                                )
                                suscriptores.append(no_open)
                        except Exception as e:
                            self.logger.warning(f"Error procesando registro no open: {subscriber_data}, error: {e}")
                            continue

                    # Navegar a siguiente página si no es la última
                    if page_number < total_pages:
                        if not navegar_siguiente_pagina(self.page, page_number):
                            self.logger.warning(f"No se pudo navegar a página {page_number + 1}")
                            break

                        # Pequeña pausa para evitar sobrecargar el servidor
                        time.sleep(0.5)

                except Exception as e:
                    self.logger.error(f"Error procesando página {page_number}: {e}")
                    continue

            self.logger.end_timer("extract_no_opens",
                                f"Campaign {campaign_id}: {len(suscriptores)} no opens extracted")

        except Exception as e:
            error_msg = f"Error extrayendo no abiertos para campaña {campaign_id}: {e}"
            self.logger.error(error_msg)

        return suscriptores

    def get_extraction_metadata(self) -> Dict[str, Any]:
        """Retorna metadatos sobre la extracción actual"""
        return {
            "service_version": "1.0.0",
            "timeouts": self.timeouts,
            "extraction_timestamp": time.time()
        }