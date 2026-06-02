"""
FieldsPage — Page Object para la página de campos de una lista en Acumbamail.

Navega a /app/list/{list_id}/edit/fields/ y encapsula:
- navegación a la página de campos
- extracción de campos dinámicos usando JavaScript
- fallback a página de suscriptores
"""

from playwright.sync_api import Page
from src.infrastructure.scraping.pages.base_page import BasePage
from src.infrastructure.scraping.utils.selectors import FieldSelectors
from src.shared.logging.logger import get_logger

logger = get_logger()


class FieldsPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page, url="")
        self._selectors = FieldSelectors()

    def navigate_to(self, list_id: int) -> bool:
        url = self._selectors.fields_url_template.format(list_id=list_id)
        try:
            self._page.goto(url, timeout=30000)
            self._page.wait_for_load_state("networkidle", timeout=30000)
            logger.debug(f"✅ Navegado a página de campos: {url}")
            return True
        except Exception as e:
            logger.error(f"Error navegando a página de campos: {e}")
            return False

    def extract_fields_from_page(self) -> list:
        try:
            resultado = self._page.evaluate("""
                () => {
                    const campos = [];
                    const filasCampos = document.querySelectorAll('li');

                    for (let fila of filasCampos) {
                        const primerGeneric = fila.querySelector('generic:first-child');
                        if (primerGeneric && primerGeneric.textContent) {
                            const nombreCampo = primerGeneric.textContent.trim();
                            if (nombreCampo &&
                                !nombreCampo.includes('Campo de etiqueta') &&
                                !nombreCampo.includes('Estado') &&
                                !nombreCampo.includes('Tipo') &&
                                !nombreCampo.includes('Comando') &&
                                !nombreCampo.includes('Acciones') &&
                                nombreCampo.length > 1 &&
                                nombreCampo.length < 100) {
                                campos.push(nombreCampo);
                            }
                        }
                    }

                    return {
                        campos: campos,
                        totalEncontrados: campos.length
                    };
                }
            """)
            return resultado.get("campos", [])
        except Exception as e:
            logger.error(f"Error extrayendo campos: {e}")
            return []

    def navigate_to_subscribers_fallback(self, list_id: int) -> bool:
        url = self._selectors.subscribers_url_template.format(list_id=list_id)
        try:
            self._page.goto(url, timeout=30000)
            self._page.wait_for_load_state("networkidle", timeout=30000)
            logger.debug(f"✅ Navegado a página de suscriptores (fallback): {url}")
            return True
        except Exception as e:
            logger.error(f"Error navegando a suscriptores fallback: {e}")
            return False

    def extract_fields_from_subscribers(self) -> list:
        try:
            resultado = self._page.evaluate("""
                () => {
                    const listas = document.querySelectorAll('ul');

                    let listaTabla = null;
                    for (let ul of listas) {
                        const items = ul.querySelectorAll('li');
                        if (items.length > 5) {
                            const enlaces = ul.querySelectorAll('a[href*="subscriber/detail"]');
                            if (enlaces.length > 0) {
                                listaTabla = ul;
                                break;
                            }
                        }
                    }

                    if (!listaTabla) return { error: "No se encontró la tabla de suscriptores" };

                    const filas = listaTabla.querySelectorAll('li');
                    const encabezados = [];
                    const encabezadosVistos = new Set();

                    if (filas.length > 0) {
                        const filaHeader = filas[0];
                        const elementos = filaHeader.querySelectorAll('*');
                        for (let elem of elementos) {
                            const text = elem.textContent.trim();
                            if (text && text.length > 2 && text.length < 50 &&
                                !text.includes('checkbox') && !text.includes('button') &&
                                !text.match(/^\\d+$/) && !encabezadosVistos.has(text)) {
                                encabezados.push(text);
                                encabezadosVistos.add(text);
                            }
                        }
                    }

                    return {
                        encabezados: encabezados,
                        totalFilas: filas.length
                    };
                }
            """)
            return resultado.get("encabezados", [])
        except Exception as e:
            logger.error(f"Error extrayendo campos de suscriptores: {e}")
            return []