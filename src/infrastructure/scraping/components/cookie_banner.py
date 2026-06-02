from playwright.sync_api import Page, TimeoutError as PWTimeoutError
from src.shared.logging.logger import get_logger

logger = get_logger()


class ComponenteBannerCookies:
    POPUP_INDICATORS = [
        "div[data-testid='cookie-banner']",
        "div[id*='cookie']",
        "div[class*='cookie']",
        "div[id*='consent']",
        "div[class*='consent']",
        "#usercentrics-root",
        "[data-testid='uc-banner']",
    ]

    ACCEPT_STRATEGIES = [
        {"type": "role", "selector": "button", "name": "Aceptar todas"},
        {"type": "role", "selector": "button", "name": "Aceptar"},
        {"type": "role", "selector": "button", "name": "Accept all"},
        {"type": "role", "selector": "button", "name": "Accept"},
        {"type": "css", "selector": "button[data-testid='accept-all']"},
        {"type": "css", "selector": "button[id*='accept']"},
        {"type": "css", "selector": "button[class*='accept']"},
        {"type": "css", "selector": "a[data-cy='accept-cookies']"},
        {
            "type": "xpath",
            "selector": "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceptar todas')]",
        },
        {
            "type": "xpath",
            "selector": "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]",
        },
        {
            "type": "xpath",
            "selector": "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceptar')]",
        },
    ]

    def __init__(self, page: Page):
        self._page = page

    def is_present(self) -> bool:
        for indicator in self.POPUP_INDICATORS:
            try:
                if self._page.locator(indicator).count() > 0:
                    return True
            except Exception:
                pass
        return False

    def accept(self, agresivo: bool = True) -> bool:
        logger.info("Cookies: aceptando popup", agresivo=agresivo)

        if not self.is_present():
            logger.info("No se detectó popup de cookies")
            return True

        max_reintentos = 3 if agresivo else 1
        timeout_base = 10000 if agresivo else 3000

        for intento in range(max_reintentos):
            if self._try_accept_strategies(timeout_base):
                return True

            if agresivo and intento < max_reintentos - 1:
                logger.warning("Cookies: reintentando")
                self._page.wait_for_timeout(3000)
            else:
                logger.error("No se pudo manejar el popup de cookies")
                return False

        return False

    def _try_accept_strategies(self, timeout_base: int) -> bool:
        for i, estrategia in enumerate(self.ACCEPT_STRATEGIES):
            try:
                timeout = timeout_base + (i * 2000)
                elemento = self._resolve(estrategia, timeout)
                elemento.wait_for(state="visible", timeout=timeout)
                elemento.wait_for(state="enabled", timeout=timeout)
                elemento.click(timeout=timeout)
                self._page.wait_for_timeout(2000)

                if not self.is_present():
                    return True
            except PWTimeoutError:
                continue
            except Exception:
                continue
        return False

    def _resolve(self, strategy: dict, timeout: int):
        if strategy["type"] == "role":
            return self._page.get_by_role(strategy["selector"], name=strategy["name"])
        if strategy["type"] == "css":
            return self._page.locator(strategy["selector"])
        return self._page.locator(f"xpath={strategy['selector']}")
