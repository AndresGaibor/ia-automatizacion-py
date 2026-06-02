"""
SegmentPage — Page Object para la página de segmentos de Acumbamail.

Navega a /app/list/{list_id}/segments/ y encapsula:
- navegación a la página de segmentos
- creación de nuevos segmentos
- llenado del formulario de segmento
- guardado del segmento
"""

from playwright.sync_api import Page, TimeoutError as PWTimeoutError
from src.infrastructure.scraping.pages.base_page import BasePage
from src.infrastructure.scraping.utils.selectors import SegmentSelectors
from src.shared.logging.logger import get_logger

logger = get_logger()


class SegmentPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page, url="")
        self._selectors = SegmentSelectors()

    def navigate_to(self, list_id: int) -> bool:
        url = self._selectors.segments_url_template.format(list_id=list_id)
        try:
            self._page.goto(url, wait_until="networkidle", timeout=60000)
            self._page.wait_for_load_state("networkidle", timeout=30000)
            self._page.wait_for_timeout(1500)
            logger.debug(f"✅ Navegado a página de segmentos: {url}")
            return True
        except Exception as e:
            logger.error(f"Error navegando a segmentos: {e}")
            return False

    def wait_page_ready(self, networkidle_timeout: int = 30000, extra_delay: float = 1.5) -> None:
        self._page.wait_for_load_state("networkidle", timeout=networkidle_timeout)
        self._page.wait_for_timeout(int(extra_delay * 1000))

    def _find_nuevo_segmento_button(self):
        button = None

        strategies = [
            ("empty_state", lambda: self._page.locator(self._selectors.empty_state_add_button).get_by_text(self._selectors.new_segment_button_text)),
            ("normal", lambda: self._page.locator(self._selectors.new_segment_button).get_by_text(self._selectors.new_segment_button_text)),
            ("by_role", lambda: self._page.get_by_role("button", name=self._selectors.new_segment_button_text)),
        ]

        for name, locator_func in strategies:
            try:
                btn = locator_func()
                if btn.is_visible(timeout=5000):
                    button = btn
                    logger.debug(f"✅ Botón 'Nuevo segmento' encontrado con estrategia: {name}")
                    break
            except PWTimeoutError:
                logger.debug(f"⏱️ Timeout en estrategia: {name}")
            except Exception as e:
                logger.debug(f"⚠️ Error en estrategia {name}: {e}")

        return button

    def click_nuevo_segmento(self) -> bool:
        try:
            button = self._find_nuevo_segmento_button()
            if not button:
                logger.error("❌ No se encontró botón 'Nuevo segmento'")
                return False
            button.click(timeout=10000)
            logger.debug("✅ Clic en 'Nuevo segmento' realizado")
            return True
        except Exception as e:
            logger.error(f"Error clicking nuevo segmento: {e}")
            return False

    def wait_for_form(self) -> bool:
        try:
            self._page.wait_for_selector(self._selectors.segment_form_field_value, timeout=10000)
            return True
        except Exception as e:
            logger.error(f"Error esperando formulario: {e}")
            return False

    def fill_segment_name(self, segment_name: str) -> bool:
        try:
            try:
                nombre_input = self._page.get_by_role("textbox", name="Nombre del segmento")
                nombre_input.fill(segment_name)
                logger.debug(f"✅ Nombre '{segment_name}' llenado con rol")
            except Exception:
                nombre_input = self._page.locator(self._selectors.segment_name_input)
                nombre_input.fill(segment_name)
                logger.debug(f"✅ Nombre '{segment_name}' llenado con selector")
            return True
        except Exception as e:
            logger.error(f"Error llenando nombre del segmento: {e}")
            return False

    def select_segmentos_field(self) -> bool:
        try:
            campo_select = self._page.locator(self._selectors.segment_form_field_name)
            campo_select.select_option(label=self._selectors.segment_option_segmentos)
            logger.debug("✅ Campo 'Segmentos' seleccionado")
            return True
        except Exception as e:
            logger.error(f"Error seleccionando campo Segmentos: {e}")
            return False

    def select_contiene_condition(self) -> bool:
        try:
            condicion_select = self._page.locator(self._selectors.segment_form_field_type)
            condicion_select.select_option(label=self._selectors.segment_condition_contiene)
            logger.debug("✅ Condición 'contiene' seleccionada")
            return True
        except Exception as e:
            logger.error(f"Error seleccionando condición: {e}")
            return False

    def fill_segment_value(self, segment_name: str) -> bool:
        try:
            valor_input = self._page.locator(self._selectors.segment_form_field_value)
            valor_input.fill(segment_name)
            logger.debug(f"✅ Valor '{segment_name}' configurado")
            return True
        except Exception as e:
            logger.error(f"Error llenando valor del segmento: {e}")
            return False

    def configure_segment_conditions(self, segment_name: str) -> bool:
        try:
            if not self.select_segmentos_field():
                return False
            if not self.select_contiene_condition():
                return False
            if not self.fill_segment_value(segment_name):
                return False
            return True
        except Exception as e:
            logger.error(f"Error configurando condiciones: {e}")
            return False

    def _find_save_button(self):
        button = None

        strategies = [
            ("segment_button_text", lambda: self._page.locator(self._selectors.save_segment_button)),
            ("save_by_role", lambda: self._page.get_by_role("button", name=self._selectors.save_button_text)),
            ("create_by_role", lambda: self._page.get_by_role("button", name=self._selectors.create_button_text)),
            ("submit_first", lambda: self._page.locator(self._selectors.submit_button).first),
        ]

        for name, locator_func in strategies:
            try:
                btn = locator_func()
                if btn.is_visible(timeout=3000):
                    button = btn
                    logger.debug(f"✅ Botón guardar encontrado con estrategia: {name}")
                    break
            except Exception:
                pass

        return button

    def click_guardar(self) -> bool:
        try:
            button = self._find_save_button()
            if not button:
                logger.error("❌ No se encontró botón de guardar")
                return False
            button.click(timeout=10000)
            logger.debug("✅ Clic en guardar realizado")
            return True
        except Exception as e:
            logger.error(f"Error clicking guardar: {e}")
            return False

    def wait_for_saved(self) -> bool:
        try:
            self._page.wait_for_load_state("networkidle", timeout=15000)
            self._page.wait_for_timeout(5000)
            return True
        except Exception as e:
            logger.error(f"Error esperando confirmación: {e}")
            return False

    def click_segmentos_field(self) -> bool:
        try:
            self._page.get_by_text("Segmentos").click(timeout=5000)
            logger.debug("✅ Click en 'Segmentos' realizado")
            return True
        except Exception as e:
            logger.error(f"Error clicking campo Segmentos: {e}")
            return False

    def click_contiene_condition(self) -> bool:
        try:
            self._page.get_by_text("contiene").click(timeout=5000)
            logger.debug("✅ Click en 'contiene' realizado")
            return True
        except Exception as e:
            logger.error(f"Error clicking condición contiene: {e}")
            return False

    def fill_segment_value_input(self, segment_name: str) -> bool:
        try:
            self._page.locator("input[type='text']").last.fill(segment_name)
            logger.debug(f"✅ Valor '{segment_name}' llenado en input text")
            return True
        except Exception as e:
            logger.error(f"Error llenando valor en input text: {e}")
            return False

    def esperar_entre_segmentos(self, segundos: int = 2) -> None:
        self._page.wait_for_timeout(segundos * 1000)