"""
Scraper para obtener URLs de campañas desde la página de seguimiento de URLs de Acumbamail
"""
from typing import List, Optional
from playwright.sync_api import Page
import time
import re
from datetime import datetime

from ..base import BaseScraper, ScrapingConfig
from ...logger import logger


class CampaignURLScraper(BaseScraper):
    """
    Scraper para obtener URLs de campañas desde la página de seguimiento de URLs
    """
    
    def __init__(self, page: Page, config: Optional[ScrapingConfig] = None):
        super().__init__(page, config)
    
    def get_campaign_urls(self, campaign_id: int) -> List[str]:
        """
        Obtener URLs de seguimiento para una campaña específica
        
        Args:
            campaign_id: ID de la campaña
            
        Returns:
            Lista de URLs encontradas en la campaña
        """
        logger.info(f"🔍 Iniciando scraping de URLs para campaña {campaign_id}")
        start_time = time.time()
        
        def _scrape_urls():
            # Navegar a la página de seguimiento de URLs de la campaña
            url = f"{self.config.base_url}/report/campaign/{campaign_id}/url/"
            logger.debug(f"Navegando a: {url}")
            
            self.page.goto(url, wait_until="networkidle", timeout=self.config.timeout)
            
            # Verificar que estamos en la página correcta
            if f"report/campaign/{campaign_id}/url/" not in self.page.url:
                raise Exception(f"No se pudo navegar a URLs de campaña {campaign_id}. URL actual: {self.page.url}")
            
            logger.debug(f"✅ Página cargada correctamente. URL: {self.page.url}")
            
            # Esperar a que se carguen las URLs - usando diferentes estrategias
            wait_success = False
            selectors_to_try = ["ul", "li", "a", ".url-tracking", "[data-testid='url-list']"]
            
            for selector in selectors_to_try:
                try:
                    logger.debug(f"⏳ Esperando elemento: {selector}")
                    self.page.wait_for_selector(selector, timeout=15000)
                    logger.debug(f"✅ Encontrado elemento con selector: {selector}")
                    wait_success = True
                    break
                except Exception as e:
                    logger.debug(f"⚠️ No se encontró elemento con selector '{selector}': {e}")
                    continue
            
            if not wait_success:
                logger.warning("⚠️ No se encontró ningún selector conocido en la página")
            
            # Extraer URLs de la lista
            urls = self._extract_urls_from_page()
            
            duration = time.time() - start_time
            logger.info(f"✅ URLs scraping completado: {len(urls)} URLs encontradas en {duration:.1f}s")
            return urls
        
        return self.wait_and_retry(_scrape_urls)
    
    def _extract_urls_from_page(self) -> List[str]:
        """
        Extraer URLs de la página actual de seguimiento de URLs
        
        Returns:
            Lista de URLs extraídas
        """
        try:
            logger.debug("🔍 Iniciando extracción de URLs de la página")
            
            # Intentar múltiples estrategias para encontrar los elementos de URLs
            # Estrategia 1: Buscar listas con elementos de tipo listitem
            list_items = []
            
            # Intentar con diferentes selectores
            strategies = [
                lambda: self.page.get_by_role("list").get_by_role("listitem").all(),
                lambda: self.page.locator("ul li").all(),  # Alternativa con CSS
                lambda: self.page.locator("li").all(),     # Alternativa más genérica
            ]
            
            for i, strategy in enumerate(strategies):
                try:
                    list_items = strategy()
                    if list_items:
                        logger.debug(f"✅ Estrategia {i+1} encontró {len(list_items)} elementos")
                        break
                except Exception as e:
                    logger.debug(f"⚠️ Estrategia {i+1} fallida: {e}")
                    continue
            
            if not list_items:
                logger.warning("⚠️ No se encontraron elementos de lista en la página de URLs")
                
                # Hacer un screenshot para debugging si estamos en modo verbose
                try:
                    import os
                    if os.getenv("DEBUG_URL_SCRAPING", "0") == "1":
                        screenshot_path = f"/tmp/debug_url_scraping_{int(time.time())}.png"
                        self.page.screenshot(path=screenshot_path)
                        logger.info(f"📸 Screenshot de debugging guardado en: {screenshot_path}")
                except:
                    pass  # No hacer nada si falla el screenshot
                
                return []
            
            urls = []
            logger.debug(f"🔍 Procesando {len(list_items)} elementos de lista")
            
            for i, item in enumerate(list_items):
                try:
                    item_text = item.text_content().strip()
                    logger.debug(f"📄 Elemento {i+1} texto: '{item_text}'")
                    
                    # Extraer la URL del texto del elemento
                    # La URL normalmente es la primera parte antes de los números de clics y porcentajes
                    # Ejemplo: "http://example.com 3 (27,3% abridores)" -> "http://example.com"
                    
                    # Usar regex para extraer la URL del principio del texto
                    url_match = re.match(r'(https?://[^\s]+)', item_text)
                    if url_match:
                        url = url_match.group(1)
                        urls.append(url)
                        logger.debug(f"🔗 URL extraída: {url}")
                    else:
                        logger.debug(f"🔍 No se encontró URL en el texto: '{item_text}'")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error procesando elemento {i+1}: {e}")
                    continue
            
            # Eliminar duplicados manteniendo el orden
            unique_urls = []
            for url in urls:
                if url and url not in unique_urls:
                    unique_urls.append(url)
            
            logger.info(f"✅ Se encontraron {len(unique_urls)} URLs únicas: {unique_urls}")
            return unique_urls
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo URLs de la página: {e}")
            import traceback
            logger.error(f" traceback: {traceback.format_exc()}")
            return []


# Función auxiliar para integración con el sistema existente
def get_campaign_urls_with_fallback(page: Page, campaign_id: int) -> str:
    """
    Obtener URLs de campaña como string separado por comas, con manejo de errores
    
    Args:
        page: Página Playwright autenticada
        campaign_id: ID de la campaña
        
    Returns:
        String con URLs separados por comas, o string vacío si falla
    """
    logger.debug(f"🚀 Iniciando obtención de URLs para campaña {campaign_id}")
    
    try:
        config = ScrapingConfig(timeout=30000)
        scraper = CampaignURLScraper(page, config)
        urls = scraper.get_campaign_urls(campaign_id)
        
        # Devolver URLs como string separado por comas
        urls_str = ", ".join(urls) if urls else ""
        logger.info(f"✅ URLs obtenidas para campaña {campaign_id}: {len(urls)} URLs -> '{urls_str}'")
        return urls_str
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo URLs para campaña {campaign_id}: {e}")
        import traceback
        logger.error(f"  traceback: {traceback.format_exc()}")
        return ""