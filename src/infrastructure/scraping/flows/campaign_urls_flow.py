"""
CampaignUrlsFlow - flujo de extracción de URLs rastreadas por campaña.
"""
import time as time_module

from playwright.sync_api import Page
from src.infrastructure.scraping.pages.campaign_urls_page import PaginaUrlsCampania
from src.infrastructure.scraping.models.campanias import ScrapedCampaignUrl
from src.shared.logging.logger import get_logger

logger = get_logger()


class FlujoUrlsCampania:
    def __init__(self, page: Page):
        self._page = page
        self._urls_page = PaginaUrlsCampania(page)

    def scrape(self, campaign_id: int) -> list[ScrapedCampaignUrl]:
        """Extrae todas las URLs rastreadas de una campaña."""
        logger.info(f"🔗 Iniciando scraping de URLs para campaña {campaign_id}")
        start_time = time_module.time()

        self._urls_page.navigate_to(campaign_id)

        if self._urls_page.is_on_login_page():
            logger.error(f"❌ Redirigido a login al acceder a URLs de campaña {campaign_id}")
            logger.warning("⚠️ Sesión expirada - no se pueden extraer URLs")
            return []

        if not self._urls_page.wait_for_url_list():
            logger.warning(f"⚠️ No se encontraron URLs en la campaña {campaign_id}")
            return []

        urls = self._extract_all_urls(campaign_id)
        duration = time_module.time() - start_time
        logger.info(f"✅ URLs scraping completado: {len(urls)} URLs en {duration:.1f}s")
        return urls

    def _extract_all_urls(self, campaign_id: int) -> list[ScrapedCampaignUrl]:
        urls = []
        count = self._urls_page.get_item_count()
        logger.info(f"📊 Se encontraron {count} items en la lista")

        for i in range(count):
            item = self._urls_page.get_item(i)
            try:
                url_data = self._extract_single_url(item, campaign_id)
                if url_data:
                    urls.append(url_data)
            except Exception as e:
                logger.warning(f"⚠️ Error procesando item de URL: {e}")
                continue

        return urls

    def _extract_single_url(self, item, campaign_id: int) -> ScrapedCampaignUrl | None:
        item_text = item.text_content()
        if not item_text:
            return None

        if self._urls_page.is_header_row(item_text):
            return None

        url = self._extract_url(item, item_text)
        if not url:
            return None

        clicks, percentage = self._urls_page.extract_clicks_and_percentage(item_text)

        return ScrapedCampaignUrl(
            url=url,
            clicks=clicks,
            click_percentage=percentage,
            campaign_id=campaign_id
        )

    def _extract_url(self, item, item_text: str) -> str | None:
        links_locator = item.locator('a')
        links_count = links_locator.count()

        url = self._try_direct_link(links_locator, links_count)
        if url:
            return url

        url = self._try_details_link(links_locator, links_count, item_text)
        if url:
            return url

        return self._try_text_extraction(item_text)

    def _try_direct_link(self, links_locator, links_count: int) -> str | None:
        for i in range(links_count):
            link = links_locator.nth(i)
            href = link.get_attribute('href')
            if href and href.startswith('http'):
                return href
        return None

    def _try_details_link(self, links_locator, links_count: int, item_text: str) -> str | None:
        details_link = None
        for i in range(links_count):
            link = links_locator.nth(i)
            href = link.get_attribute('href')
            link_text = link.text_content().strip()
            if href and ('/click/' in href and '/details/' in href) or link_text == 'Detalles':
                details_link = href
                break

        if not details_link:
            return None

        details_url = self._build_details_url(details_link)
        return self._urls_page.navigate_to_details_and_back(details_url)

    def _build_details_url(self, details_link: str) -> str:
        if details_link.startswith('/'):
            return f"https://acumbamail.com{details_link}"
        return details_link

    def _try_text_extraction(self, item_text: str) -> str | None:
        import re
        url_match = re.search(r'(https?://\S+)', item_text)
        if url_match:
            logger.debug(f"   ⚠️ Usando URL del texto (puede estar truncada): {url_match.group(1)}")
            return url_match.group(1)
        return None