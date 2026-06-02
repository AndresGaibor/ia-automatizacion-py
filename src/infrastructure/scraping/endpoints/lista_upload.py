"""
Endpoint de scraping para subir/crear listas de suscriptores en Acumbamail.
Ahora usa POM (Page Object Model) para encapsular selectores.
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
from src.infrastructure.scraping.utils.field_types import field_type_label
from ....utils import get_timeouts
from ..pages.lists_page import PaginaListas


class SubidorListas:
    """Scraper para subir/crear listas de suscriptores usando web scraping con POM"""

    def __init__(self):
        self.logger = get_logger()

    def safe_interaction(
        self, lists_page: PaginaListas, action_description: str, action_callable: Callable[[], Any]
    ) -> Tuple[Optional[Any], bool]:
        """
        Wrapper para interacciones seguras con manejo robusto de errores.

        Args:
            lists_page: Instancia de PaginaListas (POM)
            action_description: Descripción de la acción para logging
            action_callable: Función callable que ejecuta la acción

        Returns:
            Tuple (resultado, exito): Resultado de la acción y booleano de éxito
        """
        page = lists_page.page
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
        self, lists_page: PaginaListas, selector_description: str, locator, timeout: int = 10000
    ) -> bool:
        """
        Espera a que un elemento esté visible y hace clic.

        Args:
            lists_page: Instancia de PaginaListas (POM)
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

    def inicializar_navegacion_lista(self, lists_page: PaginaListas) -> bool:
        """
        Navega a la sección de listas con espera optimizada usando POM.

        Args:
            lists_page: Instancia de PaginaListas (POM)

        Returns:
            True si la navegación fue exitosa
        """
        try:
            self.logger.info("Navegando a la sección de listas")
            return lists_page.navigate_to_lists()
        except Exception as e:
            self.logger.error(f"Error navegando a la sección de listas: {e}")
            return False

    def cargar_columnas_excel(
        self, archivo: str, hoja: str
    ) -> tuple[list[ListUploadColumn], list[str]]:
        """
        Carga columnas del Excel y obtiene valores de ejemplo.

        Returns:
            (columnas, segunda_fila): Lista de columnas con metadatos y valores de la segunda fila
        """
        try:
            with pd.ExcelFile(archivo, engine="openpyxl") as xls:
                df = pd.read_excel(xls, sheet_name=hoja, dtype=str).fillna("")

            columnas_nombres = [str(c) for c in df.columns.tolist()]

            if len(df) > 0:
                segunda_fila = [str(v) for v in df.iloc[0].tolist()]
            else:
                segunda_fila = [""] * len(columnas_nombres)

            columnas = []
            for idx, nombre in enumerate(
                columnas_nombres, start=1
            ):
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
        Genera un CSV temporal solo con la hoja indicada.

        Returns:
            Ruta del archivo temporal CSV
        """
        try:
            with pd.ExcelFile(archivo_excel, engine="openpyxl") as xls:
                df = pd.read_excel(xls, sheet_name=hoja, dtype=str).fillna("")

            tmp_path = os.path.join(
                tempfile.gettempdir(), f"lista_{uuid.uuid4().hex}.csv"
            )
            df.to_csv(tmp_path, index=False, encoding="utf-8-sig")

            self.logger.info(f"Archivo temporal CSV generado: {tmp_path}")
            return tmp_path
        except Exception as e:
            self.logger.error(f"Error generando CSV temporal: {e}")
            raise

    def crear_lista(self, lists_page: PaginaListas, nombre_lista: str) -> bool:
        """
        Crea una nueva lista en Acumbamail usando POM.

        Args:
            lists_page: Instancia de PaginaListas (POM)
            nombre_lista: Nombre de la lista a crear

        Returns:
            True si se creó exitosamente
        """
        try:
            self.logger.info(f"📝 Creando lista: '{nombre_lista}'")
            return lists_page.crear_lista(nombre_lista)
        except Exception as e:
            self.logger.error(f"❌ Error creando lista: {e}")
            return False

    def subir_archivo(self, lists_page: PaginaListas, archivo_csv: str) -> bool:
        """
        Sube el archivo CSV a la lista usando POM.

        Args:
            lists_page: Instancia de PaginaListas (POM)
            archivo_csv: Ruta al archivo CSV

        Returns:
            True si se subió exitosamente
        """
        try:
            self.logger.info("📤 Subiendo archivo CSV")
            return lists_page.subir_archivo(archivo_csv)
        except Exception as e:
            self.logger.error(f"❌ Error subiendo archivo: {e}")
            return False

    def mapear_columnas(
        self,
        lists_page: PaginaListas,
        columnas: list[ListUploadColumn],
        progress_callback: Optional[Callable[[ListUploadProgress], None]] = None,
    ) -> int:
        """
        Mapea las columnas del archivo subido a campos personalizados usando POM.

        Args:
            lists_page: Instancia de PaginaListas (POM)
            columnas: Lista de columnas a mapear
            progress_callback: Callback opcional para reportar progreso

        Returns:
            Número de campos mapeados exitosamente
        """
        page = lists_page.page
        campos_mapeados = 0
        total_columnas = len(columnas)

        try:
            self.logger.info("")
            self.logger.info(f"🔗 MAPEO DE COLUMNAS ({total_columnas} columnas)")
            self.logger.info("-" * 70)

            self.logger.info("🔍 Detectando columnas disponibles en la página...")
            columnas_disponibles = lists_page.detectar_columnas_disponibles(total_columnas)
            columnas_procesar = min(total_columnas, len(columnas_disponibles))

            columnas_a_mapear = 0
            indices_a_mapear = []

            for i, columna in enumerate(columnas):
                if columna.index != 1:
                    indices_a_mapear.append(i)
                    columnas_a_mapear += 1

            self.logger.info(
                f"📊 Total columnas: {columnas_procesar}, Email (index=1) ya mapeado, Columnas a mapear: {columnas_a_mapear}"
            )
            if columnas_a_mapear == 0:
                self.logger.info("✅ No hay columnas adicionales para mapear")
                return 1

            for loop_idx, columnas_idx in enumerate(indices_a_mapear):
                columna = columnas[columnas_idx]
                try:
                    if progress_callback:
                        progreso_actual = loop_idx
                        porcentaje_progreso = (progreso_actual / columnas_a_mapear * 30) if columnas_a_mapear > 0 else 0

                        progreso = ListUploadProgress(
                            stage="mapeando_campos",
                            current_column=progreso_actual + 1,
                            total_columns=columnas_a_mapear,
                            mensaje=f"Mapeando '{columna.name}'",
                            porcentaje=60.0 + porcentaje_progreso,
                        )
                        progress_callback(progreso)

                    if not lists_page.mapear_columna(columna):
                        self.logger.warning(f"   ⚠️ Fallo mapeando columna {columna.name}")
                        continue

                    campos_mapeados += 1

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
            total_campos_mapeados = campos_mapeados + 1 if campos_mapeados > 0 else 1
            self.logger.info(
                f"📊 RESULTADO DEL MAPEO: {total_campos_mapeados}/{total_columnas} campos exitosos (incluyendo email)"
            )
            return total_campos_mapeados

        except Exception as e:
            self.logger.error(f"❌ Error en mapeo de columnas: {e}")
            return campos_mapeados

    def finalizar_subida(self, lists_page: PaginaListas) -> bool:
        """
        Finaliza el proceso de subida usando POM.

        Args:
            lists_page: Instancia de PaginaListas (POM)

        Returns:
            True si se finalizó exitosamente
        """
        page = lists_page.page
        try:
            self.logger.info("🔄 Iniciando finalización de subida")
            self.logger.debug(f"URL actual: {page.url}")

            self.logger.info("📌 Paso 1: Localizando botón 'Siguiente'")
            if not lists_page.click_siguiente():
                self.logger.error("❌ ERROR PASO 1 - No se pudo localizar botón 'Siguiente'")
                return False

            self.logger.info("📌 Paso 2: Verificando mensaje de éxito")
            return lists_page.verificar_mensaje_exito()

        except Exception as e:
            self.logger.error(f"❌ ERROR GENERAL en finalizar_subida: {e}")
            self.logger.error(f"Tipo de error: {type(e).__name__}")
            self.logger.error(f"URL cuando ocurrió el error: {page.url}")
            try:
                if page.locator("text=error").count() > 0:
                    self.logger.warning("⚠️ Se detectó la palabra 'error' en la página")
                if page.locator("text=fallo").count() > 0:
                    self.logger.warning("⚠️ Se detectó la palabra 'fallo' en la página")
            except Exception:
                pass
            return False

    def subir_lista_completa(
        self,
        page: Page,
        config: ListUploadConfig,
        progress_callback: Optional[Callable[[ListUploadProgress], None]] = None,
        url_base: Optional[str] = None,
        url: Optional[str] = None,
    ) -> ListUploadResult:
        """
        Ejecuta el proceso completo de subida de lista usando POM.

        Args:
            page: Página de Playwright
            config: Configuración de subida
            progress_callback: Callback opcional para reportar progreso
            url_base: URL base (si no se provee, usa load_config)
            url: URL principal (si no se provee, usa load_config)

        Returns:
            ListUploadResult con el resultado del proceso
        """
        from ....utils import load_config

        if url_base is None or url is None:
            cfg = load_config()
            url_base = url_base or cfg.get("url_base", "")
            url = url or cfg.get("url", "")

        lists_page = PaginaListas(page, url_base, url)

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
            if progress_callback:
                progreso = ListUploadProgress(
                    stage="navegando",
                    current_column=0,
                    total_columns=0,
                    mensaje="Navegando a la sección de listas",
                    porcentaje=5.0,
                )
                progress_callback(progreso)

            if not self.inicializar_navegacion_lista(lists_page):
                session.add_error("No se pudo navegar a la sección de listas")
                session.complete_session(success=False)
                resultado.error_message = "Error navegando a la sección de listas"
                return resultado

            if progress_callback:
                progreso = ListUploadProgress(
                    stage="creando_lista",
                    current_column=0,
                    total_columns=0,
                    mensaje=f"Creando lista '{config.nombre_lista}'",
                    porcentaje=20.0,
                )
                progress_callback(progreso)

            if not self.crear_lista(lists_page, config.nombre_lista):
                session.add_error("No se pudo crear la lista")
                session.complete_session(success=False)
                resultado.error_message = "Error creando la lista"
                return resultado

            resultado.list_created = True

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

            if not self.subir_archivo(lists_page, archivo_temporal):
                session.add_error("No se pudo subir el archivo")
                session.complete_session(success=False)
                resultado.error_message = "Error subiendo el archivo"
                return resultado

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
                lists_page, config.columnas, progress_callback
            )
            resultado.fields_mapped = campos_mapeados

            if progress_callback:
                progreso = ListUploadProgress(
                    stage="finalizando",
                    current_column=0,
                    total_columns=0,
                    mensaje="Finalizando subida",
                    porcentaje=95.0,
                )
                progress_callback(progreso)

            if not self.finalizar_subida(lists_page):
                session.add_error("No se pudo finalizar la subida")
                session.complete_session(success=False)
                resultado.error_message = "Error finalizando la subida"
                return resultado

            resultado.subscribers_uploaded = True

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
            if archivo_temporal and os.path.exists(archivo_temporal):
                try:
                    os.remove(archivo_temporal)
                    self.logger.debug(f"Archivo temporal eliminado: {archivo_temporal}")
                except Exception as e:
                    self.logger.warning(f"No se pudo eliminar archivo temporal: {e}")

        return resultado

ListUploader = SubidorListas
