"""
Módulo para crear listas de suscriptores usando scraping (web automation)

Este módulo usa el endpoint de scraping para subir listas completas a Acumbamail
mediante automatización web con Playwright.
"""

from playwright.sync_api import sync_playwright
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional
import os
from pathlib import Path

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from .utils import (
    load_config,
    data_path,
    storage_state_path,
    notify,
    configurar_navegador,
    crear_contexto_navegador,
    get_timeouts,
)
from .autentificacion import login
from .infrastructure.scraping.endpoints.lista_upload import ListUploader
from .infrastructure.scraping.models.listas import (
    ListUploadConfig,
    ListUploadColumn,
    ListUploadProgress,
)
from .shared.logging.logger import get_logger
from .excel_helper import ExcelHelper


def listar_hojas(archivo: str) -> list[str]:
    """Devuelve la lista de hojas del archivo Excel"""
    return ExcelHelper.obtener_hojas(archivo)


def seleccionar_hoja_cli(archivo: str) -> str:
    """Selector por consola (fallback)"""
    hojas = listar_hojas(archivo)
    if not hojas:
        raise ValueError("El archivo no contiene hojas.")
    if len(hojas) == 1:
        print(f"Usando única hoja: {hojas[0]}")
        return hojas[0]
    print("\nHojas disponibles en el Excel:")
    for i, h in enumerate(hojas, 1):
        print(f"  {i}) {h}")
    while True:
        op = input(f"Selecciona la hoja (1-{len(hojas)}) [1]: ").strip()
        if op == "":
            return hojas[0]
        if op.isdigit():
            idx = int(op)
            if 1 <= idx <= len(hojas):
                return hojas[idx - 1]
        print("Opción inválida. Intenta nuevamente.")


def seleccionar_hoja_tk(archivo: str, master=None, multiple=False) -> Optional[list[str] | str]:
    """Ventana modal para elegir hoja. Devuelve nombre(s) o None."""
    try:
        hojas = listar_hojas(archivo)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron listar hojas:\n{e}")
        return None

    if not hojas:
        messagebox.showwarning("Excel", "El archivo no contiene hojas.")
        return None

    owns_root = False
    if master is None:
        master = tk.Tk()
        master.withdraw()
        owns_root = True

    result: dict[str, Optional[list[str] | str]] = {"val": None}

    win = tk.Toplevel(master)
    title = "Seleccionar hojas" if multiple else "Seleccionar hoja"
    win.title(title)
    win.resizable(False, False)
    win.grab_set()
    win.transient(master)
    win.geometry("820x520")

    label_text = "Selecciona las hojas a usar (puedes seleccionar múltiples):" if multiple else "Selecciona la hoja a usar:"
    tk.Label(win, text=label_text).pack(padx=12, pady=(12, 6), anchor="w")

    # Contenedor con scrollbars
    frame_lb = tk.Frame(win)
    frame_lb.pack(padx=12, fill="both", expand=True)
    frame_lb.rowconfigure(0, weight=1)
    frame_lb.columnconfigure(0, weight=1)

    # Configurar Listbox para selección múltiple si se solicita
    select_mode = tk.EXTENDED if multiple else tk.SINGLE
    lb = tk.Listbox(frame_lb, height=min(14, len(hojas)), exportselection=False, selectmode=select_mode)
    vsb = tk.Scrollbar(frame_lb, orient="vertical", command=lb.yview)
    hsb = tk.Scrollbar(frame_lb, orient="horizontal", command=lb.xview)
    lb.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    for h in hojas:
        lb.insert(tk.END, h)
    lb.selection_set(0)

    lb.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    # Contador de selección para modo múltiple
    if multiple:
        counter_label = tk.Label(win, text="0 hojas seleccionadas", font=("Arial", 10))
        counter_label.pack(pady=(6, 0))

        def update_counter():
            selected_count = len(lb.curselection())
            counter_label.config(text=f"{selected_count} hoja{'s' if selected_count != 1 else ''} seleccionada{'s' if selected_count != 1 else ''}")
            win.after(100, update_counter)
        update_counter()

    btns = tk.Frame(win)
    btns.pack(padx=12, pady=12, fill="x")

    def aceptar():
        try:
            selected_indices = lb.curselection()
            if multiple:
                if selected_indices:
                    result["val"] = [hojas[i] for i in selected_indices]
                else:
                    result["val"] = None
            else:
                if selected_indices:
                    result["val"] = hojas[selected_indices[0]]
                else:
                    result["val"] = None
        except Exception:
            result["val"] = None
        win.destroy()

    def cancelar():
        result["val"] = None
        win.destroy()

    tk.Button(btns, text="Cancelar", command=cancelar).pack(side="right")
    tk.Button(btns, text="Aceptar", command=aceptar).pack(side="right", padx=6)

    win.bind("<Return>", lambda e: aceptar())
    win.bind("<Escape>", lambda e: cancelar())

    win.wait_window()
    if owns_root:
        master.destroy()
    return result["val"]


def seleccionar_hoja(archivo: str) -> str:
    """Intenta UI; si no, cae a CLI"""
    try:
        import threading

        if threading.current_thread() is threading.main_thread():
            sel = seleccionar_hoja_tk(archivo)
            if sel and isinstance(sel, str):
                return sel
    except Exception:
        pass
    return seleccionar_hoja_cli(archivo)


def seleccionar_hojas_multiples(archivo: str, master=None) -> Optional[list[str]]:
    """Función específica para seleccionar múltiples hojas"""
    try:
        import threading
        if threading.current_thread() is threading.main_thread():
            sel = seleccionar_hoja_tk(archivo, master=master, multiple=True)
            if sel and isinstance(sel, list):
                return sel
    except Exception:
        pass

    # Fallback CLI para selección múltiple
    return seleccionar_hojas_cli_multiples(archivo)


def seleccionar_hojas_cli_multiples(archivo: str) -> list[str]:
    """Selector por consola para múltiples hojas"""
    hojas = listar_hojas(archivo)
    if not hojas:
        raise ValueError("El archivo no contiene hojas.")

    if len(hojas) == 1:
        print(f"Usando única hoja: {hojas[0]}")
        return [hojas[0]]

    print("\nHojas disponibles en el Excel:")
    for i, h in enumerate(hojas, 1):
        print(f"  {i}) {h}")

    print("\nSelecciona las hojas (ej: 1,3,5 o 1-5 o 'todas'):")

    while True:
        op = input("Hojas a procesar: ").strip().lower()

        if op == "todas":
            return hojas

        if "," in op:
            # Selección por coma: 1,3,5
            try:
                indices = [int(x.strip()) - 1 for x in op.split(",")]
                if all(0 <= idx < len(hojas) for idx in indices):
                    return [hojas[idx] for idx in indices]
            except Exception:
                pass

        if "-" in op:
            # Selección por rango: 1-5
            try:
                start, end = op.split("-")
                start_idx = int(start.strip()) - 1
                end_idx = int(end.strip()) - 1
                if 0 <= start_idx <= end_idx < len(hojas):
                    return hojas[start_idx:end_idx + 1]
            except Exception:
                pass

        # Selección simple: 1
        if op.isdigit():
            idx = int(op) - 1
            if 0 <= idx < len(hojas):
                return [hojas[idx]]

        print("Opción inválida. Intenta nuevamente.")


def seleccionar_archivo_excel(
    directorio_inicial: Optional[str] = None,
) -> Optional[str]:
    """
    Abre diálogo para seleccionar archivo Excel
    """
    root = tk.Tk()
    root.withdraw()

    if not directorio_inicial:
        directorio_inicial = data_path(".")

    archivo = filedialog.askopenfilename(
        title="Seleccionar archivo Excel para subir",
        initialdir=directorio_inicial,
        filetypes=[
            ("Archivos Excel", "*.xlsx"),
            ("Archivos Excel antiguos", "*.xls"),
            ("Todos los archivos", "*.*"),
        ],
    )

    root.destroy()
    return archivo if archivo else None


def main(nombre_hoja: Optional[str] = None, archivo_excel: Optional[str] = None, multiple: bool = False):
    """
    Función principal para subir lista usando scraping desde Listas.xlsx

    Args:
        nombre_hoja: Nombre de la hoja a usar (si None, se pregunta al usuario)
        archivo_excel: Ruta del archivo Excel (si None, usa data/Listas.xlsx por defecto)
        multiple: Si es True, permite procesar múltiples hojas
    """
    logger = get_logger()
    logger.info("=" * 70)
    if multiple:
        logger.info("🚀 INICIANDO SUBIDA MÚLTIPLE DE LISTAS CON SCRAPING")
    else:
        logger.info("🚀 INICIANDO SUBIDA DE LISTA CON SCRAPING")
    logger.info("=" * 70)

    # Cargar configuración
    config = load_config()
    url = config.get("url", "")
    url_base = config.get("url_base", "")
    headless = bool(config.get("headless", False))

    logger.info(f"⚙️  Configuración cargada:")
    logger.info(f"   • URL Base: {url_base}")
    logger.info(f"   • Modo headless: {headless}")

    # Usar Listas.xlsx por defecto
    if not archivo_excel:
        archivo_excel = data_path("Listas.xlsx")
        logger.info(f"📁 Usando archivo por defecto: Listas.xlsx")

    if not os.path.exists(archivo_excel):
        logger.error(f"❌ Archivo no encontrado: {archivo_excel}")
        logger.error(f"💡 Asegúrate de que existe el archivo data/Listas.xlsx")
        notify(
            "Error",
            f"Archivo no encontrado: Listas.xlsx\nDebes crear el archivo en la carpeta data/",
            "error",
        )
        return

    logger.info(f"✅ Archivo encontrado: {os.path.basename(archivo_excel)}")

    # Mostrar hojas disponibles
    try:
        hojas_disponibles = listar_hojas(archivo_excel)
        logger.info(f"📋 Hojas disponibles en el archivo ({len(hojas_disponibles)}):")
        for i, hoja in enumerate(hojas_disponibles, 1):
            logger.info(f"   {i}. {hoja}")
    except Exception as e:
        logger.error(f"❌ Error leyendo hojas del archivo: {e}")
        notify("Error", f"No se pudieron leer las hojas del archivo: {e}", "error")
        return

    # Determinar hojas a procesar
    hojas_a_procesar = []

    if multiple:
        # Seleccionar múltiples hojas
        if not nombre_hoja or isinstance(nombre_hoja, list) and not nombre_hoja:
            logger.info("")
            logger.info("🔍 Esperando selección de hojas múltiples...")
            hojas_seleccionadas = seleccionar_hojas_multiples(archivo_excel)
            if not hojas_seleccionadas:
                logger.error("❌ No se seleccionaron hojas")
                notify("Error", "No se seleccionaron hojas", "error")
                return
            hojas_a_procesar = hojas_seleccionadas
        elif isinstance(nombre_hoja, list):
            hojas_a_procesar = nombre_hoja
        else:
            hojas_a_procesar = [nombre_hoja]

        logger.info("")
        logger.info("=" * 70)
        logger.info(f"📄 HOJAS SELECCIONADAS: {len(hojas_a_procesar)}")
        logger.info("-" * 70)
        for i, hoja in enumerate(hojas_a_procesar, 1):
            logger.info(f"   {i}. {hoja}")
        logger.info("=" * 70)
    else:
        # Modo simple (compatibilidad hacia atrás)
        if not nombre_hoja:
            logger.info("")
            logger.info("🔍 Esperando selección de hoja...")
            nombre_hoja = seleccionar_hoja(archivo_excel)
            if not nombre_hoja:
                logger.error("❌ No se seleccionó ninguna hoja")
                notify("Error", "No se seleccionó ninguna hoja", "error")
                return
            hojas_a_procesar = [nombre_hoja]
        else:
            hojas_a_procesar = [nombre_hoja]

        logger.info("")
        logger.info("=" * 70)
        logger.info(f"📄 HOJA SELECCIONADA: {nombre_hoja}")
        logger.info("=" * 70)

    # Procesar cada hoja
    resultados = []
    uploader = ListUploader()

    for idx, nombre_hoja_actual in enumerate(hojas_a_procesar, 1):
        logger.info("")
        logger.info(f"📊 PROCESANDO HOJA {idx}/{len(hojas_a_procesar)}: {nombre_hoja_actual}")
        logger.info("-" * 70)

        # Cargar columnas del Excel
        columnas, _ = uploader.cargar_columnas_excel(archivo_excel, nombre_hoja_actual)

        if not columnas:
            logger.error(f"❌ No se pudieron cargar las columnas de la hoja '{nombre_hoja_actual}'")
            notify("Error", f"No se pudieron cargar las columnas de la hoja '{nombre_hoja_actual}'", "error")
            resultados.append({
                'hoja': nombre_hoja_actual,
                'success': False,
                'error': 'Error al cargar columnas'
            })
            continue

        # El nombre de la lista es la hoja seleccionada
        nombre_lista = nombre_hoja_actual

        logger.info(f"✅ Columnas detectadas: {len(columnas)}")
        logger.info("")
        logger.info("📋 Detalle de columnas a mapear:")
        for i, col in enumerate(columnas, 1):
            valor_muestra = (
                col.sample_value[:30] + "..."
                if len(col.sample_value) > 30
                else col.sample_value
            )
            logger.info(
                f"   {i:2}. {col.name:25} → {col.field_type:15} (ej: {valor_muestra})"
            )

        # Crear configuración de subida
        logger.info("")
        logger.info("⚙️  CONFIGURACIÓN DE SUBIDA")
        logger.info("-" * 70)
        upload_config = ListUploadConfig(
            nombre_lista=nombre_lista,
            archivo_path=archivo_excel,
            hoja_nombre=nombre_hoja_actual,
            columnas=columnas,
            timeout_seconds=60,
            wait_time_ms=2000,
        )
        logger.info(f"✅ Lista: '{nombre_lista}'")
        logger.info(f"✅ Columnas: {len(columnas)} campos a mapear")
        logger.info(f"✅ Timeout: {upload_config.timeout_seconds}s")

        # Callback de progreso
        def progress_callback(progress: ListUploadProgress):
            barra_progreso = "█" * int(progress.porcentaje / 5) + "░" * (
                20 - int(progress.porcentaje / 5)
            )
            logger.info(
                f"[{barra_progreso}] {progress.porcentaje:5.1f}% | {progress.stage:20} | {progress.mensaje}"
            )

        # Solo abrir navegador una vez para la primera hoja
        if idx == 1:
            logger.info("")
            logger.info("=" * 70)
            logger.info("🌐 INICIANDO NAVEGADOR")
            logger.info("=" * 70)

            with sync_playwright() as p:
                logger.info("🌐 Configurando navegador...")
                browser = configurar_navegador(p, headless)
                context = crear_contexto_navegador(browser, headless)
                page = context.new_page()
                logger.info("✅ Navegador configurado")

                try:
                    # Navegar y autenticar
                    logger.info("")
                    logger.info("🔐 AUTENTICACIÓN")
                    logger.info("-" * 70)
                    logger.info(f"🌐 Navegando a: {url_base}")
                    page.goto(url_base, timeout=60000)
                    logger.info(f"🌐 Navegando a: {url}")
                    page.goto(url, timeout=60000)

                    logger.info("🔑 Iniciando sesión...")
                    login(page, context)
                    logger.info("✅ Autenticación exitosa")

                    # Procesar la primera hoja
                    resultado = procesar_hoja_lista(page, uploader, upload_config, progress_callback, nombre_hoja_actual)
                    resultados.append(resultado)

                    # Procesar el resto de las hojas
                    for jdx, nombre_hoja_resto in enumerate(hojas_a_procesar[1:], 2):
                        logger.info("")
                        logger.info(f"📊 PROCESANDO HOJA {jdx}/{len(hojas_a_procesar)}: {nombre_hoja_resto}")
                        logger.info("-" * 70)

                        columnas_resto, _ = uploader.cargar_columnas_excel(archivo_excel, nombre_hoja_resto)
                        if columnas_resto:
                            upload_config_resto = ListUploadConfig(
                                nombre_lista=nombre_hoja_resto,
                                archivo_path=archivo_excel,
                                hoja_nombre=nombre_hoja_resto,
                                columnas=columnas_resto,
                                timeout_seconds=60,
                                wait_time_ms=2000,
                            )
                            resultado_resto = procesar_hoja_lista(page, uploader, upload_config_resto, progress_callback, nombre_hoja_resto)
                            resultados.append(resultado_resto)
                        else:
                            logger.error(f"❌ No se pudieron cargar las columnas de la hoja '{nombre_hoja_resto}'")
                            resultados.append({
                                'hoja': nombre_hoja_resto,
                                'success': False,
                                'error': 'Error al cargar columnas'
                            })

                    # Mostrar resumen final
                    mostrar_resumen_final(resultados, multiple)

                except Exception as e:
                    logger.error(f"❌ Error durante el proceso: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    notify("Error", f"Error durante el proceso: {e}", "error")

                finally:
                    logger.info("")
                    logger.info("🔒 Cerrando navegador...")
                    browser.close()
                    logger.info("✅ Navegador cerrado")

        # Si no es la primera hoja, continuamos con el flujo normal (esto se maneja arriba)
        break


def procesar_hoja_lista(page, uploader, upload_config, progress_callback, nombre_hoja):
    """Función auxiliar para procesar una hoja individual"""
    logger = get_logger()

    logger.info("")
    logger.info("=" * 70)
    logger.info(f"📤 SUBIDA DE LISTA: '{nombre_hoja}'")
    logger.info("=" * 70)

    resultado = uploader.subir_lista_completa(page, upload_config, progress_callback)

    # Mostrar resultado individual
    logger.info("")
    logger.info("=" * 70)
    if resultado.success:
        logger.info("✅ RESULTADO: ÉXITO")
        logger.info("=" * 70)
        logger.success(f"🎉 Lista '{nombre_hoja}' subida exitosamente")
        logger.info("")
        logger.info("📊 Resumen:")
        logger.info(f"   ✓ Lista creada: {resultado.list_created}")
        logger.info(f"   ✓ Suscriptores subidos: {resultado.subscribers_uploaded}")

        return {
            'hoja': nombre_hoja,
            'success': True,
            'subscribers_uploaded': resultado.subscribers_uploaded,
            'fields_mapped': resultado.fields_mapped
        }
    else:
        logger.info("❌ RESULTADO: ERROR")
        logger.info("=" * 70)
        logger.error(f"❌ Error subiendo lista '{nombre_hoja}': {resultado.error_message}")

        return {
            'hoja': nombre_hoja,
            'success': False,
            'error': resultado.error_message
        }


def mostrar_resumen_final(resultados, multiple):
    """Muestra el resumen final del procesamiento"""
    logger = get_logger()

    logger.info("")
    logger.info("=" * 70)
    if multiple:
        logger.info("🏁 RESUMEN FINAL - PROCESAMIENTO MÚLTIPLE")
    else:
        logger.info("🏁 PROCESO FINALIZADO")
    logger.info("=" * 70)

    exitosas = sum(1 for r in resultados if r['success'])
    fallidas = len(resultados) - exitosas

    if multiple:
        logger.info(f"📊 Total de hojas procesadas: {len(resultados)}")
        logger.info(f"✅ Exitosas: {exitosas}")
        logger.info(f"❌ Fallidas: {fallidas}")

        if fallidas > 0:
            logger.info("")
            logger.error("📋 Detalle de errores:")
            for resultado in resultados:
                if not resultado['success']:
                    logger.error(f"   • {resultado['hoja']}: {resultado['error']}")

        # Notificación resumida
        if fallidas == 0:
            notify(
                "Procesamiento completado",
                f"Se subieron exitosamente {exitosas} listas",
                "info"
            )
        else:
            notify(
                f"Procesamiento con errores ({exitosas}/{len(resultados)} exitosas)",
                f"{exitosas} listas subidas correctamente, {fallidas} con errores",
                "warning"
            )

    logger.info("")
    logger.info("=" * 70)


if __name__ == "__main__":
    # Verificar si se ejecuta en modo no interactivo
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Modo automático: selecciona la primera hoja
        archivo = data_path("Listas.xlsx")
        if os.path.exists(archivo):
            hojas = listar_hojas(archivo)
            if hojas:
                print(f"🔄 Modo automático: seleccionando primera hoja '{hojas[0]}'")
                main(nombre_hoja=hojas[0], archivo_excel=archivo)
            else:
                print("❌ No hay hojas en el archivo")
        else:
            print(f"❌ Archivo no encontrado: {archivo}")
    else:
        main()
