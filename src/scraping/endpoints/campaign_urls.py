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
            
            # Esperar a que se carguen las URLs
            self.wait_for_element("ul", timeout=30000)
            
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
            # Los URLs están dentro de list items en una lista
            # En el snapshot vimos que los elementos son como:
            # listitem [ref=s1e123]: http://intranet.madrid.org/... 3 (27,3% abridores)
            # listitem [ref=s1e134]: https://faro.comunidad.madrid/ 0 (0,0% abridores)
            
            # Usando locators modernos de Playwright en lugar de selectores CSS complejos
            list_items = self.page.get_by_role("list").get_by_role("listitem").all()
            
            urls = []
            for item in list_items:
                item_text = item.text_content().strip()
                
                # Extraer la URL del texto del elemento
                # La URL normalmente es la primera parte antes de los números de clics y porcentajes
                # Ejemplo: "http://example.com 3 (27,3% abridores)" -> "http://example.com"
                
                # Usar regex para extraer la URL del principio del texto
                url_match = re.match(r'(https?://[^\s]+)', item_text)
                if url_match:
                    url = url_match.group(1)
                    urls.append(url)
            
            # Eliminar duplicados manteniendo el orden
            unique_urls = []
            for url in urls:
                if url not in unique_urls:
                    unique_urls.append(url)
            
            logger.debug(f"URLs extraídas: {unique_urls}")
            return unique_urls
            
        except Exception as e:
            logger.warning(f"Error extrayendo URLs de la página: {e}")
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
    try:
        config = ScrapingConfig(timeout=30000)
        scraper = CampaignURLScraper(page, config)
        urls = scraper.get_campaign_urls(campaign_id)
        
        # Devolver URLs como string separado por comas
        urls_str = ", ".join(urls) if urls else ""
        logger.info(f"URLs obtenidas para campaña {campaign_id}: {len(urls)} URLs")
        return urls_str
        
    except Exception as e:
        logger.error(f"Error obteniendo URLs para campaña {campaign_id}: {e}")
        return ""