"""Browser management and automation utilities."""
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
from playwright.sync_api import TimeoutError as PWTimeoutError

from ...core.errors import BrowserAutomationError
from ...core.config.config_manager import ConfigManager


class BrowserManager:
    """Manages browser instances and configuration for automation."""

    REAL_UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._setup_playwright_path()

    def _setup_playwright_path(self):
        """Configure Playwright browsers path for portable execution."""
        project_root = self._get_project_root()
        playwright_path = os.path.join(project_root, "ms-playwright")
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", playwright_path)
        os.makedirs(playwright_path, exist_ok=True)

    def _get_project_root(self) -> str:
        """Get project root directory."""
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return str(Path(__file__).parent.parent.parent.parent)

    def get_timeouts(self) -> Dict[str, int]:
        """Get timeout configuration."""
        try:
            config = self.config_manager.get_config()
            timeouts = config.get('timeouts', {})
            return {
                'navigation': timeouts.get('navigation', 60) * 1000,  # Convert to milliseconds
                'element': timeouts.get('element', 15) * 1000,
                'upload': timeouts.get('upload', 120) * 1000,
                'default': timeouts.get('default', 30) * 1000
            }
        except Exception:
            # Default timeouts if config is not available
            return {
                'navigation': 60000,
                'element': 15000,
                'upload': 120000,
                'default': 30000
            }

    def start(self) -> 'BrowserManager':
        """Start the browser with configured settings."""
        try:
            self.playwright = sync_playwright().start()
            config = self.config_manager.get_config()
            headless = config.get('headless', False)

            self.browser = self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )

            return self

        except Exception as e:
            raise BrowserAutomationError(
                "Failed to start browser",
                context={"error": str(e)}
            ) from e

    def create_context(
        self,
        storage_state_path: Optional[str] = None,
        **kwargs
    ) -> BrowserContext:
        """Create a new browser context with session persistence."""
        if not self.browser:
            raise BrowserAutomationError("Browser not started. Call start() first.")

        context_args = {
            'user_agent': self.REAL_UA,
            'viewport': {'width': 1280, 'height': 720},
            'ignore_https_errors': True,
            **kwargs
        }

        if storage_state_path and os.path.exists(storage_state_path):
            context_args['storage_state'] = storage_state_path

        try:
            self.context = self.browser.new_context(**context_args)
            timeouts = self.get_timeouts()
            self.context.set_default_timeout(timeouts['default'])
            self.context.set_default_navigation_timeout(timeouts['navigation'])

            return self.context

        except Exception as e:
            raise BrowserAutomationError(
                "Failed to create browser context",
                context={"error": str(e)}
            ) from e

    def new_page(self) -> Page:
        """Create a new page in the current context."""
        if not self.context:
            raise BrowserAutomationError("Browser context not created. Call create_context() first.")

        try:
            page = self.context.new_page()
            return page
        except Exception as e:
            raise BrowserAutomationError(
                "Failed to create new page",
                context={"error": str(e)}
            ) from e

    def save_session(self, storage_path: str):
        """Save current session state."""
        if not self.context:
            raise BrowserAutomationError("No context available to save session.")

        try:
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            self.context.storage_state(path=storage_path)
        except Exception as e:
            raise BrowserAutomationError(
                "Failed to save session state",
                context={"storage_path": storage_path, "error": str(e)}
            ) from e

    def close(self):
        """Close browser and cleanup resources."""
        try:
            if self.context:
                self.context.close()
                self.context = None

            if self.browser:
                self.browser.close()
                self.browser = None

            if self.playwright:
                self.playwright.stop()
                self.playwright = None

        except Exception:
            # Log but don't raise on cleanup errors
            pass

    def __enter__(self) -> 'BrowserManager':
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class PageWrapper:
    """Wrapper for Page with enhanced error handling and logging."""

    def __init__(self, page: Page, browser_manager: BrowserManager):
        self.page = page
        self.browser_manager = browser_manager

    def navigate(self, url: str, **kwargs) -> None:
        """Navigate to URL with enhanced error handling."""
        try:
            timeouts = self.browser_manager.get_timeouts()
            timeout = kwargs.pop('timeout', timeouts['navigation'])
            self.page.goto(url, timeout=timeout, **kwargs)
        except PWTimeoutError as e:
            raise BrowserAutomationError(
                f"Navigation timeout to {url}",
                page_url=url,
                context={"timeout": timeout}
            ) from e
        except Exception as e:
            raise BrowserAutomationError(
                f"Navigation failed to {url}",
                page_url=url,
                context={"error": str(e)}
            ) from e

    def wait_for_selector(self, selector: str, **kwargs) -> None:
        """Wait for selector with enhanced error handling."""
        try:
            timeouts = self.browser_manager.get_timeouts()
            timeout = kwargs.pop('timeout', timeouts['element'])
            self.page.wait_for_selector(selector, timeout=timeout, **kwargs)
        except PWTimeoutError as e:
            raise BrowserAutomationError(
                f"Element not found: {selector}",
                page_url=self.page.url,
                selector=selector,
                context={"timeout": timeout}
            ) from e

    def click_element(self, selector: str, **kwargs) -> None:
        """Click element with enhanced error handling."""
        try:
            timeouts = self.browser_manager.get_timeouts()
            timeout = kwargs.pop('timeout', timeouts['element'])
            self.page.click(selector, timeout=timeout, **kwargs)
        except PWTimeoutError as e:
            raise BrowserAutomationError(
                f"Click timeout on element: {selector}",
                page_url=self.page.url,
                selector=selector
            ) from e
        except Exception as e:
            raise BrowserAutomationError(
                f"Click failed on element: {selector}",
                page_url=self.page.url,
                selector=selector,
                context={"error": str(e)}
            ) from e

    def fill_element(self, selector: str, value: str, **kwargs) -> None:
        """Fill element with enhanced error handling."""
        try:
            timeouts = self.browser_manager.get_timeouts()
            timeout = kwargs.pop('timeout', timeouts['element'])
            self.page.fill(selector, value, timeout=timeout, **kwargs)
        except Exception as e:
            raise BrowserAutomationError(
                f"Fill failed on element: {selector}",
                page_url=self.page.url,
                selector=selector,
                context={"value": value, "error": str(e)}
            ) from e