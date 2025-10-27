"""
Scraper para endpoints de campañas que NO existen en la API de Acumbamail

IMPORTANTE: Este archivo contiene métodos ESQUELETO que necesitas implementar.
Cada método tiene comentarios TODO indicando qué necesitas hacer.
"""
from typing import List, Optional, Dict
from playwright.sync_api import Page
import time
from datetime import datetime

from ..base import BaseScraper, ScrapingConfig
from ..models.campanias import (
    ScrapedNonOpener,
    ScrapedHardBounce,
    ScrapedCampaignStats,
    ScrapedGeographicStats,
    ScrapedDeviceStats,
    ScrapedCampaignData,
    ScrapedCampaignUrl
)
from ..utils.selectors import CampaignSelectors, CommonSelectors
from ..utils.navigation import NavigationHelper
from src.shared.logging.logger import get_logger

logger = get_logger()


class CampaignsScraper(BaseScraper):
    """
    Scraper para endpoints de campañas que no existen en API
    
    Proporciona acceso a datos como:
    - Suscriptores que NO abrieron emails
    - Hard bounces detallados  
    - Estadísticas geográficas y por dispositivo
    """
    
    def __init__(self, page: Page, config: Optional[ScrapingConfig] = None):
        super().__init__(page, config)
        self.selectors = CampaignSelectors()
        self.common = CommonSelectors()
        self.navigation = NavigationHelper(page)
    
    # === MÉTODO PRINCIPAL: NO-OPENERS ===
    def get_non_openers(self, campaign_id: int) -> List[ScrapedNonOpener]:
        """
        ⭐ MÉTODO PRIORITARIO: Obtener suscriptores que NO abrieron la campaña
        
        Este es el método más importante ya que esta información no está 
        disponible en la API de Acumbamail.
        
        Args:
            campaign_id: ID de la campaña
            
        Returns:
            Lista de suscriptores que no abrieron el email
            
        TODO: IMPLEMENTAR ESTE MÉTODO PRIMERO
        """
        logger.info(f"🔍 Iniciando scraping de no-openers para campaña {campaign_id}")
        start_time = time.time()
        
        def _scrape_non_openers():
            # TODO: 1. Navegar a la página de la campaña
            self.navigate_to_campaign(campaign_id)
            
            # TODO: 2. Ir a la sección correcta (estadísticas/suscriptores)
            # self.navigation.go_to_campaign_tab(campaign_id, "statistics")
            
            # TODO: 3. Buscar la sección de "No abrieron" / "Unopened"
            # self.wait_for_element(self.selectors.non_opener_emails)
            
            # TODO: 4. Extraer emails con paginación
            all_non_openers = []
            
            def extract_emails_from_page(elements):
                """
                TODO: Implementar extracción de emails de la página actual
                
                Args:
                    elements: Lista de elementos HTML encontrados
                    
                Returns:
                    Lista de objetos ScrapedNonOpener
                """
                page_emails = []
                
                # TODO: Iterar por cada elemento y extraer:
                # - Email del suscriptor
                # - Fecha de envío (si está disponible)  
                # - Nombre del suscriptor (si está disponible)
                # - Lista de origen (si está disponible)
                
                for element in elements:
                    try:
                        # TODO: Extraer email del elemento
                        # email = element.text_content().strip()
                        # O usar selector más específico si es una tabla:
                        # email = element.query_selector(".email-cell").text_content()
                        
                        # TODO: Crear objeto ScrapedNonOpener
                        # non_opener = ScrapedNonOpener(
                        #     email=email,
                        #     campaign_id=campaign_id,
                        #     date_sent=self._extract_date_sent(element),
                        #     subscriber_name=self._extract_subscriber_name(element),
                        #     list_name=self._extract_list_name(element)
                        # )
                        # page_emails.append(non_opener)
                        
                        # PLACEHOLDER: Remover cuando implementes
                        pass
                        
                    except Exception as e:
                        logger.warning(f"Error extrayendo email de elemento: {e}")
                        continue
                
                return page_emails
            
            # TODO: 5. Usar paginación automática
            # all_non_openers = self.handle_pagination(
            #     item_selector=self.selectors.non_opener_emails,
            #     next_button_selector=self.selectors.next_page_button,
            #     extract_func=extract_emails_from_page
            # )
            
            # PLACEHOLDER: Remover cuando implementes
            logger.warning("⚠️  get_non_openers() NO IMPLEMENTADO - retornando lista vacía")
            
            duration = time.time() - start_time
            logger.info(f"✅ No-openers scraping completado: {len(all_non_openers)} emails en {duration:.1f}s")
            return all_non_openers
        
        return self.wait_and_retry(_scrape_non_openers)
    
    # === MÉTODO SECUNDARIO: HARD BOUNCES ===
    def get_hard_bounces(self, campaign_id: int) -> List[ScrapedHardBounce]:
        """
        🔧 Obtener hard bounces detallados de la campaña
        
        Aunque la API tiene algunos datos de bounces, puede que falten detalles
        como razones específicas, códigos de error, etc.
        
        Args:
            campaign_id: ID de la campaña
            
        Returns:
            Lista de hard bounces con información detallada
            
        TODO: IMPLEMENTAR DESPUÉS DE get_non_openers()
        """
        logger.info(f"🔍 Iniciando scraping de hard bounces para campaña {campaign_id}")
        
        def _scrape_hard_bounces():
            # TODO: 1. Navegar a la sección de hard bounces
            self.navigate_to_campaign(campaign_id)
            
            # TODO: 2. Buscar sección de bounces/errores
            # self.navigation.go_to_campaign_tab(campaign_id, "bounces")
            
            # TODO: 3. Extraer hard bounces con detalles
            all_hard_bounces = []
            
            def extract_bounces_from_page(elements):
                """TODO: Extraer hard bounces de la página"""
                page_bounces = []
                
                for element in elements:
                    try:
                        # TODO: Extraer información del bounce:
                        # - Email
                        # - Fecha del bounce  
                        # - Razón específica
                        # - Código de error
                        # - Detalles adicionales
                        
                        # bounce = ScrapedHardBounce(
                        #     email=self._extract_bounce_email(element),
                        #     campaign_id=campaign_id,
                        #     bounce_date=self._extract_bounce_date(element),
                        #     bounce_reason=self._extract_bounce_reason(element),
                        #     bounce_code=self._extract_bounce_code(element)
                        # )
                        # page_bounces.append(bounce)
                        
                        pass  # PLACEHOLDER
                        
                    except Exception as e:
                        logger.warning(f"Error extrayendo bounce: {e}")
                        continue
                
                return page_bounces
            
            # TODO: 4. Usar paginación si es necesario
            # all_hard_bounces = self.handle_pagination(...)
            
            # PLACEHOLDER
            logger.warning("⚠️  get_hard_bounces() NO IMPLEMENTADO - retornando lista vacía")
            return all_hard_bounces
        
        return self.wait_and_retry(_scrape_hard_bounces)
    
    # === MÉTODO AVANZADO: ESTADÍSTICAS EXTENDIDAS ===
    def get_extended_stats(self, campaign_id: int) -> ScrapedCampaignStats:
        """
        📊 Obtener estadísticas avanzadas no disponibles en API
        
        Incluye datos como:
        - Estadísticas geográficas (por país)
        - Estadísticas por dispositivo
        - Distribución por horarios
        
        Args:
            campaign_id: ID de la campaña
            
        Returns:
            Estadísticas extendidas de la campaña
            
        TODO: IMPLEMENTAR COMO ÚLTIMO (OPCIONAL)
        """
        logger.info(f"📊 Iniciando scraping de estadísticas extendidas para campaña {campaign_id}")
        start_time = time.time()
        
        def _scrape_extended_stats():
            # TODO: 1. Navegar a sección de estadísticas avanzadas
            self.navigate_to_campaign(campaign_id)
            
            # TODO: 2. Extraer estadísticas básicas como verificación
            stats = ScrapedCampaignStats(campaign_id=campaign_id)
            
            # TODO: 3. Extraer números básicos
            # stats.total_sent = self._extract_stat_number(self.selectors.total_sent)
            # stats.total_opened = self._extract_stat_number(self.selectors.total_opened)
            # stats.total_not_opened = self._extract_stat_number(self.selectors.total_not_opened)
            
            # TODO: 4. Extraer estadísticas geográficas
            # stats.geographic_stats = self._scrape_geographic_stats()
            
            # TODO: 5. Extraer estadísticas por dispositivo  
            # stats.device_stats = self._scrape_device_stats()
            
            # TODO: 6. Extraer estadísticas temporales (hora/día)
            # stats.hourly_stats = self._scrape_hourly_stats()
            # stats.daily_stats = self._scrape_daily_stats()
            
            # Metadatos
            stats.scraped_at = datetime.now().isoformat()
            stats.scraping_duration = time.time() - start_time
            
            # PLACEHOLDER
            logger.warning("⚠️  get_extended_stats() NO IMPLEMENTADO - retornando stats vacías")
            return stats
        
        return self.wait_and_retry(_scrape_extended_stats)
    
    # === MÉTODO: URLS DE CAMPAÑA ===
    def get_campaign_urls(self, campaign_id: int) -> List[ScrapedCampaignUrl]:
        """
        🔗 Obtener URLs de la campaña con estadísticas de clics

        Navega a la página de seguimiento de URLs y extrae:
        - URL completa
        - Número total de clics
        - Porcentaje de abridores que hicieron clic

        Args:
            campaign_id: ID de la campaña

        Returns:
            Lista de URLs con sus estadísticas de clics
        """
        logger.info(f"🔗 Iniciando scraping de URLs para campaña {campaign_id}")
        start_time = time.time()

        def _scrape_urls():
            campaign_urls = []

            try:
                # 1. Navegar a la página de seguimiento de URLs
                url_page = f"https://acumbamail.com/report/campaign/{campaign_id}/url/"
                logger.info(f"🌐 Navegando a: {url_page}")
                self.page.goto(url_page, wait_until="networkidle", timeout=60000)

                # Esperar a que la página cargue completamente
                self.page.wait_for_load_state("networkidle", timeout=30000)
                self.page.wait_for_timeout(1000)  # Espera adicional para estabilidad

                # 2. Buscar la lista de URLs
                # Basándonos en el snapshot de BrowserMCP, las URLs están en una lista (<ul> o <ol>)
                # Primero intentamos encontrar la lista principal
                try:
                    # Esperar a que aparezca al menos un listitem con URL
                    self.page.wait_for_selector("ul li, ol li", timeout=10000)
                    logger.info("✅ Lista de URLs encontrada")
                except Exception as e:
                    logger.warning(f"⚠️  No se encontraron URLs en la campaña {campaign_id}: {e}")
                    return []

                # 3. Contar items primero
                list_items_count = self.page.locator("ul li, ol li").count()
                logger.info(f"📊 Se encontraron {list_items_count} items en la lista")

                # Filtrar solo los items que contienen URLs (ignorar encabezados)
                # Procesar item por item, volviendo a la página principal después de cada navegación
                for item_index in range(list_items_count):
                    # Re-obtener el item en cada iteración para evitar elementos obsoletos
                    item = self.page.locator("ul li, ol li").nth(item_index)
                    try:
                        # Obtener el texto completo del item
                        item_text = item.text_content()

                        if not item_text:
                            continue

                        # Filtrar el encabezado "Url Han hecho clic Acciones"
                        if "Url Han hecho clic Acciones" in item_text or "Han hecho clic" in item_text:
                            continue

                        # Buscar enlaces dentro del item - pueden contener la URL completa en href o title
                        import re
                        url = None

                        # Método 1: Buscar enlace <a> con href (URLs externas directas)
                        links_locator = item.locator('a')
                        links_count = links_locator.count()

                        for link_idx in range(links_count):
                            link = links_locator.nth(link_idx)
                            href = link.get_attribute('href')
                            # Si encuentra URL externa directa (poco común)
                            if href and href.startswith('http'):
                                url = href
                                break

                        # Método 2: Buscar enlace "Detalles" y extraer URL de la página de detalles
                        if not url:
                            # Buscar enlace que contiene "Detalles" o "/click/.../details/"
                            details_link = None
                            for link_idx in range(links_count):
                                link = links_locator.nth(link_idx)
                                href = link.get_attribute('href')
                                link_text = link.text_content().strip()
                                if href and ('/click/' in href and '/details/' in href) or link_text == 'Detalles':
                                    details_link = href
                                    break

                            if details_link:
                                # Navegar a la página de detalles para obtener la URL completa
                                try:
                                    # Construir URL completa si es relativa
                                    if details_link.startswith('/'):
                                        details_url = f"https://acumbamail.com{details_link}"
                                    else:
                                        details_url = details_link

                                    logger.debug(f"   🔍 Navegando a detalles: {details_url}")

                                    # Guardar URL actual para volver
                                    current_url = self.page.url

                                    # Navegar a detalles
                                    self.page.goto(details_url, wait_until="domcontentloaded", timeout=15000)
                                    self.page.wait_for_timeout(500)

                                    # Buscar la URL completa en la página de detalles
                                    # La URL suele estar en un elemento con la clase que indica la URL rastreada
                                    page_content = self.page.content()

                                    # Buscar URLs completas en el HTML
                                    url_patterns = [
                                        r'(https?://[^"\s<>]+)',  # URL entre comillas o espacios
                                    ]

                                    for pattern in url_patterns:
                                        urls_found = re.findall(pattern, page_content)
                                        for found_url in urls_found:
                                            # Filtrar URLs que NO son relevantes
                                            skip_domains = [
                                                'acumbamail.com',
                                                'clickacm.com',
                                                'w3.org',
                                                'schema.org',
                                                'google.com/recaptcha',
                                                'gstatic.com'
                                            ]

                                            # Verificar si la URL debe ser saltada
                                            should_skip = any(domain in found_url.lower() for domain in skip_domains)

                                            # Además, la URL debe ser similar a la truncada que vimos
                                            # Extraer el inicio de la URL truncada del item_text
                                            truncated_match = re.search(r'(https?://[^\s]{20,})', item_text)
                                            if truncated_match:
                                                truncated_url_start = truncated_match.group(1)[:50]  # Primeros 50 caracteres
                                                # La URL encontrada debe empezar similar a la truncada
                                                if not should_skip and found_url.startswith(truncated_url_start[:30]):
                                                    url = found_url
                                                    logger.debug(f"   ✅ URL completa encontrada en detalles: {url[:80]}...")
                                                    break

                                        if url:
                                            break

                                    # Volver a la página de lista de URLs
                                    self.page.goto(current_url, wait_until="networkidle", timeout=15000)
                                    self.page.wait_for_timeout(1000)  # Esperar más tiempo para estabilidad

                                except Exception as e:
                                    logger.warning(f"   ⚠️ Error obteniendo URL desde detalles: {e}")

                        # Método 3: Extraer del texto visible (último recurso, puede estar truncada)
                        if not url:
                            url_match = re.search(r'(https?://\S+)', item_text)
                            if url_match:
                                url = url_match.group(1)
                                logger.debug(f"   ⚠️ Usando URL del texto (puede estar truncada): {url}")
                            else:
                                continue

                        # Patrón para buscar clics: "X (Y% abridores)" o "X (Y,Y% abridores)"
                        clicks_match = re.search(r'(\d+)\s*\((\d+[,.]?\d*)\s*%\s*abridores\)', item_text)

                        if clicks_match:
                            clicks = int(clicks_match.group(1))
                            percentage_str = clicks_match.group(2).replace(',', '.')
                            percentage = float(percentage_str)
                        else:
                            # Si no se encuentra el patrón, intentar buscar solo el número
                            clicks_simple = re.search(r'(\d+)\s+\(', item_text)
                            if clicks_simple:
                                clicks = int(clicks_simple.group(1))
                                percentage = 0.0
                            else:
                                clicks = 0
                                percentage = 0.0

                        # Crear objeto ScrapedCampaignUrl
                        campaign_url = ScrapedCampaignUrl(
                            url=url,
                            clicks=clicks,
                            click_percentage=percentage,
                            campaign_id=campaign_id
                        )

                        campaign_urls.append(campaign_url)
                        logger.debug(f"   ✅ URL extraída: {campaign_url.short_url} - {clicks} clics ({percentage}%)")

                    except Exception as e:
                        logger.warning(f"⚠️  Error procesando item de URL: {e}")
                        continue

                duration = time.time() - start_time
                logger.info(f"✅ URLs scraping completado: {len(campaign_urls)} URLs en {duration:.1f}s")
                return campaign_urls

            except Exception as e:
                logger.error(f"❌ Error en scraping de URLs: {e}")
                return []

        return self.wait_and_retry(_scrape_urls)

    # === MÉTODO COMBINADO ===
    def get_complete_campaign_data(self, campaign_id: int,
                                 include_non_openers: bool = True,
                                 include_hard_bounces: bool = True,
                                 include_extended_stats: bool = False,
                                 include_campaign_urls: bool = True) -> ScrapedCampaignData:
        """
        🎯 Obtener todos los datos scrapeados de una campaña

        Este método combina todos los otros métodos para obtener
        un conjunto completo de datos.

        Args:
            campaign_id: ID de la campaña
            include_non_openers: Si incluir no-openers (recomendado: True)
            include_hard_bounces: Si incluir hard bounces (recomendado: True)
            include_extended_stats: Si incluir stats extendidas (opcional: False)
            include_campaign_urls: Si incluir URLs de campaña (recomendado: True)

        Returns:
            Objeto con todos los datos scrapeados
        """
        logger.info(f"🎯 Iniciando scraping completo de campaña {campaign_id}")
        start_time = time.time()
        
        # Inicializar contenedor de datos
        campaign_data = ScrapedCampaignData(
            campaign_id=campaign_id,
            scraped_at=datetime.now().isoformat()
        )
        
        # Obtener no-openers si se solicita
        if include_non_openers:
            try:
                logger.info("📧 Obteniendo no-openers...")
                campaign_data.non_openers = self.get_non_openers(campaign_id)
                campaign_data.scraping_methods.append("get_non_openers")
                logger.info(f"✅ No-openers obtenidos: {len(campaign_data.non_openers)}")
            except Exception as e:
                logger.error(f"❌ Error obteniendo no-openers: {e}")
        
        # Obtener hard bounces si se solicita
        if include_hard_bounces:
            try:
                logger.info("💥 Obteniendo hard bounces...")
                campaign_data.hard_bounces = self.get_hard_bounces(campaign_id)
                campaign_data.scraping_methods.append("get_hard_bounces")
                logger.info(f"✅ Hard bounces obtenidos: {len(campaign_data.hard_bounces)}")
            except Exception as e:
                logger.error(f"❌ Error obteniendo hard bounces: {e}")
        
        # Obtener URLs de campaña si se solicita
        if include_campaign_urls:
            try:
                logger.info("🔗 Obteniendo URLs de campaña...")
                campaign_data.campaign_urls = self.get_campaign_urls(campaign_id)
                campaign_data.scraping_methods.append("get_campaign_urls")
                logger.info(f"✅ URLs de campaña obtenidas: {len(campaign_data.campaign_urls)}")
            except Exception as e:
                logger.error(f"❌ Error obteniendo URLs de campaña: {e}")

        # Obtener estadísticas extendidas si se solicita
        if include_extended_stats:
            try:
                logger.info("📊 Obteniendo estadísticas extendidas...")
                campaign_data.extended_stats = self.get_extended_stats(campaign_id)
                campaign_data.scraping_methods.append("get_extended_stats")
                logger.info("✅ Estadísticas extendidas obtenidas")
            except Exception as e:
                logger.error(f"❌ Error obteniendo estadísticas extendidas: {e}")

        duration = time.time() - start_time
        logger.info(f"🎉 Scraping completo finalizado en {duration:.1f}s")
        logger.info(f"📊 Resumen: {campaign_data.summary}")

        return campaign_data
    
    # === MÉTODOS AUXILIARES (IMPLEMENTAR SEGÚN NECESIDAD) ===
    
    def _extract_stat_number(self, selector: str) -> int:
        """
        TODO: Extraer número de un elemento estadístico
        
        Args:
            selector: Selector CSS del elemento
            
        Returns:
            Número extraído o 0 si no se encuentra
        """
        try:
            text = self.get_text_content(selector, "0")
            # TODO: Limpiar texto y convertir a número
            # Ejemplo: "1,234 emails" -> 1234
            clean_text = text.replace(",", "").replace(".", "")
            numbers = ''.join(filter(str.isdigit, clean_text))
            return int(numbers) if numbers else 0
        except Exception as e:
            logger.warning(f"Error extrayendo número de '{selector}': {e}")
            return 0
    
    def _extract_date_sent(self, element) -> Optional[str]:
        """TODO: Extraer fecha de envío de un elemento"""
        # TODO: Implementar según estructura HTML real
        return None
    
    def _extract_subscriber_name(self, element) -> Optional[str]:
        """TODO: Extraer nombre del suscriptor de un elemento"""
        # TODO: Implementar según estructura HTML real  
        return None
    
    def _extract_list_name(self, element) -> Optional[str]:
        """TODO: Extraer nombre de la lista de un elemento"""
        # TODO: Implementar según estructura HTML real
        return None
    
    def _scrape_geographic_stats(self) -> List[ScrapedGeographicStats]:
        """TODO: Extraer estadísticas geográficas"""
        # TODO: Buscar sección de estadísticas por país
        # TODO: Extraer datos de cada país
        logger.warning("⚠️  _scrape_geographic_stats() NO IMPLEMENTADO")
        return []
    
    def _scrape_device_stats(self) -> List[ScrapedDeviceStats]:
        """TODO: Extraer estadísticas por dispositivo"""
        # TODO: Buscar sección de estadísticas por dispositivo
        # TODO: Extraer datos de cada tipo de dispositivo
        logger.warning("⚠️  _scrape_device_stats() NO IMPLEMENTADO")
        return []
    
    def _scrape_hourly_stats(self) -> Dict[str, int]:
        """TODO: Extraer estadísticas por hora del día"""
        logger.warning("⚠️  _scrape_hourly_stats() NO IMPLEMENTADO")
        return {}
    
    def _scrape_daily_stats(self) -> Dict[str, int]:
        """TODO: Extraer estadísticas por día de la semana"""
        logger.warning("⚠️  _scrape_daily_stats() NO IMPLEMENTADO")
        return {}


# === INSTRUCCIONES DE IMPLEMENTACIÓN ===
"""
🚀 GUÍA DE IMPLEMENTACIÓN:

1️⃣ PRIMERO: Implementar get_non_openers()
   - Es el método más importante
   - Actualizar selectores en selectors.py
   - Probar con una campaña real
   - Manejar paginación

2️⃣ SEGUNDO: Implementar get_hard_bounces()  
   - Similar a no-openers pero con más detalles
   - Extraer razones de bounce
   - Códigos de error si están disponibles

3️⃣ TERCERO: Implementar get_extended_stats() (opcional)
   - Estadísticas avanzadas
   - Datos geográficos y por dispositivo
   - Solo si necesitas estos datos

📝 PASOS PARA CADA MÉTODO:

1. Inspeccionar la página web real en el navegador
2. Anotar los selectores CSS correctos en selectors.py
3. Implementar la lógica de extracción
4. Manejar errores y casos edge
5. Probar con datos reales
6. Optimizar rendimiento

🔧 TIPS:
- Usa screenshots automáticos en errores para debug
- Implementa timeouts apropiados
- Maneja la paginación cuidadosamente  
- Loguea todo para debugging
- Prueba con diferentes campañas
"""