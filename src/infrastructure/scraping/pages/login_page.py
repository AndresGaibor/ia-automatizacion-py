from playwright.sync_api import Page
from src.infrastructure.scraping.pages.base_page import PaginaBase
from src.infrastructure.scraping.components.cookie_banner import ComponenteBannerCookies
from src.infrastructure.scraping.components.login_form import ComponenteFormularioLogin
from src.infrastructure.scraping.components.session_guard import ComponenteGuardiaSesion


class PaginaLogin(PaginaBase):
    def __init__(self, page: Page, base_url: str):
        super().__init__(page, base_url)
        self.cookie_banner = ComponenteBannerCookies(page)
        self.login_form = ComponenteFormularioLogin(page)
        self.session_guard = ComponenteGuardiaSesion(page)

    def navigate_to(self, url: str) -> None:
        if url:
            self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)

    def wait_stabilize(self) -> None:
        self._page.wait_for_load_state("networkidle", timeout=30_000)

    def is_logged_in(self) -> bool:
        return self.session_guard.is_authenticated()

    def handle_cookies(self, agresivo: bool = True) -> None:
        self.cookie_banner.accept(agresivo=agresivo)

    def do_login(self, username: str, password: str) -> None:
        self.login_form.click_entrar_link()
        self.login_form.fill_credentials(username, password)
        self.login_form.submit()


LoginPage = PaginaLogin