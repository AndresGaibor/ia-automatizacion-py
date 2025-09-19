"""
Módulo mejorado de crear_lista con logging avanzado
Wrapper que añade logging comprehensivo a todas las funciones principales
"""

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page
from .utils import cargar_terminos_busqueda, crear_contexto_navegador, configurar_navegador, navegar_a_reportes, navegar_siguiente_pagina, obtener_total_paginas, load_config, data_path, storage_state_path, notify, get_timeouts, safe_goto
from .autentificacion import login
from .tipo_campo import field_type_label
import pandas as pd
import os
import threading
import tkinter as tk
from tkinter import messagebox
import tempfile
import uuid
import time
from .logger import get_logger as get_old_logger
from .enhanced_logger import get_crear_lista_logger, get_main_logger, log_operation, log_errors

# Importar funciones originales del módulo original
from .crear_lista import (
    listar_hojas as _listar_hojas_orig,
    _seleccionar_hoja_cli as _seleccionar_hoja_cli_orig,
    seleccionar_hoja_tk as _seleccionar_hoja_tk_orig,
    crear_archivo_temporal_con_datos as _crear_archivo_temporal_orig,
    procesar_fila_usuario as _procesar_fila_usuario_orig,
    crear_listas_desde_excel as _crear_listas_desde_excel_orig,
    _esperar_despues_de_anadir as _esperar_despues_de_anadir_orig,
    _click_aniadir_robusto as _click_aniadir_robusto_orig,
    _cerrar_popup_si_presente as _cerrar_popup_si_presente_orig,
    main as _main_orig
)

# Logger específico para crear lista
logger = get_crear_lista_logger()

@log_operation("listar_hojas_excel", "crear_lista")
def listar_hojas(archivo: str) -> list[str]:
    """Versión mejorada con logging de listar_hojas"""
    logger.log_file_operation("Analizando", archivo)

    try:
        hojas = _listar_hojas_orig(archivo)
        logger.log_data_extraction("hojas Excel", len(hojas), archivo,
                                 context={"sheet_names": hojas})
        return hojas
    except Exception as e:
        logger.error(f"Error listando hojas de {archivo}", error=e,
                    context={"file_path": archivo})
        raise

@log_operation("seleccion_hoja_cli", "crear_lista")
def seleccionar_hoja_cli(archivo: str, multiple=False) -> str | list[str]:
    """Versión mejorada con logging de _seleccionar_hoja_cli"""
    logger.info(f"Iniciando selección CLI de hojas (multiple={multiple})",
               context={"file_path": archivo, "multiple_selection": multiple})

    try:
        resultado = _seleccionar_hoja_cli_orig(archivo, multiple)

        if isinstance(resultado, list):
            logger.info(f"✅ Seleccionadas {len(resultado)} hojas: {', '.join(resultado)}",
                       context={"selected_sheets": resultado, "selection_count": len(resultado)})
        else:
            logger.info(f"✅ Seleccionada hoja: {resultado}",
                       context={"selected_sheet": resultado})

        return resultado
    except Exception as e:
        logger.error("Error en selección CLI de hojas", error=e,
                    context={"file_path": archivo, "multiple": multiple})
        raise

@log_operation("seleccion_hoja_gui", "crear_lista")
def seleccionar_hoja_tk(archivo: str, master=None, multiple=False):
    """Versión mejorada con logging de seleccionar_hoja_tk"""
    logger.info(f"Iniciando selección GUI de hojas (multiple={multiple})",
               context={"file_path": archivo, "multiple_selection": multiple, "has_master": master is not None})

    try:
        resultado = _seleccionar_hoja_tk_orig(archivo, master, multiple)

        if resultado is None:
            logger.warning("Selección GUI cancelada por el usuario")
        elif isinstance(resultado, list):
            logger.info(f"✅ GUI: Seleccionadas {len(resultado)} hojas",
                       context={"selected_sheets": resultado, "selection_count": len(resultado)})
        else:
            logger.info(f"✅ GUI: Seleccionada hoja: {resultado}",
                       context={"selected_sheet": resultado})

        return resultado
    except Exception as e:
        logger.error("Error en selección GUI de hojas", error=e,
                    context={"file_path": archivo, "multiple": multiple})
        raise

@log_operation("crear_archivo_temporal", "crear_lista")
def crear_archivo_temporal_con_datos(datos_usuarios: list[dict], nombre_hoja: str) -> str:
    """Versión mejorada con logging de crear_archivo_temporal_con_datos"""
    logger.info(f"Creando archivo temporal para hoja: {nombre_hoja}",
               context={"sheet_name": nombre_hoja, "user_count": len(datos_usuarios)})

    try:
        archivo_temporal = _crear_archivo_temporal_orig(datos_usuarios, nombre_hoja)

        # Obtener tamaño del archivo
        size = os.path.getsize(archivo_temporal) if os.path.exists(archivo_temporal) else 0

        logger.log_file_operation("Creado", archivo_temporal, size,
                                 context={"sheet_name": nombre_hoja, "user_count": len(datos_usuarios)})

        return archivo_temporal
    except Exception as e:
        logger.error(f"Error creando archivo temporal para {nombre_hoja}", error=e,
                    context={"sheet_name": nombre_hoja, "user_count": len(datos_usuarios)})
        raise

@log_operation("procesar_fila_usuario", "crear_lista")
def procesar_fila_usuario(page: Page, fila: dict, archivo_temporal: str, nombre_lista: str, progress_callback=None):
    """Versión mejorada con logging de procesar_fila_usuario"""
    email = fila.get('email', 'N/A')
    logger.info(f"Procesando usuario: {email}",
               context={"email": email, "list_name": nombre_lista})

    try:
        resultado = _procesar_fila_usuario_orig(page, fila, archivo_temporal, nombre_lista, progress_callback)

        logger.info(f"✅ Usuario procesado exitosamente: {email}",
                   context={"email": email, "list_name": nombre_lista, "success": True})

        return resultado
    except Exception as e:
        logger.error(f"Error procesando usuario {email}", error=e,
                    context={"email": email, "list_name": nombre_lista, "temp_file": archivo_temporal})
        raise

@log_operation("crear_listas_completo", "crear_lista")
def crear_listas_desde_excel(archivo_excel: str, hojas_seleccionadas: list[str], progress_callback=None, headless: bool = True):
    """Versión mejorada con logging de crear_listas_desde_excel"""
    logger.info(f"Iniciando creación de listas desde Excel: {archivo_excel}",
               context={
                   "file_path": archivo_excel,
                   "selected_sheets": hojas_seleccionadas,
                   "sheet_count": len(hojas_seleccionadas),
                   "headless_mode": headless
               })

    start_time = time.time()

    try:
        with logger.operation("crear_listas_excel_completo") as op:
            op.log_progress(f"Iniciando procesamiento de {len(hojas_seleccionadas)} hojas")

            resultado = _crear_listas_desde_excel_orig(archivo_excel, hojas_seleccionadas, progress_callback, headless)

            duration = time.time() - start_time
            logger.log_performance_metric("total_creation_time", duration * 1000, "ms",
                                        context={
                                            "sheets_processed": len(hojas_seleccionadas),
                                            "success": True
                                        })

            logger.info(f"✅ Creación de listas completada en {duration:.2f}s",
                       context={
                           "total_duration": duration,
                           "sheets_count": len(hojas_seleccionadas),
                           "success": True
                       })

            return resultado

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Error en creación de listas después de {duration:.2f}s", error=e,
                    context={
                        "file_path": archivo_excel,
                        "selected_sheets": hojas_seleccionadas,
                        "duration": duration,
                        "headless_mode": headless
                    })
        raise

@log_operation("esperar_post_anadir", "crear_lista")
def esperar_despues_de_anadir(page: Page, timeout_seg: int = 15) -> bool:
    """Versión mejorada con logging de _esperar_despues_de_anadir"""
    logger.info(f"Esperando confirmación post-añadir (timeout: {timeout_seg}s)",
               context={"timeout_seconds": timeout_seg})

    try:
        resultado = _esperar_despues_de_anadir_orig(page, timeout_seg)

        if resultado:
            logger.info("✅ Confirmación post-añadir detectada")
        else:
            logger.warning("❌ Timeout esperando confirmación post-añadir")

        return resultado
    except Exception as e:
        logger.error("Error esperando confirmación post-añadir", error=e,
                    context={"timeout_seconds": timeout_seg})
        raise

@log_operation("click_anadir_archivo", "crear_lista")
def click_aniadir_robusto(page: Page) -> bool:
    """Versión mejorada con logging de _click_aniadir_robusto"""
    logger.log_browser_action("Haciendo clic en botón Añadir")

    try:
        resultado = _click_aniadir_robusto_orig(page)

        if resultado:
            logger.info("✅ Clic en Añadir exitoso")
        else:
            logger.warning("❌ Clic en Añadir falló")

        return resultado
    except Exception as e:
        logger.error("Error haciendo clic en botón Añadir", error=e)
        raise

@log_operation("cerrar_popup", "crear_lista")
def cerrar_popup_si_presente(page: Page):
    """Versión mejorada con logging de _cerrar_popup_si_presente"""
    logger.log_browser_action("Verificando y cerrando popups si están presentes")

    try:
        _cerrar_popup_si_presente_orig(page)
        logger.debug("✅ Verificación de popups completada")
    except Exception as e:
        logger.warning("Error cerrando popup", error=e)
        # No re-lanzar la excepción ya que cerrar popup es opcional

@log_operation("main_crear_lista", "crear_lista")
def main():
    """Función principal mejorada con logging comprehensivo"""
    logger.info("🚀 Iniciando aplicación Crear Lista")

    try:
        with logger.operation("aplicacion_crear_lista_completa") as op:
            op.log_progress("Inicializando aplicación")

            resultado = _main_orig()

            logger.info("✅ Aplicación Crear Lista finalizada exitosamente")
            return resultado

    except KeyboardInterrupt:
        logger.info("🛑 Aplicación interrumpida por el usuario")
        raise
    except Exception as e:
        logger.error("❌ Error crítico en aplicación Crear Lista", error=e)
        raise
    finally:
        logger.info("🏁 Finalizando aplicación Crear Lista")

# Funciones de utilidad adicionales para logging específico
def log_excel_analysis(archivo: str, hojas: list[str], filas_por_hoja: dict[str, int]):
    """Log específico para análisis de archivos Excel"""
    total_filas = sum(filas_por_hoja.values())
    logger.info(f"📊 Análisis de Excel completado: {archivo}",
               context={
                   "file_path": archivo,
                   "total_sheets": len(hojas),
                   "sheet_names": hojas,
                   "rows_per_sheet": filas_por_hoja,
                   "total_rows": total_filas
               })

def log_browser_setup(headless: bool, user_data_dir: str = None):
    """Log específico para configuración del navegador"""
    logger.info(f"🌐 Configurando navegador (headless={headless})",
               context={
                   "headless_mode": headless,
                   "user_data_dir": user_data_dir,
                   "browser_type": "chromium"
               })

def log_list_creation_summary(hojas_procesadas: list[str], exitosas: list[str], fallidas: list[str]):
    """Log resumen de creación de listas"""
    logger.info(f"📋 Resumen de creación de listas:",
               context={
                   "total_sheets": len(hojas_procesadas),
                   "successful_sheets": exitosas,
                   "failed_sheets": fallidas,
                   "success_count": len(exitosas),
                   "failure_count": len(fallidas),
                   "success_rate": len(exitosas) / len(hojas_procesadas) * 100 if hojas_procesadas else 0
               })

if __name__ == "__main__":
    main()