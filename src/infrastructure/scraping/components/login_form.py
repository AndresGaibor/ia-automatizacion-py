from playwright.sync_api import Page
from src.shared.logging.logger import get_logger

logger = get_logger()


class LoginFormComponent:
    def __init__(self, page: Page):
        self._page = page

    def is_visible(self) -> bool:
        try:
            return self._page.get_by_role("textbox", name="Correo electrónico").is_visible()
        except Exception:
            return False

    def fill_credentials(self, username: str, password: str) -> None:
        logger.info("Rellenando formulario de login")
        self._page.get_by_role("textbox", name="Correo electrónico").fill(username)
        self._page.get_by_role("textbox", name="Contraseña").fill(password)
        # Checkbox "Mantener sesión iniciada" — el <input> suele estar oculto,
        # así que clickeamos el <label> asociado (fallback a CSS si get_by_role no funciona)
        keepme = self._page.locator('label[for="keepme-logged"]')
        if keepme.is_visible():
            keepme.click()

    def click_entrar_link(self) -> None:
        logger.info("Clic en botón de entrada")
        btn_entrar = self._page.get_by_role("link", name="Entra")
        btn_entrar.click()
        self._page.wait_for_load_state("networkidle")

    def submit(self) -> None:
        logger.info("Enviando formulario de login")
        with self._page.expect_navigation(wait_until="domcontentloaded"):
            self._page.get_by_role("button", name="Entrar").click()
