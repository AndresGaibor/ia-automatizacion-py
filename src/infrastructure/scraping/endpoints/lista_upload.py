"""
Endpoint de scraping para subir/crear listas de suscriptores en Acumbamail
"""

import logging
from playwright.sync_api import (
    Page,
    TimeoutError as PWTimeoutError,
    Error as PWError,
    expect,
)
from typing import Optional, Callable, Tuple, Any
from datetime import datetime
import pandas as pd
import os
import tempfile
import uuid
from pathlib import Path


from ..models.listas import (
    ListUploadConfig,
    ListUploadSession,
    ListUploadResult,
    ListUploadColumn,
    ListUploadProgress,
)

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from ....shared.logging.logger import get_logger
from ....tipo_campo import field_type_label
from ....utils import get_timeouts


class ListUploader:
    """Scraper para subir/crear listas de suscriptores usando web scraping"""

    def __init__(self):
        self.logger = get_logger()

    def safe_interaction(
        self, page: Page, action_description: str, action_callable: Callable[[], Any]
    ) -> Tuple[Optional[Any], bool]:
        """
        Wrapper para interacciones seguras con manejo robusto de errores

        Args:
            page: Página de Playwright
            action_description: Descripción de la acción para logging
            action_callable: Función callable que ejecuta la acción

        Returns:
            Tuple (resultado, exito): Resultado de la acción y booleano de éxito
        """
        try:
            result = action_callable()
            return result, True
        except PWTimeoutError:
            self.logger.warning(f"⏱️ Timeout en: {action_description}")
            return None, False
        except PWError as e:
            self.logger.error(f"❌ Error de Playwright en {action_description}: {e}")
            return None, False
        except Exception as e:
            self.logger.error(f"❌ Error inesperado en {action_description}: {e}")
            return None, False

    def wait_and_click(
        self, page: Page, selector_description: str, locator, timeout: int = 10000
    ) -> bool:
        """
        Espera a que un elemento esté visible y hace clic

        Args:
            page: Página de Playwright
            selector_description: Descripción del selector para logging
            locator: Locator de Playwright
            timeout: Timeout en milisegundos

        Returns:
            True si tuvo éxito, False si no
        """
        try:
            locator.wait_for(state="visible", timeout=timeout)
            locator.click()
            self.logger.debug(f"✅ Click exitoso: {selector_description}")
            return True
        except PWTimeoutError:
            self.logger.warning(f"⏱️ Elemento no visible: {selector_description}")
            return False
        except PWError as e:
            self.logger.error(f"❌ Error haciendo click en {selector_description}: {e}")
            return False

    def inicializar_navegacion_lista(self, page: Page) -> bool:
        """
        Navega a la sección de listas con espera optimizada
        """
        try:
            self.logger.info("Navegando a la sección de listas")
            # Usar selector moderno para navegar a Listas (primer link en la navegación)
            page.get_by_role("link", name="Listas").first.click()
            # Optimizado: solo esperar domcontentloaded en lugar de networkidle
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            return True
        except Exception as e:
            self.logger.error(f"Error navegando a la sección de listas: {e}")
            return False

    def cargar_columnas_excel(
        self, archivo: str, hoja: str
    ) -> tuple[list[ListUploadColumn], list[str]]:
        """
        Carga columnas del Excel y obtiene valores de ejemplo

        Returns:
            (columnas, segunda_fila): Lista de columnas con metadatos y valores de la segunda fila
        """
        try:
            with pd.ExcelFile(archivo, engine="openpyxl") as xls:
                # Leer como texto y reemplazar NaN por vacío
                df = pd.read_excel(xls, sheet_name=hoja, dtype=str).fillna("")

            columnas_nombres = [str(c) for c in df.columns.tolist()]

            # Primera fila de datos (debajo del header)
            if len(df) > 0:
                segunda_fila = [str(v) for v in df.iloc[0].tolist()]
            else:
                segunda_fila = [""] * len(columnas_nombres)

            # Crear objetos ListUploadColumn con detección de tipo
            columnas = []
            for idx, nombre in enumerate(
                columnas_nombres, start=1
            ):  # Start at 1 (Columna 1, 2, 3, etc.)
                valor_ejemplo = (
                    segunda_fila[idx - 1] if idx - 1 < len(segunda_fila) else ""
                )
                tipo_campo = (
                    field_type_label(valor_ejemplo) if valor_ejemplo else "Texto"
                )

                columnas.append(
                    ListUploadColumn(
                        index=idx,
                        name=nombre,
                        field_type=tipo_campo,
                        sample_value=valor_ejemplo,
                    )
                )

            return columnas, segunda_fila

        except Exception as e:
            self.logger.error(f"Error cargando columnas: {e}")
            return [], []

    def generar_archivo_temporal_csv(self, archivo_excel: str, hoja: str) -> str:
        """
        Genera un CSV temporal solo con la hoja indicada

        Returns:
            Ruta del archivo temporal CSV
        """
        try:
            with pd.ExcelFile(archivo_excel, engine="openpyxl") as xls:
                df = pd.read_excel(xls, sheet_name=hoja, dtype=str).fillna("")

            # CSV temporal compatible con Excel (utf-8-sig)
            tmp_path = os.path.join(
                tempfile.gettempdir(), f"lista_{uuid.uuid4().hex}.csv"
            )
            df.to_csv(tmp_path, index=False, encoding="utf-8-sig")

            self.logger.info(f"Archivo temporal CSV generado: {tmp_path}")
            return tmp_path
        except Exception as e:
            self.logger.error(f"Error generando CSV temporal: {e}")
            raise

    def crear_lista(self, page: Page, nombre_lista: str) -> bool:
        """
        Crea una nueva lista en Acumbamail usando selectores modernos

        Returns:
            True si se creó exitosamente
        """
        try:
            self.logger.info(f"📝 Creando lista: '{nombre_lista}'")

            # Click en "Nueva Lista" - optimizado sin esperas innecesarias
            self.logger.info("   🖱️  Click en 'Nueva Lista'")
            # Eliminado: wait_for_load_state redundantes

            # El enlace no define href, por lo que no expone role="link"; usamos fallback text-based
            btn_nueva_lista = page.locator(
                "a.font-color-white-1", has_text="Nueva Lista"
            )
            btn_nueva_lista.wait_for(state="visible", timeout=10000)  # Reducido de 15s
            btn_nueva_lista.click()

            # Llenar nombre de lista - con auto-waiting
            self.logger.info(f"   ✏️  Ingresando nombre: '{nombre_lista}'")
            name_input = page.locator("#name")
            name_input.wait_for(state="visible", timeout=10000)  # Reducido de 15s
            name_input.fill("")  # Optimizado: fill en lugar de type lento
            name_input.fill(nombre_lista)  # Eliminado delay=30

            # Click en "Crear" - ya usa role-based locator (validado con BrowserMCP)
            self.logger.info("   🖱️  Click en 'Crear'")
            page.get_by_role("button", name="Crear").click()
            # Auto-waiting de Playwright - no necesita wait_for_load_state

            self.logger.success(f"✅ Lista '{nombre_lista}' creada exitosamente")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error creando lista: {e}")
            return False

    def subir_archivo(self, page: Page, archivo_csv: str) -> bool:
        """
        Sube el archivo CSV a la lista usando selectores modernos

        Returns:
            True si se subió exitosamente
        """
        try:
            self.logger.info("📤 Subiendo archivo CSV")

            # Click en "Añadir suscriptores" - usando role-based locator optimizado
            self.logger.info("   🖱️  Click en 'Añadir suscriptores'")
            page.get_by_role("link", name="Añadir suscriptores").click()
            # Optimizado: solo esperar domcontentloaded en lugar de networkidle
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            # Auto-waiting de Playwright - no necesita wait_for_load_state

            # Seleccionar opción "Archivo CSV/Excel" - usando label-based locator (validado con BrowserMCP)
            self.logger.info("   ☑️  Seleccionando opción 'Archivo CSV/Excel'")
            page.get_by_label("Archivo CSV/Excel").check()

            # Subir archivo - usando file input selector (patrón moderno)
            import os

            tamaño = os.path.getsize(archivo_csv) / 1024  # KB
            self.logger.info(f"   📎 Subiendo archivo ({tamaño:.1f} KB)")
            page.set_input_files('input[type="file"]', archivo_csv)

            # Esperar a que se procese el archivo y buscar botón de continuar
            self.logger.info("   ⏳ Esperando procesamiento del archivo...")
            try:
                # Optimizado: buscar botón con timeout reducido
                btn_continuar = page.locator("a", has_text="Añadir")
                btn_continuar.wait_for(
                    state="visible", timeout=10000
                )  # Reducido de 15s

                if btn_continuar.is_visible():
                    btn_continuar.click()
                    # Optimizado: usar domcontentloaded en lugar de networkidle
                    page.wait_for_load_state("domcontentloaded", timeout=20000)
                    self.logger.info("   🖱️  Click en 'Añadir'")
                else:
                    # Intentar con Enter si no se encuentra el botón
                    page.keyboard.press("Enter")
                    self.logger.info("   ⌨️  Presionando Enter para continuar")
            except PWTimeoutError:
                # Timeout: intentar con Enter como fallback
                page.keyboard.press("Enter")
                self.logger.info("   ⌨️  Presionando Enter para continuar (timeout)")
            except Exception:
                # Error general: intentar con Enter como último recurso
                page.keyboard.press("Enter")
                self.logger.info("   ⌨️  Presionando Enter para continuar (error)")

            # Cerrar popup si aparece - optimizado con timeout reducido
            try:
                btn_close_popup = page.locator("a", has_text="Aceptar")
                btn_close_popup.wait_for(
                    state="visible", timeout=5000
                )  # Reducido de 10s
                btn_close_popup.click(timeout=3000)  # Reducido de 5s
                self.logger.debug("   ✓ Popup cerrado")
            except PWTimeoutError:
                self.logger.debug("   ✓ No apareció popup")

            self.logger.success("✅ Archivo CSV subido exitosamente")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error subiendo archivo: {e}")
            return False

    def mapear_columnas(
        self,
        page: Page,
        columnas: list[ListUploadColumn],
        progress_callback: Optional[Callable[[ListUploadProgress], None]] = None,
    ) -> int:
        """
        Mapea las columnas del archivo subido a campos personalizados optimizado

        Args:
            page: Página de Playwright
            columnas: Lista de columnas a mapear
            progress_callback: Callback opcional para reportar progreso

        Returns:
            Número de campos mapeados exitosamente
        """
        campos_mapeados = 0
        total_columnas = len(columnas)
        timeouts = get_timeouts()
        column_mapping_timeout = timeouts.get("column_mapping", 30000)

        try:
            self.logger.info("")
            self.logger.info(f"🔗 MAPEO DE COLUMNAS ({total_columnas} columnas)")
            self.logger.info("-" * 70)

            # Validación temprana: detectar cuántas columnas realmente existen en la página
            self.logger.info("🔍 Detectando columnas disponibles en la página...")
            columnas_disponibles = []

            for i in range(
                1, total_columnas + 3
            ):  # Buscar hasta 2 columnas extra por seguridad
                try:
                    contenedor = page.locator("div.col", has_text=f"Columna {i}")
                    if contenedor.count() > 0:
                        columnas_disponibles.append(i)
                        self.logger.debug(f"   ✓ Columna {i} encontrada")
                    else:
                        if i <= total_columnas:
                            self.logger.warning(f"   ⚠️ Columna {i} no encontrada")
                except Exception:
                    break

            columnas_procesar = min(total_columnas, len(columnas_disponibles))

            # La primera columna (email, index=1) ya está mapeada automáticamente
            # Buscar la columna con index=1 para saltarla
            columnas_a_mapear = 0
            indices_a_mapear = []

            for i, columna in enumerate(columnas):
                if columna.index != 1:  # Saltar la columna con index=1 (email)
                    indices_a_mapear.append(i)
                    columnas_a_mapear += 1

            self.logger.info(
                f"📊 Total columnas: {columnas_procesar}, Email (index=1) ya mapeado, Columnas a mapear: {columnas_a_mapear}"
            )
            if columnas_a_mapear == 0:
                self.logger.info("✅ No hay columnas adicionales para mapear")
                return 1  # Retornar 1 por la columna de email ya mapeada

            # Mapear las columnas que no son email (index != 1)
            for loop_idx, columnas_idx in enumerate(indices_a_mapear):
                columna = columnas[columnas_idx]
                try:
                    # Reportar progreso (ajustado para columnas que no son email)
                    if progress_callback:
                        # Calcular el progreso dentro de las columnas a mapear (ignorando email)
                        progreso_actual = loop_idx  # 0-based para las columnas a mapear
                        porcentaje_progreso = (progreso_actual / columnas_a_mapear * 30) if columnas_a_mapear > 0 else 0

                        progreso = ListUploadProgress(
                            stage="mapeando_campos",
                            current_column=progreso_actual + 1,  # 1-based para mostrar al usuario
                            total_columns=columnas_a_mapear,  # Solo columnas a mapear
                            mensaje=f"Mapeando '{columna.name}'",
                            porcentaje=60.0 + porcentaje_progreso,  # 60-90%
                        )
                        progress_callback(progreso)

                    self.logger.info(
                        f"📋 Columna {columna.index}: '{columna.name}' → {columna.field_type}"
                    )

                    # Seleccionar contenedor de la columna
                    self.logger.debug(f"   🔍 Localizando Columna {columna.index}")
                    contenedor = page.locator(
                        "div.col", has_text=f"Columna {columna.index}"
                    )

                    # Validar que el contenedor exista antes de continuar
                    if contenedor.count() == 0:
                        self.logger.warning(
                            f"   ⚠️ Contenedor de Columna {columna.index} no encontrado"
                        )
                        continue

                    selector = contenedor.locator("select")

                    # Seleccionar "Crear nueva..." con timeout optimizado
                    self.logger.debug("   🖱️  Seleccionando 'Crear nueva...'")
                    selector.select_option(
                        label="Crear nueva...", timeout=column_mapping_timeout
                    )

                    # Esperar a que aparezca el popup con timeout reducido
                    contenedor_popup = page.locator(f"#add-field-popup-{columna.index}")
                    contenedor_popup.wait_for(state="visible", timeout=10000)

                    # Llenar nombre del campo
                    self.logger.debug(f"   ✏️  Nombre: '{columna.name}'")
                    input_nombre = contenedor_popup.locator(
                        f"#popup-field-name-{columna.index}"
                    )
                    input_nombre.fill(columna.name)

                    # Seleccionar tipo de campo
                    self.logger.debug(f"   🏷️  Tipo: '{columna.field_type}'")
                    selector_tipo = contenedor_popup.locator("select")
                    selector_tipo.select_option(label=columna.field_type, timeout=10000)

                    # Click en "Añadir"
                    self.logger.debug("   🖱️  Click en 'Añadir'")
                    btn_aniadir = contenedor_popup.get_by_role("button", name="Añadir")
                    btn_aniadir.click(timeout=5000)

                    # Esperar a que la página se estabilice después de añadir el campo
                    page.wait_for_load_state("networkidle", timeout=10000)

                    # Cerrar popup si aparece después de añadir campo
                    try:
                        self.logger.debug("   🔍 Buscando popup después de añadir campo...")
                        btn_close_popup = page.locator('a', has_text="Aceptar")
                        btn_close_popup.wait_for(state="visible", timeout=5000)
                        btn_close_popup.click(timeout=3000)
                        self.logger.debug("   ✅ Popup cerrado después de añadir campo")
                    except PWTimeoutError:
                        self.logger.debug("   ✓ No apareció popup después de añadir campo")

                    campos_mapeados += 1
                    self.logger.info(f"   ✅ Campo mapeado exitosamente")

                except PWTimeoutError as e:
                    self.logger.warning(
                        f"   ⚠️ Timeout en columna {columna.name}: {str(e)[:100]}..."
                    )
                    continue
                except Exception as e:
                    self.logger.warning(
                        f"   ⚠️ Error en columna {columna.name}: {str(e)[:100]}..."
                    )
                    continue

            self.logger.info("")
            # Agregar 1 por la columna de email que se mapea automáticamente
            total_campos_mapeados = campos_mapeados + 1 if campos_mapeados > 0 else 1
            self.logger.info(
                f"📊 RESULTADO DEL MAPEO: {total_campos_mapeados}/{total_columnas} campos exitosos (incluyendo email)"
            )
            return total_campos_mapeados

        except Exception as e:
            self.logger.error(f"❌ Error en mapeo de columnas: {e}")
            return campos_mapeados

    def finalizar_subida(self, page: Page) -> bool:
        """
        Finaliza el proceso de subida haciendo click en "Siguiente" usando selectores modernos

        Returns:
            True si se finalizó exitosamente
        """
        try:
            self.logger.info("🔄 Iniciando finalización de subida")
            self.logger.debug(f"URL actual: {page.url}")

            # Paso 1: Localizar el botón "Siguiente"
            self.logger.info("📌 Paso 1: Localizando botón 'Siguiente'")
            try:
                btn_siguiente = page.get_by_text("Siguiente", exact=True)
                self.logger.debug("✅ Botón 'Siguiente' localizado por texto exacto")

                # Verificar que el botón sea visible antes de hacer clic
                is_visible = btn_siguiente.is_visible(timeout=5000)
                self.logger.debug(f"🔍 Botón visible: {is_visible}")

                if not is_visible:
                    self.logger.warning(
                        "⚠️ Botón 'Siguiente' no es visible, intentando con otros selectores"
                    )
                    # Intentar con otros selectores
                    btn_siguiente = page.locator("a:visible", has_text="Siguiente")
                    if btn_siguiente.count() == 0:
                        btn_siguiente = page.get_by_role("link", name="Siguiente")
                    self.logger.debug("✅ Botón encontrado con selector alternativo")

            except Exception as e:
                self.logger.error(
                    f"❌ ERROR PASO 1 - No se pudo localizar botón 'Siguiente': {e}"
                )
                self.logger.error(f"Tipo de error: {type(e).__name__}")
                self.logger.debug(f"URL actual cuando falló: {page.url}")
                return False

            # Paso 2: Hacer clic en el botón
            self.logger.info("📌 Paso 2: Haciendo clic en botón 'Siguiente'")
            try:
                btn_siguiente.click()
                self.logger.debug("✅ Click realizado exitosamente")

                # Optimizado: eliminada espera fija de 1s (auto-waiting de Playwright es suficiente)

            except PWTimeoutError as e:
                self.logger.error(f"❌ ERROR PASO 2 - Timeout al hacer clic: {e}")
                self.logger.debug(
                    f"Botón HTML: {btn_siguiente.inner_html() if hasattr(btn_siguiente, 'inner_html') else 'N/A'}"
                )
                return False
            except Exception as e:
                self.logger.error(f"❌ ERROR PASO 2 - Error al hacer clic: {e}")
                self.logger.error(f"Tipo de error: {type(e).__name__}")
                return False

            # Paso 3: Esperar la carga de la página
            self.logger.info("📌 Paso 3: Esperando carga de la página después del clic")
            try:
                self.logger.debug("⏳ Esperando domcontentloaded...")
                page.wait_for_load_state("domcontentloaded", timeout=20000)
                self.logger.debug("✅ Estado de carga completado")
                self.logger.debug(f"URL después de la navegación: {page.url}")

            except PWTimeoutError as e:
                self.logger.warning(f"⚠️ Timeout esperando carga de página: {e}")
                self.logger.warning(
                    "⚠️ Continuando de todos modos, la página podría haber cargado parcialmente"
                )
            except Exception as e:
                self.logger.error(f"❌ ERROR PASO 3 - Error esperando carga: {e}")
                self.logger.error(f"Tipo de error: {type(e).__name__}")
                return False

            # Paso 4: Verificar mensaje de éxito
            self.logger.info("📌 Paso 4: Verificando mensaje de éxito")
            try:
                self.logger.debug(
                    "🔍 Buscando mensaje: 'Tus suscriptores se han importado con éxito'"
                )
                expect(
                    page.get_by_text("Tus suscriptores se han importado con éxito")
                ).to_be_visible(timeout=30000)
                self.logger.info("✅ Mensaje de éxito principal encontrado")
                self.logger.info("🎉 Suscriptores importados con éxito")
                return True

            except PWTimeoutError:
                self.logger.warning("⚠️ No se encontró el mensaje principal de éxito")
                self.logger.info(
                    "🔍 Intentando con mensaje alternativo: 'importado con éxito'"
                )

                try:
                    expect(page.get_by_text("importado con éxito")).to_be_visible(
                        timeout=10000
                    )
                    self.logger.info("✅ Mensaje de éxito alternativo encontrado")
                    self.logger.info(
                        "🎉 Suscriptores importados con éxito (mensaje alternativo)"
                    )
                    return True

                except PWTimeoutError:
                    self.logger.warning("⚠️ No se encontró ningún mensaje de éxito")
                    self.logger.warning(
                        "❌ No se pudo confirmar la importación de suscriptores"
                    )
                    self.logger.debug(f"URL final: {page.url}")
                    self.logger.debug(
                        "🔍 Contenido parcial de la página para debugging..."
                    )
                    try:
                        # Intentar capturar algún contenido para debugging
                        page_content = page.content()[:500]  # Primeros 500 caracteres
                        self.logger.debug(f"Contenido página: {page_content}")
                    except Exception:
                        self.logger.debug("No se pudo capturar contenido de página")
                    return False

                except Exception as e:
                    self.logger.error(
                        f"❌ ERROR PASO 4 - Error buscando mensaje alternativo: {e}"
                    )
                    self.logger.error(f"Tipo de error: {type(e).__name__}")
                    return False

            except Exception as e:
                self.logger.error(
                    f"❌ ERROR PASO 4 - Error inesperado verificando mensaje: {e}"
                )
                self.logger.error(f"Tipo de error: {type(e).__name__}")
                return False

        except Exception as e:
            self.logger.error(f"❌ ERROR GENERAL en finalizar_subida: {e}")
            self.logger.error(f"Tipo de error: {type(e).__name__}")
            self.logger.error(f"URL cuando ocurrió el error: {page.url}")

            # Intentar capturar más información de debugging
            try:
                self.logger.debug(
                    "🔍 Capturando información adicional para debugging..."
                )
                self.logger.debug(f"Título de la página: {page.title()}")
                self.logger.debug(f"URL actual: {page.url}")
                # Verificar si hay algún elemento que podría indicar el estado
                if page.locator("text=error").count() > 0:
                    self.logger.warning("⚠️ Se detectó la palabra 'error' en la página")
                if page.locator("text=fallo").count() > 0:
                    self.logger.warning("⚠️ Se detectó la palabra 'fallo' en la página")
            except Exception as debug_e:
                self.logger.debug(
                    f"No se pudo capturar información adicional: {debug_e}"
                )

            return False

    def subir_lista_completa(
        self,
        page: Page,
        config: ListUploadConfig,
        progress_callback: Optional[Callable[[ListUploadProgress], None]] = None,
    ) -> ListUploadResult:
        """
        Ejecuta el proceso completo de subida de lista

        Args:
            page: Página de Playwright
            config: Configuración de subida
            progress_callback: Callback opcional para reportar progreso

        Returns:
            ListUploadResult con el resultado del proceso
        """
        # Crear sesión
        session = ListUploadSession(
            session_id=f"list_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            config=config,
            status="active",
        )

        resultado = ListUploadResult(
            session_info=session,
            success=False,
            list_created=False,
            fields_mapped=0,
            subscribers_uploaded=False,
        )

        archivo_temporal = None

        try:
            # Etapa 1: Navegación (0-10%)
            if progress_callback:
                progreso = ListUploadProgress(
                    stage="navegando",
                    current_column=0,
                    total_columns=0,
                    mensaje="Navegando a la sección de listas",
                    porcentaje=5.0,
                )
                progress_callback(progreso)

            if not self.inicializar_navegacion_lista(page):
                session.add_error("No se pudo navegar a la sección de listas")
                session.complete_session(success=False)
                resultado.error_message = "Error navegando a la sección de listas"
                return resultado

            # Etapa 2: Creación de lista (10-30%)
            if progress_callback:
                progreso = ListUploadProgress(
                    stage="creando_lista",
                    current_column=0,
                    total_columns=0,
                    mensaje=f"Creando lista '{config.nombre_lista}'",
                    porcentaje=20.0,
                )
                progress_callback(progreso)

            if not self.crear_lista(page, config.nombre_lista):
                session.add_error("No se pudo crear la lista")
                session.complete_session(success=False)
                resultado.error_message = "Error creando la lista"
                return resultado

            resultado.list_created = True

            # Etapa 3: Generación y subida de archivo (30-50%)
            if progress_callback:
                progreso = ListUploadProgress(
                    stage="subiendo_archivo",
                    current_column=0,
                    total_columns=0,
                    mensaje="Generando y subiendo archivo CSV",
                    porcentaje=40.0,
                )
                progress_callback(progreso)

            archivo_temporal = self.generar_archivo_temporal_csv(
                config.archivo_path, config.hoja_nombre
            )

            if not self.subir_archivo(page, archivo_temporal):
                session.add_error("No se pudo subir el archivo")
                session.complete_session(success=False)
                resultado.error_message = "Error subiendo el archivo"
                return resultado

            # Etapa 4: Mapeo de columnas (50-90%)
            if progress_callback:
                progreso = ListUploadProgress(
                    stage="mapeando_campos",
                    current_column=0,
                    total_columns=len(config.columnas),
                    mensaje="Iniciando mapeo de campos",
                    porcentaje=60.0,
                )
                progress_callback(progreso)

            campos_mapeados = self.mapear_columnas(
                page, config.columnas, progress_callback
            )
            resultado.fields_mapped = campos_mapeados

            # Etapa 5: Finalización (90-100%)
            if progress_callback:
                progreso = ListUploadProgress(
                    stage="finalizando",
                    current_column=0,
                    total_columns=0,
                    mensaje="Finalizando subida",
                    porcentaje=95.0,
                )
                progress_callback(progreso)

            if not self.finalizar_subida(page):
                session.add_error("No se pudo finalizar la subida")
                session.complete_session(success=False)
                resultado.error_message = "Error finalizando la subida"
                return resultado

            resultado.subscribers_uploaded = True

            # Éxito completo
            session.complete_session(success=True)
            resultado.success = True

            self.logger.info(f"Lista '{config.nombre_lista}' subida exitosamente")

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error en subida de lista: {error_msg}")
            session.add_error(error_msg)
            session.complete_session(success=False)
            resultado.error_message = error_msg

        finally:
            # Limpiar archivo temporal
            if archivo_temporal and os.path.exists(archivo_temporal):
                try:
                    os.remove(archivo_temporal)
                    self.logger.debug(f"Archivo temporal eliminado: {archivo_temporal}")
                except Exception as e:
                    self.logger.warning(f"No se pudo eliminar archivo temporal: {e}")

        return resultado
