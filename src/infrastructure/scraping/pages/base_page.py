from playwright.sync_api import Page


class PaginaBase:
    def __init__(self, page: Page, url: str = ""):
        self._page = page
        self._url = url

    @property
    def page(self) -> Page:
        return self._page

    @property
    def url(self) -> str:
        return self._url

    def navigate(self) -> None:
        if self._url:
            self._page.goto(self._url, wait_until="domcontentloaded")

    def wait_for_load(self, timeout: int = 45000, use_networkidle: bool = False) -> None:
        self._page.wait_for_load_state("domcontentloaded", timeout=timeout)
        if use_networkidle:
            self._page.wait_for_load_state("networkidle", timeout=timeout)

    def wait_session_stable(self, networkidle_timeout: int = 30000, extra_delay: float = 2.0) -> None:
        self._page.wait_for_load_state("networkidle", timeout=networkidle_timeout)
        self._page.wait_for_timeout(int(extra_delay * 1000))
