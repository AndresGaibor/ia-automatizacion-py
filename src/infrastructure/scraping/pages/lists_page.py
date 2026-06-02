"""
ListsPage — página de gestión de listas de Acumbamail.

Navega a la sección de listas y encapsula:
- navegación inicial (url_base + url)
- autenticación via LoginPage
- click en link "Listas"
- creación de listas
- subida de archivos CSV
- mapeo de columnas
- finalización del proceso de importación
"""

from playwright.sync_api import (
    Page,
    TimeoutError as PWTimeoutError,
    Error as PWError,
    expect,
)
from typing import Optional, Callable, Tuple, Any

from src.infrastructure.scraping.pages.base_page import BasePage
from src.infrastructure.scraping.pages.login_page import LoginPage
from src.shared.logging.logger import get_logger
from src.utils import get_timeouts

from ..models.listas import ListUploadColumn, ListUploadProgress

logger = get_logger()


class ListsPage(BasePage):
    def __init__(self, page: Page, base_url: str, url: str):
        super().__init__(page, url)
        self._base_url = base_url
        self._url = url
        self._login_page = LoginPage(page, base_url)

    def navigate_to_lists(self) -> bool:
        """
        Navega a la sección de listas:
        1. Navega a url_base
        2. Navega a url (página principal de newsletters)
        3. Hace click en el link "Listas"

        Returns:
            True si la navegación fue exitosa
        """
        try:
            logger.info("🌐 Navegando a la sección de listas")

            logger.info(f"   → Navegando a URL base: {self._base_url}")
            self._page.goto(self._base_url, wait_until="domcontentloaded", timeout=60000)

            logger.info(f"   → Navegando a URL principal: {self._url}")
            self._page.goto(self._url, wait_until="domcontentloaded", timeout=60000)

            logger.info("   → Click en link 'Listas'")
            self._page.get_by_role("link", name="Listas").first.click()
            self._page.wait_for_load_state("domcontentloaded", timeout=30000)

            logger.info("✅ Navegación a sección de listas completada")
            return True

        except Exception as e:
            logger.error(f"❌ Error navegando a la sección de listas: {e}")
            return False

    def authenticate(self) -> bool:
        """
        Ejecuta el proceso de autenticación usando LoginPage POM.

        Returns:
            True si la autenticación fue exitosa
        """
        from src.autentificacion import login
        from playwright.sync_api import BrowserContext

        try:
            logger.info("🔐 Iniciando autenticación")
            context = self._page.context
            login(self._page, context)
            logger.info("✅ Autenticación exitosa")
            return True

        except Exception as e:
            logger.error(f"❌ Error en autenticación: {e}")
            return False

    def click_nueva_lista(self) -> bool:
        """
        Hace click en el botón 'Nueva Lista'.

        Returns:
            True si el click fue exitoso
        """
        try:
            btn_nueva_lista = self._page.locator(
                "a.font-color-white-1", has_text="Nueva Lista"
            )
            btn_nueva_lista.wait_for(state="visible", timeout=10000)
            btn_nueva_lista.click()
            return True
        except Exception as e:
            logger.error(f"❌ Error click en 'Nueva Lista': {e}")
            return False

    def fill_nombre_lista(self, nombre_lista: str) -> bool:
        """
        Llena el campo de nombre de lista.

        Args:
            nombre_lista: Nombre para la nueva lista

        Returns:
            True si se rellenó correctamente
        """
        try:
            name_input = self._page.locator("#name")
            name_input.wait_for(state="visible", timeout=10000)
            name_input.fill("")
            name_input.fill(nombre_lista)
            return True
        except Exception as e:
            logger.error(f"❌ Error rellenando nombre de lista: {e}")
            return False

    def click_crear_lista(self) -> bool:
        """
        Hace click en el botón 'Crear' para crear la lista.

        Returns:
            True si el click fue exitoso
        """
        try:
            self._page.get_by_role("button", name="Crear").click()
            return True
        except Exception as e:
            logger.error(f"❌ Error click en 'Crear': {e}")
            return False

    def crear_lista(self, nombre_lista: str) -> bool:
        """
        Crea una nueva lista en Acumbamail.

        Args:
            nombre_lista: Nombre de la lista a crear

        Returns:
            True si se creó exitosamente
        """
        try:
            logger.info(f"📝 Creando lista: '{nombre_lista}'")

            if not self.click_nueva_lista():
                return False

            logger.info(f"   ✏️  Ingresando nombre: '{nombre_lista}'")
            if not self.fill_nombre_lista(nombre_lista):
                return False

            logger.info("   🖱️  Click en 'Crear'")
            if not self.click_crear_lista():
                return False

            logger.success(f"✅ Lista '{nombre_lista}' creada exitosamente")
            return True

        except Exception as e:
            logger.error(f"❌ Error creando lista: {e}")
            return False

    def click_anadir_suscriptores(self) -> bool:
        """
        Hace click en el enlace 'Añadir suscriptores'.

        Returns:
            True si el click fue exitoso
        """
        try:
            self._page.get_by_role("link", name="Añadir suscriptores").click()
            self._page.wait_for_load_state("domcontentloaded", timeout=30000)
            return True
        except Exception as e:
            logger.error(f"❌ Error click en 'Añadir suscriptores': {e}")
            return False

    def select_csv_excel_option(self) -> bool:
        """
        Selecciona la opción 'Archivo CSV/Excel'.

        Returns:
            True si se seleccionó correctamente
        """
        try:
            self._page.get_by_label("Archivo CSV/Excel").check()
            return True
        except Exception as e:
            logger.error(f"❌ Error seleccionando 'Archivo CSV/Excel': {e}")
            return False

    def upload_csv_file(self, archivo_csv: str) -> bool:
        """
        Sube el archivo CSV usando el input de file.

        Args:
            archivo_csv: Ruta al archivo CSV

        Returns:
            True si se subió correctamente
        """
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
        """
        Hace click en el botón 'Añadir' para confirmar la subida.

        Returns:
            True si el click fue exitoso
        """
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
        """
        Cierra el popup de confirmación 'Aceptar' si aparece.

        Returns:
            True si se cerró o no apareció
        """
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
        """
        Sube el archivo CSV a la lista.

        Args:
            archivo_csv: Ruta al archivo CSV

        Returns:
            True si se subió exitosamente
        """
        try:
            logger.info("📤 Subiendo archivo CSV")

            logger.info("   🖱️  Click en 'Añadir suscriptores'")
            if not self.click_anadir_suscriptores():
                return False

            logger.info("   ☑️  Seleccionando opción 'Archivo CSV/Excel'")
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
        """
        Obtiene el contenedor de una columna específica.

        Args:
            column_index: Índice de la columna (1-based)

        Returns:
            Locator del contenedor
        """
        return self._page.locator("div.col", has_text=f"Columna {column_index}")

    def select_crear_nueva_opcion(self, column_index: int, timeout: int = 30000) -> bool:
        """
        Selecciona la opción 'Crear nueva...' en el selector de columna.

        Args:
            column_index: Índice de la columna
            timeout: Timeout en ms

        Returns:
            True si se seleccionó correctamente
        """
        try:
            contenedor = self.get_column_container(column_index)
            selector = contenedor.locator("select")
            selector.select_option(label="Crear nueva...", timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"❌ Error seleccionando 'Crear nueva...': {e}")
            return False

    def wait_for_field_popup(self, column_index: int) -> bool:
        """
        Espera a que aparezca el popup de creación de campo.

        Args:
            column_index: Índice de la columna

        Returns:
            True si el popup apareció
        """
        try:
            contenedor_popup = self._page.locator(f"#add-field-popup-{column_index}")
            contenedor_popup.wait_for(state="visible", timeout=10000)
            return True
        except Exception as e:
            logger.error(f"❌ Error esperando popup de campo: {e}")
            return False

    def fill_field_name(self, column_index: int, field_name: str) -> bool:
        """
        Llena el nombre del campo en el popup.

        Args:
            column_index: Índice de la columna
            field_name: Nombre del campo

        Returns:
            True si se rellenó correctamente
        """
        try:
            input_nombre = self._page.locator(f"#popup-field-name-{column_index}")
            input_nombre.fill(field_name)
            return True
        except Exception as e:
            logger.error(f"❌ Error llenando nombre de campo: {e}")
            return False

    def select_field_type(self, column_index: int, field_type: str) -> bool:
        """
        Selecciona el tipo de campo en el popup.

        Args:
            column_index: Índice de la columna
            field_type: Tipo de campo

        Returns:
            True si se seleccionó correctamente
        """
        try:
            contenedor_popup = self._page.locator(f"#add-field-popup-{column_index}")
            selector_tipo = contenedor_popup.locator("select")
            selector_tipo.select_option(label=field_type, timeout=10000)
            return True
        except Exception as e:
            logger.error(f"❌ Error seleccionando tipo de campo: {e}")
            return False

    def click_aniadir_field_button(self, column_index: int) -> bool:
        """
        Hace click en el botón 'Añadir' del popup de campo.

        Args:
            column_index: Índice de la columna

        Returns:
            True si el click fue exitoso
        """
        try:
            contenedor_popup = self._page.locator(f"#add-field-popup-{column_index}")
            btn_aniadir = contenedor_popup.get_by_role("button", name="Añadir")
            btn_aniadir.click(timeout=5000)
            return True
        except Exception as e:
            logger.error(f"❌ Error click en 'Añadir' del popup: {e}")
            return False

    def mapear_columna(self, columna: ListUploadColumn) -> bool:
        """
        Mapea una columna individual.

        Args:
            columna: Objeto ListUploadColumn con los datos

        Returns:
            True si se mapeó correctamente
        """
        try:
            logger.info(
                f"📋 Columna {columna.index}: '{columna.name}' → {columna.field_type}"
            )

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
        """
        Detecta qué columnas están disponibles en la página.

        Args:
            total_columnas: Total de columnas a buscar

        Returns:
            Lista de índices de columnas disponibles
        """
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
        """
        Hace click en el botón 'Siguiente'.

        Returns:
            True si el click fue exitoso
        """
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
        """
        Verifica que aparezca el mensaje de éxito de importación.

        Returns:
            True si el mensaje aparece
        """
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