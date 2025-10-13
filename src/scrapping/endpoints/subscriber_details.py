"""
Endpoint para scraping de detalles de suscriptores
Contiene la lógica extraída de demo.py con mejores prácticas aplicadas
"""
import logging
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
                logging.info(f"🔍 Iniciando navegación a detalles de suscriptores - Campaña: {campaign_id}, Filtro: {filter_index}")

                # Paso 1: Construir URL
                logging.info("📌 Paso 1: Construyendo URL de navegación")
                try:
                    url_base = self.config.get("url_base", "")
                    url = f"{url_base}/report/campaign/{campaign_id}/subscribers/?filter_index={filter_index}"
                    logging.debug(f"✅ URL construida: {url}")
                except Exception as e:
                    logging.error(f"❌ ERROR PASO 1 - Construyendo URL: {e}")
                    raise Exception(f"Error construyendo URL para campaña {campaign_id}: {e}")

                # Paso 2: Navegar a la página
                logging.info("📌 Paso 2: Navegando a la página de detalles")
                try:
                    logging.debug(f"🌐 Iniciando navegación con timeout: {self.timeouts['navigation']}ms")
                    log_browser_action("navegacion_con_filtro", url, campaign_id=campaign_id, filter_index=filter_index)

                    # Usar navegación con timeout configurado
                    self.page.goto(url, timeout=self.timeouts['navigation'])
                    logging.debug("✅ Navegación iniciada correctamente")
                except PWTimeoutError as e:
                    logging.error(f"❌ ERROR PASO 2 - Timeout en navegación: {e}")
                    logging.error(f"⏱️ Timeout configurado: {self.timeouts['navigation']}ms")
                    logging.error(f"🌐 URL intentada: {url}")
                    raise Exception(f"Campaña {campaign_id} no existe o no está disponible: timeout navegando ({self.timeouts['navigation']}ms)")
                except Exception as e:
                    logging.error(f"❌ ERROR PASO 2 - Error en navegación: {e}")
                    logging.error(f"🌐 URL intentada: {url}")
                    raise Exception(f"Error navegando a campaña {campaign_id}: {e}")

                # Paso 3: Esperar carga completa de la página
                logging.info("📌 Paso 3: Esperando carga completa de la página")
                try:
                    logging.debug(f"⏳ Esperando estado 'domcontentloaded' con timeout: {self.timeouts['page_load']}ms")
                    self.page.wait_for_load_state("domcontentloaded", timeout=self.timeouts['page_load'])
                    logging.debug("✅ Página cargada completamente (domcontentloaded)")
                except PWTimeoutError as e:
                    logging.error(f"❌ ERROR PASO 3 - Timeout esperando carga de página: {e}")
                    logging.error(f"⏱️ Timeout configurado: {self.timeouts['page_load']}ms")
                    logging.error(f"🌐 URL actual: {self.page.url}")
                    # La navegación pudo funcionar pero la página está tardando en cargar
                    logging.warning("⚠️ Continuando a pesar del timeout de carga")
                except Exception as e:
                    logging.error(f"❌ ERROR PASO 3 - Error esperando carga de página: {e}")
                    logging.warning("⚠️ Continuando a pesar del error en espera de carga")

                logging.success(f"✅ Navegación completada exitosamente - Campaña: {campaign_id}, Filtro: {filter_index}")
                logging.debug(f"🌐 URL final: {self.page.url}")
                log_success("Navegación completada con filtro aplicado", campaign_id=campaign_id, filter_index=filter_index, url=self.page.url)
                return True

            except PWTimeoutError as e:
                logging.error(f"❌ ERROR CRÍTICO - PWTimeoutError no manejado: {e}")
                log_error("Timeout navegando a detalles de suscriptores",
                         campaign_id=campaign_id, timeout_ms=self.timeouts['navigation'], error=str(e))
                raise Exception(f"Campaña {campaign_id} no existe o no está disponible: timeout navegando")
            except Exception as e:
                logging.error(f"❌ ERROR CRÍTICO - Error no manejado: {e}")
                log_error("Error navegando a detalles de suscriptores",
                         campaign_id=campaign_id, error_type=type(e).__name__, error=str(e))
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
            logging.info(f"🔍 Iniciando extracción de datos de tabla - Columnas esperadas: {expected_columns}")
            logging.debug(f"🌐 URL actual: {self.page.url}")

            # Paso 1: Esperar a que la página esté lista
            logging.info("📌 Paso 1: Verificando que la página esté lista para extracción")
            try:
                logging.debug("⏳ Esperando estado 'domcontentloaded' con timeout: 30000ms")
                self.page.wait_for_load_state("domcontentloaded", timeout=30000)
                logging.debug("✅ Página lista para extracción")
            except PWTimeoutError as e:
                logging.warning(f"⚠️ TIMEOUT esperando página lista - Continuando: {e}")
                logging.warning("⏱️ La página podría estar cargando lentamente, intentando extracción de todas formas")
            except Exception as e:
                logging.warning(f"⚠️ Error esperando página lista - Continuando: {e}")

            # Paso 2: Localizar la tabla de suscriptores
            logging.info("📌 Paso 2: Localizando tabla de suscriptores")
            tabla_locator = None
            filas = None
            try:
                logging.debug("🔍 Buscando tabla con estructura: ul > li (con 'Correo electrónico')")

                # Localizador más específico usando la estructura conocida de la tabla
                tabla_locator = self.page.locator('ul').filter(
                    has=self.page.locator("li", has_text="Correo electrónico")
                )

                tabla_count = tabla_locator.count()
                logging.debug(f"🔍 Tablas encontradas: {tabla_count}")

                if tabla_count == 0:
                    logging.error("❌ ERROR PASO 2 - No se encontró tabla de suscriptores")
                    logging.debug("🔍 Intentando selectores alternativos...")

                    # Intentar selectores alternativos
                    try:
                        alternative_locator = self.page.locator('ul:has(li:has-text("Correo electrónico"))')
                        if alternative_locator.count() > 0:
                            tabla_locator = alternative_locator
                            logging.debug("✅ Selector alternativo funcionó")
                        else:
                            logging.error("❌ Selectores alternativos también fallaron")
                            log_warning("No se encontró tabla de suscriptores con ningún selector")
                            return []
                    except Exception as alt_e:
                        logging.error(f"❌ Error con selectores alternativos: {alt_e}")
                        log_warning("No se encontró tabla de suscriptores")
                        return []
                else:
                    logging.debug("✅ Tabla localizada exitosamente")

                # Obtener filas
                filas = tabla_locator.locator('> li')
                filas_total = filas.count()
                logging.debug(f"✅ Total de filas encontradas: {filas_total}")

                if filas_total <= 1:
                    logging.warning("⚠️ Tabla encontrada pero sin datos (solo header)")
                    return []

            except PWTimeoutError as e:
                logging.error(f"❌ ERROR PASO 2 - Timeout localizando tabla: {e}")
                log_warning("Timeout localizando tabla de suscriptores")
                return []
            except Exception as e:
                logging.error(f"❌ ERROR PASO 2 - Error localizando tabla: {e}")
                log_warning("Error localizando tabla de suscriptores")
                return []

            # Paso 3: Procesar filas de datos
            logging.info("📌 Paso 3: Procesando filas de datos")
            log_info("Tabla localizada", filas_totales=filas_total, expected_columns=expected_columns)

            suscriptores = []
            filas_procesadas = 0
            filas_exitosas = 0
            filas_descartadas = 0

            # Empezar desde 1 para saltar el header (primera fila)
            logging.debug(f"🔄 Procesando filas 1-{filas_total-1} (saltando header)")
            for fila_i in range(1, filas_total):
                try:
                    filas_procesadas += 1
                    logging.debug(f"📝 Procesando fila {fila_i}/{filas_total-1}")

                    # Obtener todos los divs de la fila
                    try:
                        campos = filas.nth(fila_i).locator("> div, > a")
                        campos_disponibles = campos.count()
                        logging.debug(f"   📋 Campos encontrados en fila: {campos_disponibles}")
                    except Exception as e:
                        logging.warning(f"   ⚠️ Error obteniendo campos de fila {fila_i}: {e}")
                        filas_descartadas += 1
                        continue

                    # Extraer textos de los primeros expected_columns elementos
                    campos_arr = []
                    for i in range(0, min(campos_disponibles, expected_columns)):
                        try:
                            campo_text = campos.nth(i).inner_text().strip()
                            campos_arr.append(campo_text)
                            logging.debug(f"   📄 Campo {i}: '{campo_text}'")
                        except Exception as e:
                            logging.warning(f"   ⚠️ Error extrayendo campo {i} de fila {fila_i}: {e}")
                            campos_arr.append("")

                    # Completar con vacíos si faltan
                    while len(campos_arr) < expected_columns:
                        campos_arr.append("")
                        logging.debug(f"   ➕ Agregando campo vacío para completar {expected_columns} columnas")

                    # Verificar si la fila tiene datos válidos
                    tiene_datos = any(campo.strip() for campo in campos_arr)
                    email_valido = campos_arr[0].strip() if campos_arr else False

                    if tiene_datos and email_valido:
                        suscriptores.append(campos_arr)
                        filas_exitosas += 1
                        logging.debug(f"   ✅ Fila {fila_i} agregada (email: '{campos_arr[0]}')")
                    else:
                        filas_descartadas += 1
                        logging.debug(f"   ❌ Fila {fila_i} descartada (tiene_datos: {tiene_datos}, email_valido: {email_valido})")

                except PWTimeoutError as e:
                    logging.warning(f"⚠️ TIMEOUT extrayendo fila {fila_i}: {e}")
                    filas_descartadas += 1
                    continue
                except Exception as e:
                    logging.warning(f"⚠️ Error extrayendo fila {fila_i}: {e}")
                    filas_descartadas += 1
                    continue

            # Paso 4: Resumen de extracción
            logging.info("📌 Paso 4: Resumen de extracción completada")
            logging.info(f"📊 Resultados de extracción:")
            logging.info(f"   • Total filas procesadas: {filas_procesadas}")
            logging.info(f"   • Filas exitosas: {filas_exitosas}")
            logging.info(f"   • Filas descartadas: {filas_descartadas}")
            logging.info(f"   • Suscriptores extraídos: {len(suscriptores)}")

            log_data_extraction("suscriptores", len(suscriptores), "scraping_table",
                              filas_procesadas=filas_procesadas, filas_exitosas=filas_exitosas, filas_descartadas=filas_descartadas)

            if suscriptores:
                logging.success(f"✅ Extracción completada exitosamente - {len(suscriptores)} suscriptores")
            else:
                logging.warning("⚠️ Extracción completada pero no se encontraron suscriptores")

            return suscriptores

        except PWTimeoutError as e:
            logging.error(f"❌ ERROR CRÍTICO - PWTimeoutError en extracción de tabla: {e}")
            log_error("Timeout extrayendo suscriptores de tabla",
                     expected_columns=expected_columns, error_type="PWTimeoutError", error=str(e))
            return []
        except Exception as e:
            logging.error(f"❌ ERROR CRÍTICO - Error en extracción de tabla: {e}")
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