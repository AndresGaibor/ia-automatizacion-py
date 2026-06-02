"""
ListUploadPage — Page Object para subida de archivos CSV a listas.

Maneja:
- Subida de archivo CSV
- Mapeo de columnas
- Finalización del proceso de importación
"""
from playwright.sync_api import Page, TimeoutError as PWTimeoutError, expect
from typing import Optional

from src.infrastructure.scraping.pages.base_page import PaginaBase
from src.shared.logging.logger import get_logger

from ..models.listas import ListUploadColumn

logger = get_logger()


class PaginaSubidaListas(PaginaBase):
    """Page Object para proceso de subida de suscriptores."""

    def click_anadir_suscriptores(self) -> bool:
        """Hace click en el enlace 'Añadir suscriptores'."""
        try:
            self._page.get_by_role("link", name="Añadir suscriptores").click()
            self._page.wait_for_load_state("domcontentloaded", timeout=30000)
            return True
        except Exception as e:
            logger.error(f"❌ Error click en 'Añadir suscriptores': {e}")
            return False

    def select_csv_excel_option(self) -> bool:
        """Selecciona la opción 'Archivo CSV/Excel'."""
        try:
            self._page.get_by_label("Archivo CSV/Excel").check()
            return True
        except Exception as e:
            logger.error(f"❌ Error seleccionando 'Archivo CSV/Excel': {e}")
            return False

    def upload_csv_file(self, archivo_csv: str) -> bool:
        """Sube el archivo CSV."""
        try:
            import os
            tamaño = os.path.getsize(archivo_csv) / 1024
            logger.info(f"   📎 Subiendo archivo ({tamaño:.1f} KB)")
            self._page.set_input_files('input[type="file"]', archivo_csv)
            return True
        except Exception as e:
            logger.error(f"❌ Error subiendo archivo CSV: {e}")
            return False

    def click_aniadir_button(self) -> bool:
        """Hace click en el botón 'Añadir' para confirmar la subida."""
        try:
            btn_continuar = self._page.locator("a", has_text="Añadir")
            btn_continuar.wait_for(state="visible", timeout=10000)
            if btn_continuar.is_visible():
                btn_continuar.click()
                self._page.wait_for_load_state("domcontentloaded", timeout=20000)
                logger.info("   🖱️  Click en 'Añadir'")
            return True
        except PWTimeoutError:
            logger.debug("   ⏱️ Timeout buscando botón 'Añadir', usando Enter")
            self._page.keyboard.press("Enter")
            return True
        except Exception as e:
            logger.error(f"❌ Error click en 'Añadir': {e}")
            self._page.keyboard.press("Enter")
            return True

    def close_accept_popup(self) -> bool:
        """Cierra el popup de confirmación 'Aceptar' si aparece."""
        try:
            btn_close_popup = self._page.locator("a", has_text="Aceptar")
            btn_close_popup.wait_for(state="visible", timeout=5000)
            btn_close_popup.click(timeout=3000)
            logger.debug("   ✓ Popup cerrado")
            return True
        except PWTimeoutError:
            logger.debug("   ✓ No apareció popup")
            return True
        except Exception:
            return True

    def subir_archivo(self, archivo_csv: str) -> bool:
        """Sube el archivo CSV a la lista."""
        try:
            logger.info("📤 Subiendo archivo CSV")

            if not self.click_anadir_suscriptores():
                return False

            if not self.select_csv_excel_option():
                return False

            if not self.upload_csv_file(archivo_csv):
                return False

            logger.info("   ⏳ Esperando procesamiento del archivo...")
            self.click_aniadir_button()
            self.close_accept_popup()

            logger.success("✅ Archivo CSV subido exitosamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error subiendo archivo: {e}")
            return False

    def get_column_container(self, column_index: int):
        """Obtiene el contenedor de una columna específica."""
        return self._page.locator("div.col", has_text=f"Columna {column_index}")

    def select_crear_nueva_opcion(self, column_index: int, timeout: int = 30000) -> bool:
        """Selecciona la opción 'Crear nueva...' en el selector de columna."""
        try:
            contenedor = self.get_column_container(column_index)
            selector = contenedor.locator("select")
            selector.select_option(label="Crear nueva...", timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"❌ Error seleccionando 'Crear nueva...': {e}")
            return False

    def wait_for_field_popup(self, column_index: int) -> bool:
        """Espera a que aparezca el popup de creación de campo."""
        try:
            contenedor_popup = self._page.locator(f"#add-field-popup-{column_index}")
            contenedor_popup.wait_for(state="visible", timeout=10000)
            return True
        except Exception as e:
            logger.error(f"❌ Error esperando popup de campo: {e}")
            return False

    def fill_field_name(self, column_index: int, field_name: str) -> bool:
        """Llena el nombre del campo en el popup."""
        try:
            input_nombre = self._page.locator(f"#popup-field-name-{column_index}")
            input_nombre.fill(field_name)
            return True
        except Exception as e:
            logger.error(f"❌ Error llenando nombre de campo: {e}")
            return False

    def select_field_type(self, column_index: int, field_type: str) -> bool:
        """Selecciona el tipo de campo en el popup."""
        try:
            contenedor_popup = self._page.locator(f"#add-field-popup-{column_index}")
            selector_tipo = contenedor_popup.locator("select")
            selector_tipo.select_option(label=field_type, timeout=10000)
            return True
        except Exception as e:
            logger.error(f"❌ Error seleccionando tipo de campo: {e}")
            return False

    def click_aniadir_field_button(self, column_index: int) -> bool:
        """Hace click en el botón 'Añadir' del popup de campo."""
        try:
            contenedor_popup = self._page.locator(f"#add-field-popup-{column_index}")
            btn_aniadir = contenedor_popup.get_by_role("button", name="Añadir")
            btn_aniadir.click(timeout=5000)
            return True
        except Exception as e:
            logger.error(f"❌ Error click en 'Añadir' del popup: {e}")
            return False

    def mapear_columna(self, columna: ListUploadColumn) -> bool:
        """Mapea una columna individual."""
        try:
            logger.info(f"📋 Columna {columna.index}: '{columna.name}' → {columna.field_type}")

            if not self.select_crear_nueva_opcion(columna.index):
                return False

            if not self.wait_for_field_popup(columna.index):
                return False

            logger.debug(f"   ✏️  Nombre: '{columna.name}'")
            if not self.fill_field_name(columna.index, columna.name):
                return False

            logger.debug(f"   🏷️  Tipo: '{columna.field_type}'")
            if not self.select_field_type(columna.index, columna.field_type):
                return False

            logger.debug("   🖱️  Click en 'Añadir'")
            if not self.click_aniadir_field_button(columna.index):
                return False

            self._page.wait_for_load_state("networkidle", timeout=10000)
            self.close_accept_popup()

            logger.info(f"   ✅ Campo mapeado exitosamente")
            return True

        except Exception as e:
            logger.warning(f"   ⚠️ Error mapeando columna {columna.name}: {str(e)[:100]}...")
            return False

    def detectar_columnas_disponibles(self, total_columnas: int) -> list[int]:
        """Detecta qué columnas están disponibles en la página."""
        columnas_disponibles = []
        for i in range(1, total_columnas + 3):
            try:
                contenedor = self._page.locator("div.col", has_text=f"Columna {i}")
                if contenedor.count() > 0:
                    columnas_disponibles.append(i)
                    logger.debug(f"   ✓ Columna {i} encontrada")
            except Exception:
                break
        return columnas_disponibles

    def click_siguiente(self) -> bool:
        """Hace click en el botón 'Siguiente'."""
        try:
            btn_siguiente = self._page.get_by_text("Siguiente", exact=True)
            is_visible = btn_siguiente.is_visible(timeout=5000)

            if not is_visible:
                logger.warning("⚠️ Botón 'Siguiente' no visible, intentando selector alternativo")
                btn_siguiente = self._page.locator("a:visible", has_text="Siguiente")
                if btn_siguiente.count() == 0:
                    btn_siguiente = self._page.get_by_role("link", name="Siguiente")

            btn_siguiente.click()
            self._page.wait_for_load_state("domcontentloaded", timeout=20000)
            return True

        except Exception as e:
            logger.error(f"❌ Error click en 'Siguiente': {e}")
            return False

    def verificar_mensaje_exito(self) -> bool:
        """Verifica que aparezca el mensaje de éxito de importación."""
        try:
            expect(
                self._page.get_by_text("Tus suscriptores se han importado con éxito")
            ).to_be_visible(timeout=30000)
            logger.info("✅ Mensaje de éxito encontrado")
            logger.info("🎉 Suscriptores importados con éxito")
            return True

        except PWTimeoutError:
            logger.warning("⚠️ No se encontró mensaje principal, intentando alternativo")
            try:
                expect(
                    self._page.get_by_text("importado con éxito")
                ).to_be_visible(timeout=10000)
                logger.info("✅ Mensaje de éxito alternativo encontrado")
                return True
            except PWTimeoutError:
                logger.warning("⚠️ No se encontró ningún mensaje de éxito")
                return False