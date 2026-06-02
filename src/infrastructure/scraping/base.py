"""
Base classes for scraping infrastructure.

Solo infraestructura: retry, screenshots, config.
NO navegación de negocio ni helpers de UI.
"""
from typing import Optional, Any, Callable
from playwright.sync_api import Page
from pathlib import Path
import time
from dataclasses import dataclass

from src.shared.logging.logger import get_logger

logger = get_logger()


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
    """Clase base para scrapers - solo infraestructura."""

    def __init__(self, page: Page, config: Optional[ScrapingConfig] = None):
        self.page = page
        self.config = config or ScrapingConfig()

        if self.config.screenshots_on_error:
            Path(self.config.screenshots_dir).mkdir(parents=True, exist_ok=True)

    def wait_and_retry(self, action_func: Callable, max_retries: int = None) -> Any:
        """
        Ejecuta una acción con reintentos automáticos.

        Args:
            action_func: Función a ejecutar
            max_retries: Máximo número de reintentos

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
                    if self.config.screenshots_on_error:
                        self._take_error_screenshot(f"final_attempt_{int(time.time())}")
                    logger.error(f"Falló después de {retries} intentos: {e}")
                    raise

                wait_time = (attempt + 1) * self.config.wait_between_requests
                logger.warning(f"Intento {attempt + 1} falló, esperando {wait_time}s: {e}")
                time.sleep(wait_time)

    def _take_error_screenshot(self, filename: str) -> None:
        """Tomar screenshot cuando ocurre un error."""
        try:
            screenshot_path = Path(self.config.screenshots_dir) / f"{filename}.png"
            self.page.screenshot(path=str(screenshot_path))
            logger.info(f"Screenshot guardado: {screenshot_path}")
        except Exception as e:
            logger.error(f"No se pudo tomar screenshot: {e}")