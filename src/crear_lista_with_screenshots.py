"""
Ejemplo de como integrar screenshots automáticos en crear_lista.py
Muestra el patrón de uso del nuevo sistema de logging con capturas
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
from .enhanced_logger import get_crear_lista_logger, get_main_logger, log_operation

# Logger específico para crear lista con screenshots
logger = get_crear_lista_logger()

def procesar_fila_usuario_con_screenshots(page: Page, fila: dict, archivo_temporal: str, nombre_lista: str, progress_callback=None):
    """
    Versión mejorada de procesar_fila_usuario que captura screenshots en errores
    """
    email = fila.get('email', 'N/A')

    # Usar contexto con página para screenshots automáticos
    with logger.operation("procesar_usuario", {"email": email, "lista": nombre_lista}, page) as op:
        try:
            op.log_progress(f"Iniciando procesamiento de {email}")

            # Navegar al formulario de creación de lista
            safe_goto(page, "/listas/crear")

            # Llenar el nombre de la lista
            nombre_field = page.get_by_placeholder("Nombre de la lista")
            nombre_field.fill(nombre_lista)

            op.log_progress("Formulario de lista llenado")

            # Subir archivo CSV
            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(archivo_temporal)

            op.log_progress("Archivo CSV subido")

            # Hacer clic en botón añadir
            btn_anadir = page.get_by_role("button", name="Añadir")
            btn_anadir.click()

            op.log_progress("Procesando archivo...")

            # Esperar resultados
            page.wait_for_load_state("networkidle", timeout=30000)

            # Verificar si hay errores en la página
            if verificar_errores_en_pagina(page):
                # Capturar screenshot manual del error específico
                screenshot_path = logger.capture_screenshot(
                    page,
                    f"error_procesamiento_{email}",
                    context={"email": email, "lista": nombre_lista}
                )

                # Log del error con información del screenshot
                logger.log_operation_failure(
                    "procesamiento_usuario",
                    f"Error procesando {email} - ver screenshot",
                    page,
                    context={
                        "email": email,
                        "lista": nombre_lista,
                        "screenshot": screenshot_path
                    }
                )

                raise RuntimeError(f"Error en procesamiento de {email}")

            op.log_progress("Usuario procesado exitosamente", 100, 100)

            if progress_callback:
                progress_callback(f"✅ Usuario {email} procesado")

        except Exception as e:
            # El screenshot se captura automáticamente por el contexto
            if progress_callback:
                progress_callback(f"❌ Error procesando {email}: {e}")
            raise

def verificar_errores_en_pagina(page: Page) -> bool:
    """
    Verifica si hay errores visibles en la página
    """
    # Buscar elementos que indiquen errores
    error_selectors = [
        '.error',
        '.alert-danger',
        '[class*="error"]',
        'text="Error"',
        'text="error"',
        'text="El proceso ha concluido pero con algunos errores"'  # Error específico de la imagen
    ]

    for selector in error_selectors:
        try:
            if page.locator(selector).count() > 0:
                return True
        except Exception:
            continue

    return False

def crear_lista_con_manejo_errores(archivo_excel: str, hojas_seleccionadas: list[str], progress_callback=None, headless: bool = True):
    """
    Versión de crear_lista con manejo comprehensivo de errores y screenshots
    """
    with logger.operation("crear_listas_completo", {
        "archivo": archivo_excel,
        "hojas": hojas_seleccionadas,
        "headless": headless
    }) as op:

        with sync_playwright() as p:
            # Configurar navegador
            browser = configurar_navegador(p, headless)
            context = crear_contexto_navegador(browser, headless)
            page = context.new_page()

            try:
                # Login con página disponible para screenshots
                with logger.operation("login_process", {"archivo": archivo_excel}, page) as login_op:
                    config = load_config()
                    safe_goto(page, config.get("url", ""))
                    login(page)
                    login_op.log_progress("Login completado")

                # Procesar cada hoja
                for i, hoja in enumerate(hojas_seleccionadas):
                    op.log_progress(f"Procesando hoja {i+1}/{len(hojas_seleccionadas)}: {hoja}")

                    try:
                        # Leer datos de la hoja
                        df = pd.read_excel(archivo_excel, sheet_name=hoja, engine="openpyxl")

                        if df.empty:
                            logger.warning(f"Hoja {hoja} está vacía, saltando")
                            continue

                        # Crear archivo temporal
                        datos_usuarios = df.to_dict('records')
                        archivo_temporal = crear_archivo_temporal_con_datos(datos_usuarios, hoja)

                        try:
                            # Procesar con screenshots automáticos en errores
                            procesar_fila_usuario_con_screenshots(
                                page,
                                {"email": "multiple_users"},
                                archivo_temporal,
                                hoja,
                                progress_callback
                            )

                            op.log_progress(f"Hoja {hoja} completada exitosamente")

                        except Exception as e:
                            # Screenshot se captura automáticamente
                            logger.log_operation_failure(
                                "procesar_hoja",
                                f"Error en hoja {hoja}: {e}",
                                page,
                                context={"hoja": hoja, "archivo": archivo_excel}
                            )

                            if progress_callback:
                                progress_callback(f"❌ Error en hoja {hoja}: {e}")

                        finally:
                            # Limpiar archivo temporal
                            if os.path.exists(archivo_temporal):
                                os.unlink(archivo_temporal)

                    except Exception as e:
                        logger.error(f"Error leyendo hoja {hoja}", error=e, page=page,
                                   context={"hoja": hoja, "archivo": archivo_excel})

                        if progress_callback:
                            progress_callback(f"❌ Error leyendo hoja {hoja}: {e}")

                op.log_progress("Todas las hojas procesadas", len(hojas_seleccionadas), len(hojas_seleccionadas))

            except Exception as e:
                # Screenshot automático del error general
                logger.critical("Error crítico en proceso de creación", error=e, page=page,
                              context={"archivo": archivo_excel, "hojas": hojas_seleccionadas})
                raise

            finally:
                # Cerrar navegador
                try:
                    context.close()
                    browser.close()
                except Exception:
                    pass

def crear_archivo_temporal_con_datos(datos_usuarios: list[dict], nombre_hoja: str) -> str:
    """
    Crea archivo temporal CSV con los datos de usuarios
    """
    timestamp = int(time.time())
    nombre_archivo = f"temp_lista_{nombre_hoja}_{timestamp}.csv"
    archivo_temporal = os.path.join(tempfile.gettempdir(), nombre_archivo)

    # Convertir a DataFrame y guardar como CSV
    df = pd.DataFrame(datos_usuarios)
    df.to_csv(archivo_temporal, index=False, encoding='utf-8')

    return archivo_temporal

# Función de ejemplo para demostrar uso manual de screenshots
def ejemplo_captura_manual():
    """
    Ejemplo de como capturar screenshots manualmente en operaciones específicas
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Ir a una página de prueba
            page.goto("https://example.com")

            # Capturar screenshot de estado inicial
            screenshot_path = logger.capture_screenshot(
                page,
                "estado_inicial",
                context={"url": "example.com", "step": "inicio"}
            )
            print(f"Screenshot inicial guardado en: {screenshot_path}")

            # Simular una operación que puede fallar
            try:
                # Buscar un elemento que no existe
                page.locator("elemento_inexistente").click(timeout=5000)
            except Exception as e:
                # Log de error con screenshot automático
                logger.log_browser_error(
                    "click_elemento_inexistente",
                    e,
                    page,
                    context={"elemento": "elemento_inexistente"}
                )

                # Capturar screenshot adicional del estado de error
                error_screenshot = logger.capture_screenshot(
                    page,
                    "estado_error_click",
                    context={"elemento": "elemento_inexistente", "error": str(e)}
                )
                print(f"Screenshot de error guardado en: {error_screenshot}")

        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    # Ejemplo de uso
    print("🧪 Probando sistema de screenshots...")
    ejemplo_captura_manual()
    print("✅ Prueba completada - revisa la carpeta data/logs/screenshots/")