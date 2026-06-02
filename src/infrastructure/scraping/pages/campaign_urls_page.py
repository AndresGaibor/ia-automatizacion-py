"""
CampaignUrlsPage - Page Object para página de URLs rastreadas por campaña.

Maneja navegación, extracción de lista de URLs y datos de clics.
"""
from playwright.sync_api import Page, Locator
import re

from src.infrastructure.scraping.pages.base_page import PaginaBase
from src.infrastructure.scraping.components.campaign_row import FilaCampania
from src.shared.logging.logger import get_logger

logger = get_logger()

SKIP_DOMAINS = [
    'acumbamail.com', 'clickacm.com', 'w3.org', 'schema.org',
    'google.com/recaptcha', 'gstatic.com'
]


class PaginaUrlsCampania(PaginaBase):
    BASE_URL = "https://acumbamail.com"

    def navigate_to(self, campaign_id: int) -> None:
        url = f"{self.BASE_URL}/report/campaign/{campaign_id}/url/"
        self._page.goto(url, wait_until="networkidle", timeout=60000)
        self._page.wait_for_load_state("networkidle", timeout=30000)
        self._page.wait_for_timeout(1000)

    def is_on_login_page(self) -> bool:
        try:
            from src.shared.utils.legacy_utils import is_on_login_page
            return is_on_login_page(self._page)
        except ImportError:
            return False

    def wait_for_url_list(self) -> bool:
        try:
            self._page.wait_for_selector("ul li, ol li", timeout=10000)
            return True
        except Exception:
            return False

    def get_item_count(self) -> int:
        return self._page.locator("ul li, ol li").count()

    def get_item(self, index: int) -> Locator:
        return self._page.locator("ul li, ol li").nth(index)

    def navigate_to_details_and_back(self, details_url: str) -> str | None:
        current_url = self._page.url
        self._page.goto(details_url, wait_until="domcontentloaded", timeout=15000)
        self._page.wait_for_timeout(500)

        url = self._extract_tracked_url_from_page()

        self._page.goto(current_url, wait_until="networkidle", timeout=15000)
        self._page.wait_for_timeout(1000)

        return url

    def _extract_tracked_url_from_page(self) -> str | None:
        page_content = self._page.content()

        for pattern in [r'(https?://[^"\s<>]+)']:
            urls_found = re.findall(pattern, page_content)
            for found_url in urls_found:
                if self._is_valid_tracked_url(found_url):
                    return found_url

        return None

    def _is_valid_tracked_url(self, found_url: str) -> bool:
        return not any(domain in found_url.lower() for domain in SKIP_DOMAINS)

    def extract_clicks_and_percentage(self, item_text: str) -> tuple[int, float]:
        clicks_match = re.search(r'(\d+)\s*\((\d+[,.]?\d*)\s*%\s*abridores\)', item_text)

        if clicks_match:
            clicks = int(clicks_match.group(1))
            percentage = float(clicks_match.group(2).replace(',', '.'))
            return clicks, percentage

        clicks_simple = re.search(r'(\d+)\s+\(', item_text)
        if clicks_simple:
            return int(clicks_simple.group(1)), 0.0

        return 0, 0.0

    def is_header_row(self, item_text: str) -> bool:
        return "Url Han hecho clic Acciones" in item_text or "Han hecho clic" in item_text