"""
Clases base para scraping de Acumbamail
"""
from typing import Optional, Any, List, Callable
from playwright.sync_api import Page
from pathlib import Path
import time
from dataclasses import dataclass

from ..logger import logger


@dataclass
class ScrapingConfig:
    """Configuración para scraping"""
    base_url: str = "https://acumbamail.com"
    timeout: int = 30000
    wait_between_requests: float = 1.0
    max_retries: int = 3
    screenshots_on_error: bool = True
    screenshots_dir: str = "data/screenshots"


class BaseScraper:
    """Clase base para todos los scrapers"""
    
    def __init__(self, page: Page, config: Optional[ScrapingConfig] = None):
        self.page = page
        self.config = config or ScrapingConfig()
        
        # Crear directorio de screenshots si no existe
        if self.config.screenshots_on_error:
            Path(self.config.screenshots_dir).mkdir(parents=True, exist_ok=True)
    
    def wait_and_retry(self, action_func: Callable, max_retries: int = None) -> Any:
        """
        Ejecuta una acción con reintentos automáticos
        
        Args:
            action_func: Función a ejecutar
            max_retries: Máximo número de reintentos (None usa config por defecto)
            
        Returns:
            Resultado de la función
            
        Raises:
            Exception: Si falla después de todos los reintentos
        """
        retries = max_retries or self.config.max_retries
        
        for attempt in range(retries):
            try:
                return action_func()
            except Exception as e:
                if attempt == retries - 1:
                    # Último intento - tomar screenshot y fallar
                    if self.config.screenshots_on_error:
                        self._take_error_screenshot(f"final_attempt_{int(time.time())}")
                    logger.error(f"Falló después de {retries} intentos: {e}")
                    raise
                
                wait_time = (attempt + 1) * self.config.wait_between_requests
                logger.warning(f"Intento {attempt + 1} falló, esperando {wait_time}s: {e}")
                time.sleep(wait_time)
    
    def navigate_to_campaign(self, campaign_id: int) -> None:
        """
        Navegar a una campaña específica
        
        Args:
            campaign_id: ID de la campaña
        """
        url = f"{self.config.base_url}/panel/campaign/{campaign_id}"
        logger.info(f"Navegando a campaña {campaign_id}: {url}")
        
        def _navigate():
            self.page.goto(url, wait_until="networkidle", timeout=self.config.timeout)
            # Verificar que estamos en la página correcta
            self._verify_campaign_page(campaign_id)
            return True
            
        self.wait_and_retry(_navigate)
        time.sleep(self.config.wait_between_requests)
    
    def wait_for_element(self, selector: str, timeout: int = None) -> None:
        """
        Esperar a que aparezca un elemento
        
        Args:
            selector: Selector CSS del elemento
            timeout: Timeout en milisegundos (None usa config por defecto)
        """
        timeout = timeout or self.config.timeout
        try:
            self.page.wait_for_selector(selector, timeout=timeout)
        except Exception as e:
            if self.config.screenshots_on_error:
                self._take_error_screenshot(f"wait_element_{selector.replace('[', '').replace(']', '')}")
            raise Exception(f"No se encontró elemento '{selector}' después de {timeout}ms: {e}")
    
    def click_with_retry(self, selector: str) -> None:
        """
        Hacer clic en un elemento con reintentos
        
        Args:
            selector: Selector CSS del elemento
        """
        def _click():
            self.wait_for_element(selector)
            self.page.click(selector)
            return True
        
        self.wait_and_retry(_click)
    
    def get_text_content(self, selector: str, default: str = "") -> str:
        """
        Obtener contenido de texto de un elemento
        
        Args:
            selector: Selector CSS del elemento
            default: Valor por defecto si no se encuentra
            
        Returns:
            Texto del elemento o valor por defecto
        """
        try:
            element = self.page.query_selector(selector)
            if element:
                return element.text_content().strip()
        except Exception as e:
            logger.warning(f"No se pudo obtener texto de '{selector}': {e}")
        
        return default
    
    def get_all_text_contents(self, selector: str) -> List[str]:
        """
        Obtener contenido de texto de múltiples elementos
        
        Args:
            selector: Selector CSS de los elementos
            
        Returns:
            Lista de textos de los elementos
        """
        try:
            elements = self.page.query_selector_all(selector)
            return [elem.text_content().strip() for elem in elements if elem.text_content()]
        except Exception as e:
            logger.warning(f"No se pudieron obtener textos de '{selector}': {e}")
            return []
    
    def scroll_to_bottom(self) -> None:
        """Hacer scroll hasta abajo de la página"""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(self.config.wait_between_requests)
    
    def handle_pagination(self, item_selector: str, next_button_selector: str, 
                         extract_func: Callable[[List], List]) -> List[Any]:
        """
        Manejar paginación automáticamente
        
        Args:
            item_selector: Selector de los elementos en cada página
            next_button_selector: Selector del botón "siguiente"
            extract_func: Función para extraer datos de los elementos
            
        Returns:
            Lista combinada de todos los elementos de todas las páginas
        """
        all_items = []
        page_num = 1
        
        while True:
            logger.debug(f"Procesando página {page_num}")
            
            # Esperar a que se carguen los elementos
            self.wait_for_element(item_selector)
            
            # Obtener elementos de la página actual
            elements = self.page.query_selector_all(item_selector)
            page_items = extract_func(elements)
            
            logger.debug(f"Página {page_num}: {len(page_items)} elementos")
            all_items.extend(page_items)
            
            # Verificar si hay página siguiente
            next_button = self.page.query_selector(next_button_selector)
            if not next_button or not next_button.is_visible():
                logger.debug("No hay más páginas")
                break
            
            # Hacer clic en siguiente página
            try:
                next_button.click()
                self.page.wait_for_load_state("networkidle")
                time.sleep(self.config.wait_between_requests)
                page_num += 1
            except Exception as e:
                logger.warning(f"Error al ir a página siguiente: {e}")
                break
        
        logger.info(f"Total elementos obtenidos: {len(all_items)} en {page_num} páginas")
        return all_items
    
    def _verify_campaign_page(self, campaign_id: int) -> None:
        """
        Verificar que estamos en la página correcta de la campaña
        
        Args:
            campaign_id: ID esperado de la campaña
        """
        # TODO: Implementar verificación específica según la URL/contenido real
        current_url = self.page.url
        if f"campaign/{campaign_id}" not in current_url:
            raise Exception(f"No se pudo navegar a campaña {campaign_id}. URL actual: {current_url}")
    
    def _take_error_screenshot(self, filename: str) -> None:
        """
        Tomar screenshot cuando ocurre un error
        
        Args:
            filename: Nombre base del archivo (sin extensión)
        """
        try:
            screenshot_path = Path(self.config.screenshots_dir) / f"{filename}.png"
            self.page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot guardado: {screenshot_path}")
        except Exception as e:
            logger.error(f"No se pudo tomar screenshot: {e}")