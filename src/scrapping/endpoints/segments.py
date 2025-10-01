"""
Servicio de scraping para la gestión de segmentos en Acumbamail.
Extraído desde mapeo_segmentos.py y adaptado al patrón de endpoints en src/scrapping/endpoints.
"""
from typing import List, Optional
import time

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from src.shared.logging.logger import get_logger
from src.shared.utils.legacy_utils import load_config, crear_contexto_navegador


class SegmentsScrapingService:
    """
    Servicio para crear segmentos mediante scraping en la UI de Acumbamail.

    Puede operar con una Page ya autenticada (recomendada) o, si no se provee,
    creará un navegador temporal usando el storage state configurado.
    """

    def __init__(self, page: Optional[Page] = None):
        self.page = page
        self.logger = get_logger()
        self.config = load_config()

    # (Sin helpers de lifecycle complicados; se usa context manager cuando no hay Page externa)

    # ============== API pública ==============
    def create_segment(self, list_id: int, segment_name: str, api_client) -> bool:
        """
        Crea un segmento individual.
        Primero verifica por API si ya existe. Si no, lo crea vía UI.
        """
        self.logger.info(f"Verificando si segmento '{segment_name}' existe en lista {list_id}")

        # Verificar existencia por API
        try:
            segmentos_existentes = api_client.suscriptores.get_list_segments(list_id)
            existing_names: List[str] = []
            if segmentos_existentes:
                # soportar distintos formatos (objeto con .segments o lista directa/tuplas)
                items = getattr(segmentos_existentes, 'segments', segmentos_existentes)
                for seg in items or []:
                    if isinstance(seg, tuple):
                        existing_names.append(str(seg[0]))
                    elif hasattr(seg, 'name'):
                        existing_names.append(str(getattr(seg, 'name')))
                    elif isinstance(seg, dict) and 'name' in seg:
                        existing_names.append(str(seg['name']))
                    else:
                        existing_names.append(str(seg))
            if segment_name in existing_names:
                self.logger.info("Segmento ya existe; no es necesario crearlo")
                return True
        except Exception as e:
            self.logger.warning(f"No se pudo verificar segmentos existentes: {e}")

        # Si ya tenemos Page autenticada, usarla; si no, abrir temporal
        if self.page is not None:
            page = self.page
            # flujo directo sin contexto temporal
            # Navegar a la página de segmentos
            segments_url = f"https://acumbamail.com/app/list/{list_id}/segments/"
            self.logger.info(f"Navegando a: {segments_url}")
            page.goto(segments_url, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")

            # Localizar botón "Nuevo segmento" con varias estrategias
            nuevo_segmento_button = None
            try:
                empty_state_button = page.locator("#empty-state-add-segment-button").get_by_text("Nuevo segmento")
                if empty_state_button.is_visible(timeout=5000):
                    nuevo_segmento_button = empty_state_button
                    self.logger.info("Encontrado botón en estado vacío")
            except PlaywrightTimeoutError:
                pass

            if not nuevo_segmento_button:
                try:
                    normal_button = page.locator("#new-segment-button").get_by_text("Nuevo segmento")
                    if normal_button.is_visible(timeout=5000):
                        nuevo_segmento_button = normal_button
                        self.logger.info("Encontrado botón normal")
                except PlaywrightTimeoutError:
                    pass

            if not nuevo_segmento_button:
                try:
                    by_role_button = page.get_by_role("button", name="Nuevo segmento")
                    if by_role_button.is_visible(timeout=5000):
                        nuevo_segmento_button = by_role_button
                        self.logger.info("Encontrado botón por rol")
                except PlaywrightTimeoutError:
                    pass

            if not nuevo_segmento_button:
                self.logger.error("No se pudo encontrar el botón 'Nuevo segmento'")
                return False

            nuevo_segmento_button.click()
            self.logger.info("Clic en 'Nuevo segmento'")

            # Llenar el formulario
            page.wait_for_selector("#field-value-1", timeout=10000)

            # Intento con roles específicos (si existen)
            try:
                nombre_input = page.get_by_role("textbox", name="Nombre del segmento")
                nombre_input.fill(segment_name)
            except Exception:
                nombre_input = page.locator("#field-value-1")
                nombre_input.fill(segment_name)

            # Seleccionar campo y condición y valor
            try:
                campo_select = page.locator("#field-name-1")
                campo_select.select_option(label="Segmentos")

                condicion_select = page.locator("#field-type-1")
                condicion_select.select_option(label="contiene")

                valor_input = page.locator("#field-value-1")
                valor_input.fill(segment_name)
            except Exception as e:
                # Fallback genérico
                self.logger.warning(f"Selectores específicos fallaron: {e}. Probando fallback")
                try:
                    page.get_by_text("Segmentos").click()
                    page.get_by_text("contiene").click()
                    page.locator("input[type='text']").last.fill(segment_name)
                except Exception as e2:
                    self.logger.error(f"No se pudo configurar condiciones: {e2}")
                    return False

            # Guardar el segmento
            try:
                save_button = page.locator("#segment-button-text")
                if not save_button.is_visible():
                    save_button = page.get_by_role("button", name="Guardar")
                if not save_button.is_visible():
                    save_button = page.get_by_role("button", name="Crear")
                if not save_button.is_visible():
                    save_button = page.locator("button[type='submit']").first

                save_button.click()
                self.logger.info("Clic en guardar segmento")

                # Espera breve para confirmar
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_timeout(5000)
                self.logger.info(f"Segmento '{segment_name}' creado exitosamente")
                return True
            except Exception as e:
                self.logger.error(f"Error guardando segmento: {e}")
                return False
        else:
            # Abrir un entorno temporal
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=False)
                context = crear_contexto_navegador(browser)
                page = context.new_page()

                # Navegar a la página de segmentos
                segments_url = f"https://acumbamail.com/app/list/{list_id}/segments/"
                self.logger.info(f"Navegando a: {segments_url}")
                page.goto(segments_url, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle")

                # Localizar botón "Nuevo segmento" con varias estrategias
                nuevo_segmento_button = None
                try:
                    empty_state_button = page.locator("#empty-state-add-segment-button").get_by_text("Nuevo segmento")
                    if empty_state_button.is_visible(timeout=5000):
                        nuevo_segmento_button = empty_state_button
                        self.logger.info("Encontrado botón en estado vacío")
                except PlaywrightTimeoutError:
                    pass

                if not nuevo_segmento_button:
                    try:
                        normal_button = page.locator("#new-segment-button").get_by_text("Nuevo segmento")
                        if normal_button.is_visible(timeout=5000):
                            nuevo_segmento_button = normal_button
                            self.logger.info("Encontrado botón normal")
                    except PlaywrightTimeoutError:
                        pass

                if not nuevo_segmento_button:
                    try:
                        by_role_button = page.get_by_role("button", name="Nuevo segmento")
                        if by_role_button.is_visible(timeout=5000):
                            nuevo_segmento_button = by_role_button
                            self.logger.info("Encontrado botón por rol")
                    except PlaywrightTimeoutError:
                        pass

                if not nuevo_segmento_button:
                    self.logger.error("No se pudo encontrar el botón 'Nuevo segmento'")
                    return False

                nuevo_segmento_button.click()
                self.logger.info("Clic en 'Nuevo segmento'")

                # Llenar el formulario
                page.wait_for_selector("#field-value-1", timeout=10000)

                # Intento con roles específicos (si existen)
                try:
                    nombre_input = page.get_by_role("textbox", name="Nombre del segmento")
                    nombre_input.fill(segment_name)
                except Exception:
                    nombre_input = page.locator("#field-value-1")
                    nombre_input.fill(segment_name)

                # Seleccionar campo y condición y valor
                try:
                    campo_select = page.locator("#field-name-1")
                    campo_select.select_option(label="Segmentos")

                    condicion_select = page.locator("#field-type-1")
                    condicion_select.select_option(label="contiene")

                    valor_input = page.locator("#field-value-1")
                    valor_input.fill(segment_name)
                except Exception as e:
                    # Fallback genérico
                    self.logger.warning(f"Selectores específicos fallaron: {e}. Probando fallback")
                    try:
                        page.get_by_text("Segmentos").click()
                        page.get_by_text("contiene").click()
                        page.locator("input[type='text']").last.fill(segment_name)
                    except Exception as e2:
                        self.logger.error(f"No se pudo configurar condiciones: {e2}")
                        return False

                # Guardar el segmento
                try:
                    save_button = page.locator("#segment-button-text")
                    if not save_button.is_visible():
                        save_button = page.get_by_role("button", name="Guardar")
                    if not save_button.is_visible():
                        save_button = page.get_by_role("button", name="Crear")
                    if not save_button.is_visible():
                        save_button = page.locator("button[type='submit']").first

                    save_button.click()
                    self.logger.info("Clic en guardar segmento")

                    # Espera breve para confirmar
                    page.wait_for_load_state("networkidle", timeout=15000)
                    page.wait_for_timeout(5000)
                    self.logger.info(f"Segmento '{segment_name}' creado exitosamente")
                    return True
                except Exception as e:
                    self.logger.error(f"Error guardando segmento: {e}")
                    return False

    def create_segments_batch(self, list_id: int, segment_names: List[str], api_client) -> bool:
        """
        Crea múltiples segmentos con verificación previa de existencia.
        """
        if not segment_names:
            self.logger.info("No hay segmentos para crear")
            print("  ℹ️  No hay segmentos para crear")
            return True

        # Verificar cuáles existen
        try:
            segmentos_existentes = api_client.suscriptores.get_list_segments(list_id)
            existing_names: List[str] = []
            if segmentos_existentes:
                items = getattr(segmentos_existentes, 'segments', segmentos_existentes)
                for seg in items or []:
                    if isinstance(seg, tuple):
                        existing_names.append(str(seg[0]))
                    elif hasattr(seg, 'name'):
                        existing_names.append(str(getattr(seg, 'name')))
                    elif isinstance(seg, dict) and 'name' in seg:
                        existing_names.append(str(seg['name']))
                    else:
                        existing_names.append(str(seg))
        except Exception as e:
            self.logger.warning(f"Error verificando segmentos existentes: {e}. Crearemos todos.")
            existing_names = []

        to_create = [n for n in segment_names if n not in existing_names]
        already = [n for n in segment_names if n in existing_names]

        if already:
            print(f"  ✅ {len(already)} segmento(s) ya existe(n): {already}")
        if not to_create:
            print("  ✅ Todos los segmentos ya existen")
            return True

        print(f"  🚀 Creando {len(to_create)} segmento(s) nuevo(s): {to_create}")
        success = True
        created_count = 0
        for idx, name in enumerate(to_create):
            print(f"      📝 Creando segmento {idx+1}/{len(to_create)}: '{name}'")
            ok = self.create_segment(list_id, name, api_client)
            if ok:
                print(f"      ✅ Segmento '{name}' creado exitosamente")
                created_count += 1
            else:
                print(f"      ❌ Error creando segmento '{name}'")
                success = False
            if idx < len(to_create) - 1:
                time.sleep(2)

        total = len(segment_names)
        print("  📊 Resumen de segmentos:")
        print(f"      • Total solicitados: {total}")
        print(f"      • Ya existían: {len(already)}")
        print(f"      • Creados nuevos: {created_count}")
        print(f"      • Errores: {len(to_create) - created_count}")

        return success
