from playwright.sync_api import Page
from typing import List, Tuple, Optional
from datetime import datetime

from ..models.suscriptores import (
    SubscriberScrapingData,
    SubscriberTableData,
    SubscriberFilterResult,
    CampaignSubscriberReport,
    ScrapingSession,
    SubscriberExtractionConfig
)
from src.infrastructure.api.models.campanias import CampaignBasicInfo
from src.shared.utils.legacy_utils import obtener_total_paginas, navegar_siguiente_pagina, load_config
from src.shared.logging.logger import get_logger

class SubscribersScraper:
    """Scraper para extraer datos de suscriptores de campañas"""

    def __init__(self):
        self.logger = get_logger()
        self.config = load_config()

    def seleccionar_filtro(self, page: Page, label: str) -> bool:
        """
        Selecciona un filtro en el selector de la página actual.
        Devuelve True si se seleccionó correctamente, False en caso contrario.
        """
        try:
            select_filtro = page.locator("#query-filter")
            select_filtro.wait_for(timeout=10000)
            select_filtro.select_option(label=label)
            # Optimización: usar domcontentloaded en lugar de networkidle para conexiones lentas
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            # Esperar un poco más para que la tabla se actualice
            page.wait_for_timeout(2000)
            return True
        except Exception as e:
            self.logger.error(f"Error seleccionando filtro '{label}': {e}")
            return False

    def extraer_suscriptores_tabla(self, page: Page, cantidad_campos: int) -> List[SubscriberTableData]:
        """Extrae suscriptores de la tabla de la interfaz web"""
        suscriptores = []

        # Esperar que la tabla esté visible antes de procesar
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)  # Espera adicional para cargar contenido dinámico

        try:
            self.logger.info("🔍 Buscando tabla de suscriptores usando selector específico...")
            self.logger.info(f"📍 URL actual: {page.url}")

            # Usar el selector que funciona según el código original
            tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
            self.logger.info(f"🔍 Tabla suscriptores encontrada: {tabla_suscriptores.count()} elementos")

            suscriptores_elementos = tabla_suscriptores.locator('> li')
            cantidad_suscriptores = suscriptores_elementos.count()

            self.logger.info(f"📄 {cantidad_suscriptores} elementos encontrados en la tabla")

            if cantidad_suscriptores == 0:
                self.logger.warning("⚠️ No se encontraron elementos en la tabla")
                # Intentar detectar qué hay en la página
                self.logger.info("🔍 Intentando encontrar cualquier lista ul...")
                listas_ul = page.locator('ul')
                self.logger.info(f"📋 {listas_ul.count()} listas ul encontradas en total")

                for i in range(min(5, listas_ul.count())):  # Revisar las primeras 5 listas
                    try:
                        lista_text = listas_ul.nth(i).inner_text()[:100]  # Primeros 100 caracteres
                        self.logger.info(f"📋 Lista {i}: {lista_text}")
                    except:
                        self.logger.info(f"📋 Lista {i}: No se pudo leer")
                return suscriptores

            # Saltar el primer elemento (encabezados) y procesar el resto
            for i in range(1, cantidad_suscriptores):  # empieza en 1 → segundo elemento
                try:
                    datos_suscriptor = suscriptores_elementos.nth(i).locator('> div')
                    self.logger.info(f"🔍 Procesando elemento {i}, divs encontrados: {datos_suscriptor.count()}")

                    # Extraer exactamente 4 campos como en el código original
                    correo = datos_suscriptor.nth(0).inner_text().strip() if datos_suscriptor.count() > 0 else ""
                    lista = datos_suscriptor.nth(1).inner_text().strip() if datos_suscriptor.count() > 1 else ""
                    estado = datos_suscriptor.nth(2).inner_text().strip() if datos_suscriptor.count() > 2 else ""
                    calidad = datos_suscriptor.nth(3).inner_text().strip() if datos_suscriptor.count() > 3 else ""

                    self.logger.info(f"✅ Elemento {i}: correo={correo}, lista={lista}, estado={estado}, calidad={calidad}")

                    # Solo añadir si hay datos válidos (al menos correo)
                    if correo:
                        suscriptores.append(SubscriberTableData(
                            correo=correo,
                            lista=lista,
                            estado=estado,
                            calidad=calidad
                        ))

                except Exception as e:
                    self.logger.error(f"❌ Error procesando elemento {i}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"❌ Error crítico extrayendo suscriptores de tabla: {e}")

        self.logger.info(f"📈 {len(suscriptores)} suscriptores extraídos de la tabla")
        return suscriptores

    def navegar_a_detalle_suscriptores(self, page: Page, campaign_id: int) -> bool:
        """
        Navega a la sección de detalles de suscriptores de la campaña.
        Devuelve True si se navegó correctamente, False en caso contrario.
        """
        try:
            url_base = self.config.get("url_base", "")
            url = f"{url_base}/report/campaign/{campaign_id}/"
            self.logger.info(f"🗺️ Navegando a: {url}")
            page.goto(url, timeout=30000)

            self.logger.info("🔗 Buscando enlace 'Detalles suscriptores'")
            detalles_link = page.get_by_role("link", name="Detalles suscriptores")
            detalles_link.wait_for(timeout=15000)
            detalles_link.click()
            self.logger.info("✅ Clic en 'Detalles suscriptores' exitoso")

            page.wait_for_load_state("domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)  # Espera adicional para cargar contenido
            self.logger.info("✅ Página de detalles de suscriptores cargada")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error navegando a Detalles suscriptores: {e}")
            return False

    def extraer_datos_filtro(self, page: Page, campania: CampaignBasicInfo, filter_type: str) -> SubscriberFilterResult:
        """
        Función auxiliar para extraer datos de un filtro específico.
        """
        suscriptores_resultado = []

        try:
            # Usar función rápida primero, luego optimizada si hay muchas páginas
            self.logger.info("📁 Detectando número de páginas...")
            paginas_totales = obtener_total_paginas(page)
            if paginas_totales > 3:  # Si hay más de 3 páginas, optimizar items por página
                self.logger.info(f"🚀 Detectadas {paginas_totales} páginas, optimizando items por página...")
                paginas_totales = obtener_total_paginas(page)
            self.logger.info(f"📄 Procesando {paginas_totales} páginas en total")

            for numero_pagina in range(1, paginas_totales + 1):
                self.logger.info(f"📃 Procesando página {numero_pagina}/{paginas_totales}")
                try:
                    # Extraer suscriptores de la página actual
                    suscriptores_pagina = self.extraer_suscriptores_tabla(page, 4)
                    self.logger.info(f"✅ Página {numero_pagina}: {len(suscriptores_pagina)} suscriptores extraídos")

                    # Procesar cada suscriptor de esta página
                    for suscriptor in suscriptores_pagina:
                        suscriptores_resultado.append(SubscriberScrapingData(
                            proyecto=campania.name or "",
                            lista=suscriptor.lista,
                            correo=suscriptor.correo,
                            lista2=suscriptor.lista,
                            estado=suscriptor.estado,
                            calidad=suscriptor.calidad
                        ))
                except Exception as e:
                    self.logger.error(f"❌ Error procesando página {numero_pagina}: {e}")
                    continue

                # Navegar a la siguiente página si no es la última
                if numero_pagina < paginas_totales:
                    self.logger.info(f"➡️ Navegando a página {numero_pagina + 1}")
                    if not navegar_siguiente_pagina(page, numero_pagina):
                        self.logger.error(f"❌ No se pudo navegar a la página {numero_pagina + 1}")
                        break

        except Exception as e:
            self.logger.error(f"❌ Error crítico extrayendo datos del filtro: {e}")

        self.logger.info(f"📈 Total suscriptores extraídos: {len(suscriptores_resultado)}")

        return SubscriberFilterResult(
            filter_type=filter_type,
            subscribers=suscriptores_resultado,
            total_pages=paginas_totales,
            total_subscribers=len(suscriptores_resultado)
        )

    def extraer_hard_bounces(self, page: Page, campania: CampaignBasicInfo, campaign_id: int) -> List[SubscriberScrapingData]:
        """
        Scrapea Hard bounces de la campaña y devuelve filas.
        """
        suscriptores_resultado = []
        try:
            self.navegar_a_detalle_suscriptores(page, campaign_id)
            self.seleccionar_filtro(page, "Hard bounces")

            # Optimización: Obtener el máximo de elementos por página primero
            paginas_totales = obtener_total_paginas(page)

            for numero_pagina in range(1, paginas_totales + 1):
                # Extraer suscriptores de la página actual
                suscriptores_pagina = self.extraer_suscriptores_tabla(page, 4)

                # Procesar cada suscriptor de esta página
                for suscriptor in suscriptores_pagina:
                    suscriptores_resultado.append(SubscriberScrapingData(
                        proyecto=campania.name or "",
                        lista=suscriptor.lista,
                        correo=suscriptor.correo,
                        lista2=suscriptor.lista,
                        estado=suscriptor.estado,
                        calidad=suscriptor.calidad
                    ))

                # Navegar a la siguiente página si no es la última
                if numero_pagina < paginas_totales:
                    if not navegar_siguiente_pagina(page, numero_pagina):
                        self.logger.error(f"No se pudo navegar a la página {numero_pagina + 1}")
                        break
        except Exception as e:
            self.logger.error(f"Error generando Hard bounces para campaña {campaign_id}: {e}")

        return suscriptores_resultado

    def extraer_no_abiertos(self, page: Page, campania: CampaignBasicInfo, campaign_id: int) -> List[SubscriberScrapingData]:
        """
        Scrapea No abiertos en la página de detalles abierta y devuelve filas.
        Nota: Asume que ya estamos en la vista de 'Detalles suscriptores' de la campaña.
        """
        suscriptores_resultado = []
        try:
            self.seleccionar_filtro(page, "No abiertos")

            # La función obtener_total_paginas ya optimiza elementos por página
            paginas_totales = obtener_total_paginas(page)

            for numero_pagina in range(1, paginas_totales + 1):
                # Extraer suscriptores de la página actual
                suscriptores_pagina = self.extraer_suscriptores_tabla(page, 4)

                # Procesar cada suscriptor de esta página
                for suscriptor in suscriptores_pagina:
                    suscriptores_resultado.append(SubscriberScrapingData(
                        proyecto=campania.name or "",
                        lista=suscriptor.lista,
                        correo=suscriptor.correo,
                        lista2=suscriptor.lista,
                        estado=suscriptor.estado,
                        calidad=suscriptor.calidad
                    ))

                # Navegar a la siguiente página si no es la última
                if numero_pagina < paginas_totales:
                    if not navegar_siguiente_pagina(page, numero_pagina):
                        self.logger.error(f"No se pudo navegar a la página {numero_pagina + 1}")
                        break
        except Exception as e:
            self.logger.error(f"Error generando No abiertos para campaña {campaign_id}: {e}")

        return suscriptores_resultado

    def extraer_suscriptores_optimizado(self, page: Page, campania: CampaignBasicInfo, campaign_id: int) -> Tuple[List[SubscriberScrapingData], List[SubscriberScrapingData]]:
        """
        Optimización: Extrae tanto hard bounces como no abiertos en una sola navegación
        para reducir el tiempo total de ejecución.
        Devuelve: (hard_bounces, no_abiertos)
        """
        hard_bounces = []
        no_abiertos = []

        try:
            # Navegar una sola vez a la sección de detalles
            self.logger.info(f"🗺️ Navegando a detalles de suscriptores para campaña {campaign_id}")
            if not self.navegar_a_detalle_suscriptores(page, campaign_id):
                self.logger.error(f"❌ No se pudo navegar a detalles para campaña {campaign_id}")
                return hard_bounces, no_abiertos

            self.logger.info("✅ Navegación exitosa a detalles de suscriptores")

            # Extraer Hard bounces primero
            self.logger.info(f"📦 Extrayendo Hard bounces para campaña {campaign_id}")
            try:
                if self.seleccionar_filtro(page, "Hard bounces"):
                    result = self.extraer_datos_filtro(page, campania, "Hard bounces")
                    hard_bounces = result.subscribers
                    self.logger.info(f"✅ {len(hard_bounces)} hard bounces extraídos")
                else:
                    self.logger.warning("⚠️ No se pudo seleccionar filtro Hard bounces")
            except Exception as e:
                self.logger.error(f"❌ Error extrayendo hard bounces: {e}")

            # Extraer No abiertos después
            self.logger.info(f"📧 Extrayendo No abiertos para campaña {campaign_id}")
            try:
                if self.seleccionar_filtro(page, "No abiertos"):
                    result = self.extraer_datos_filtro(page, campania, "No abiertos")
                    no_abiertos = result.subscribers
                    self.logger.info(f"✅ {len(no_abiertos)} no abiertos extraídos")
                else:
                    self.logger.warning("⚠️ No se pudo seleccionar filtro No abiertos")
            except Exception as e:
                self.logger.error(f"❌ Error extrayendo no abiertos: {e}")

        except Exception as e:
            self.logger.error(f"❌ Error crítico en extracción optimizada para campaña {campaign_id}: {e}")

        self.logger.info(f"📈 Resumen extracción campaña {campaign_id}: {len(hard_bounces)} hard bounces, {len(no_abiertos)} no abiertos")
        return hard_bounces, no_abiertos

    def extraer_suscriptores_completos(
        self,
        page: Page,
        campania: CampaignBasicInfo,
        campaign_id: int,
        config: Optional[SubscriberExtractionConfig] = None
    ) -> CampaignSubscriberReport:
        """
        Extrae todos los tipos de suscriptores de una campaña usando configuración.
        """
        if config is None:
            config = SubscriberExtractionConfig()

        session = ScrapingSession(
            session_id=f"campaign_{campaign_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            campaign_ids=[campaign_id]
        )

        report = CampaignSubscriberReport(
            campaign_id=campaign_id,
            campaign_name=campania.name or "",
            fecha_envio=campania.date_sent or ""
        )

        start_time = datetime.now()

        try:
            # Extraer hard bounces y no abiertos usando el método optimizado
            if config.use_optimized_extraction:
                hard_bounces, no_abiertos = self.extraer_suscriptores_optimizado(page, campania, campaign_id)
                if config.extract_hard_bounces:
                    report.hard_bounces = hard_bounces
                if config.extract_no_abiertos:
                    report.no_abiertos = no_abiertos
            else:
                # Extraer individualmente
                if config.extract_hard_bounces:
                    report.hard_bounces = self.extraer_hard_bounces(page, campania, campaign_id)
                if config.extract_no_abiertos:
                    report.no_abiertos = self.extraer_no_abiertos(page, campania, campaign_id)

            # Los abiertos, clics y soft bounces normalmente se obtienen por API
            # pero si se requiere scraping se puede implementar aquí

            session.total_subscribers_extracted = report.total_subscribers
            session.complete_session()

        except Exception as e:
            session.add_error(str(e))
            session.complete_session()
            raise

        end_time = datetime.now()
        report.processing_time_seconds = (end_time - start_time).total_seconds()

        return report