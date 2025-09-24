"""
Endpoint para scraping de detalles de suscriptores
Contiene la lógica extraída de demo.py con mejores prácticas aplicadas
"""
from playwright.sync_api import Page, TimeoutError as PWTimeoutError
from typing import List, Optional, Dict, Any
import time
import re

from ...utils import obtener_total_paginas, navegar_siguiente_pagina, load_config
from ...logger import get_logger
from ...structured_logger import (
    log_success, log_error, log_warning, log_info, log_performance,
    log_browser_action, log_data_extraction, log_operation, timer_decorator
)
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

    def navigate_to_subscriber_details(self, campaign_id: int) -> bool:
        """
        Navega a la sección de detalles de suscriptores de la campaña.
        Aplica mejores prácticas de Playwright y optimiza con 200 elementos por página.
        """
        with log_operation("navegacion_detalles_suscriptores", campaign_id=campaign_id):
            try:
                url_base = self.config.get("url_base", "")
                # Navegar directamente a la página de suscriptores con 200 elementos por página
                url = f"{url_base}/report/campaign/{campaign_id}/subscribers/?items_per_page=200"

                log_browser_action("navegacion_optimizada", url, campaign_id=campaign_id, items_per_page=200)
                # Usar navegación con timeout configurado
                self.page.goto(url, timeout=self.timeouts['navigation'])

                # Esperar a que la página esté completamente cargada
                self.page.wait_for_load_state("networkidle", timeout=self.timeouts['network_idle'])

                log_success("Navegación completada con 200 elementos por página", campaign_id=campaign_id, url=url)
                return True

            except PWTimeoutError as e:
                log_error(f"Timeout navegando a detalles de suscriptores", 
                         campaign_id=campaign_id, timeout_ms=self.timeouts['navigation'], error=str(e))
                # Los timeouts generalmente indican que la página no existe
                raise Exception(f"Campaña {campaign_id} no existe o no está disponible: timeout navegando")
            except Exception as e:
                log_error(f"Error navegando a detalles de suscriptores", 
                         campaign_id=campaign_id, error_type=type(e).__name__, error=str(e))
                # Otros errores de navegación también indican problemas críticos
                raise Exception(f"Campaña {campaign_id} no disponible: {e}")

    def select_filter(self, filter_name: str) -> FilterInfo:
        """
        Selecciona un filtro en el selector de la página actual.
        Retorna información sobre el filtro aplicado.
        """
        with log_operation("seleccion_filtro", filter_name=filter_name):
            try:
                # Usar localizador más específico
                select_filtro = self.page.locator("#query-filter")

                # Esperar a que el selector esté disponible
                select_filtro.wait_for(state="visible", timeout=self.timeouts['element_wait'])

                log_browser_action("select_option", filter_name, selector="#query-filter")
                select_filtro.select_option(label=filter_name, timeout=self.timeouts['element_wait'])

                # Esperar a que la página se actualice
                self.page.wait_for_load_state("networkidle", timeout=self.timeouts['network_idle'])

                # Intentar obtener el total de resultados si está disponible
                total_results = self._get_filter_total_results()

                filter_info = FilterInfo(
                    filter_name=filter_name,
                    filter_value=filter_name,  # Agregar el parámetro faltante
                    total_results=total_results
                )

                log_success("Filtro aplicado exitosamente", 
                           filter_name=filter_name, total_results=total_results)
                return filter_info

            except Exception as e:
                log_error(f"Error seleccionando filtro", 
                         filter_name=filter_name, error_type=type(e).__name__, error=str(e))
                # No lanzar excepción, solo retornar FilterInfo con error
                return FilterInfo(
                    filter_name=filter_name,
                    filter_value=filter_name,  # Agregar el parámetro faltante
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

    @timer_decorator("extract_subscribers_table")
    def extract_subscribers_from_table(self, expected_columns: int = 4) -> List[List[str]]:
        """
        Extrae datos de suscriptores de la tabla actual.
        Restaurada la lógica original que funcionaba.
        """
        try:
            log_info("Iniciando extracción de datos de tabla", expected_columns=expected_columns)

            # Esperar a que la tabla esté visible
            self.page.wait_for_load_state("networkidle", timeout=self.timeouts['network_idle'])

            # Localizador idéntico al original
            contenedor_tabla = self.page.locator("div").filter(
                has_text="Abiertos No abiertos Clics"
            ).nth(1)

            filas = contenedor_tabla.locator("ul > li")
            filas_total = filas.count()

            log_info("Tabla localizada", filas_totales=filas_total, expected_columns=expected_columns)

            suscriptores = []

            # Lógica original: empezar desde 1 para saltar el header
            for fila_i in range(1, filas_total):
                try:
                    campos = filas.nth(fila_i).locator("> div")
                    campos_arr = []
                    
                    # Contar campos disponibles en esta fila
                    campos_disponibles = campos.count()
                    
                    # Extraer todos los campos disponibles, hasta expected_columns
                    for i in range(0, min(campos_disponibles, expected_columns)):
                        try:
                            campo_text = campos.nth(i).inner_text().strip()
                            campos_arr.append(campo_text)
                        except Exception:
                            # Si no hay más campos, agregar vacío
                            campos_arr.append("")

                    # Completar con campos vacíos si faltan
                    while len(campos_arr) < expected_columns:
                        campos_arr.append("")

                    # Agregar la fila si tiene al menos un campo no vacío
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
                # Navegar a detalles si no estamos ya allí
                if not self.navigate_to_subscriber_details(campaign_id):
                    return suscriptores

                # Seleccionar filtro de hard bounces
                filter_info = self.select_filter("Hard bounces")
                log_info("Filtro Hard bounces aplicado", 
                        total_results=filter_info.total_results, campaign_id=campaign_id)

                # Obtener información de paginación
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
        Asume que ya estamos en la vista de 'Detalles suscriptores' de la campaña.
        """
        suscriptores: List[NoOpenSubscriber] = []

        with log_operation("extraccion_no_abiertos", 
                          campaign_id=campaign_id, campaign_name=campaign.name):
            try:
                # Seleccionar filtro de no abiertos
                filter_info = self.select_filter("No abiertos")
                log_info("Filtro No abiertos aplicado", 
                        total_results=filter_info.total_results, campaign_id=campaign_id)

                # Obtener información de paginación
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

    def get_expected_no_opens_count(self, campaign_id: int) -> int:
        """
        Obtiene el número total esperado de suscriptores no abiertos desde la interfaz.
        """
        try:
            # Navegar a la página de detalles de suscriptores
            url = f"https://acumbamail.com/report/campaign/{campaign_id}/subscribers/?filter_index=5&items_per_page=200"
            log_browser_action("navegar_detalles_verificacion", url, campaign_id=campaign_id)

            self.page.goto(url, timeout=self.timeouts['navigation'])
            self.page.wait_for_load_state("networkidle", timeout=self.timeouts['network_idle'])

            # Esperar a que aparezca el filtro
            select_filtro = self.page.locator("select[name='filter_index']")
            select_filtro.wait_for(state="visible", timeout=self.timeouts['element_wait'])

            # Seleccionar filtro "No abiertos" (índice 5)
            select_filtro.select_option("5")
            log_info("Filtro No abiertos aplicado para verificación", campaign_id=campaign_id)

            # Esperar a que se actualice la página
            self.page.wait_for_load_state("networkidle", timeout=self.timeouts['network_idle'])

            # Extraer el total de resultados del texto "Mostrando X de Y elementos"
            pagination_text = self.page.locator("text=/Mostrando \\d+ de \\d+ elementos/").text_content(timeout=self.timeouts['element_wait'])

            if pagination_text:
                # Usar regex para extraer el total
                match = re.search(r'Mostrando \d+ de (\d+) elementos', pagination_text)
                if match:
                    expected_total = int(match.group(1))
                    log_info("Total esperado de no abiertos obtenido", expected_total=expected_total, campaign_id=campaign_id)
                    return expected_total
                else:
                    log_warning("No se pudo extraer el total esperado de la paginación", pagination_text=pagination_text, campaign_id=campaign_id)
                    return 0
            else:
                log_warning("No se encontró texto de paginación", campaign_id=campaign_id)
                return 0

        except Exception as e:
            log_error("Error obteniendo total esperado de no abiertos", campaign_id=campaign_id, error=str(e))
            return 0

    def extract_no_opens_with_retry(self, campaign: CampaignBasicInfo, campaign_id: int, max_retries: int = 5) -> List[NoOpenSubscriber]:
        """
        Extrae suscriptores no abiertos con verificación de integridad y reintentos automáticos.
        Garantiza que se extraigan todos los datos o se alcance el límite de reintentos.
        """
        log_info("Iniciando extracción con verificación de integridad",
                campaign_id=campaign_id, max_retries=max_retries)

        # Obtener el total esperado de la interfaz
        expected_total = self.get_expected_no_opens_count(campaign_id)
        if expected_total == 0:
            log_warning("No se pudo obtener el total esperado, procediendo sin verificación",
                       campaign_id=campaign_id)
            return self.extract_no_opens(campaign, campaign_id)

        log_info("Total esperado obtenido, iniciando extracción con verificación",
                expected_total=expected_total, campaign_id=campaign_id)

        last_attempt_data = []
        last_attempt_count = 0

        for attempt in range(1, max_retries + 1):
            try:
                log_info(f"Intento {attempt}/{max_retries} de extracción",
                        attempt=attempt, max_retries=max_retries, campaign_id=campaign_id)

                # Aumentar timeouts progresivamente en cada reintento
                if attempt > 1:
                    self._increase_timeouts_for_retry(attempt)
                    log_info("Timeouts aumentados para reintento",
                            attempt=attempt, timeouts=self.timeouts, campaign_id=campaign_id)

                # Extraer datos
                extracted_data = self.extract_no_opens(campaign, campaign_id)
                extracted_count = len(extracted_data)

                log_info(f"Intento {attempt} completado",
                        extracted_count=extracted_count, expected_total=expected_total,
                        attempt=attempt, campaign_id=campaign_id)

                # Verificar si tenemos todos los datos (con tolerancia del 5% para conexiones lentas)
                tolerance = max(1, int(expected_total * 0.05))  # 5% de tolerancia, mínimo 1
                missing_count = expected_total - extracted_count

                if extracted_count >= expected_total or missing_count <= tolerance:
                    status_msg = "✅ Extracción completa - todos los datos obtenidos" if extracted_count >= expected_total else f"✅ Extracción completa con tolerancia - faltantes: {missing_count}/{tolerance} permitidos"
                    log_success(status_msg,
                               extracted_count=extracted_count, expected_total=expected_total,
                               missing_count=missing_count, tolerance=tolerance,
                               attempt=attempt, campaign_id=campaign_id)
                    return extracted_data

                # Si no tenemos todos los datos, guardar para comparación
                last_attempt_data = extracted_data
                last_attempt_count = extracted_count

                log_warning(f"❌ Datos incompletos en intento {attempt}",
                           extracted_count=extracted_count, expected_total=expected_total,
                           missing_count=missing_count, tolerance=tolerance, attempt=attempt, campaign_id=campaign_id)

                # Si no es el último intento, esperar antes del siguiente
                if attempt < max_retries:
                    wait_time = min(60 * attempt, 300)  # Espera progresiva más larga: 60s, 120s, 180s, 240s, 300s máximo
                    log_info(f"Esperando {wait_time}s antes del siguiente intento",
                            wait_time=wait_time, attempt=attempt + 1, campaign_id=campaign_id)
                    time.sleep(wait_time)

            except Exception as e:
                log_error(f"Error en intento {attempt}",
                         attempt=attempt, error=str(e), campaign_id=campaign_id)

                if attempt < max_retries:
                    wait_time = min(60 * attempt, 300)  # Misma espera progresiva tras error
                    log_info(f"Esperando {wait_time}s antes del siguiente intento tras error",
                            wait_time=wait_time, attempt=attempt + 1, campaign_id=campaign_id)
                    time.sleep(wait_time)
                else:
                    # En el último intento, devolver lo que tengamos
                    log_error("Todos los intentos fallaron, devolviendo datos parciales",
                             last_attempt_count=last_attempt_count, expected_total=expected_total,
                             campaign_id=campaign_id)
                    return last_attempt_data

        # Si llegamos aquí, todos los intentos fallaron pero tenemos datos parciales
        log_error("❌ Extracción incompleta después de todos los reintentos",
                 last_attempt_count=last_attempt_count, expected_total=expected_total,
                 max_retries=max_retries, campaign_id=campaign_id)
        return last_attempt_data

    def _increase_timeouts_for_retry(self, attempt: int):
        """
        Aumenta los timeouts progresivamente para reintentos, con límites máximos altos para conexiones lentas.
        """
        multiplier = 1 + (attempt * 0.3)  # 1.3x, 1.6x, 1.9x, etc. (más gradual)

        # Límites máximos muy altos para conexiones extremadamente lentas
        max_limits = {
            'navigation': 600000,  # 10 minutos máximo
            'element_wait': 240000,  # 4 minutos máximo
            'network_idle': 180000,  # 3 minutos máximo
            'table_extraction': 480000,  # 8 minutos máximo
            'page_load': 360000   # 6 minutos máximo
        }

        self.timeouts['navigation'] = min(int(self.timeouts['navigation'] * multiplier), max_limits['navigation'])
        self.timeouts['element_wait'] = min(int(self.timeouts['element_wait'] * multiplier), max_limits['element_wait'])
        self.timeouts['network_idle'] = min(int(self.timeouts['network_idle'] * multiplier), max_limits['network_idle'])
        self.timeouts['table_extraction'] = min(int(self.timeouts['table_extraction'] * multiplier), max_limits['table_extraction'])
        self.timeouts['page_load'] = min(int(self.timeouts['page_load'] * multiplier), max_limits['page_load'])
        """Retorna metadatos sobre la extracción actual"""
        metadata = {
            "service_version": "1.0.0",
            "timeouts": self.timeouts,
            "extraction_timestamp": time.time()
        }
        
        log_info("Metadatos de extracción generados", 
                service_version=metadata["service_version"], 
                timeouts=metadata["timeouts"])
        
        return metadata