import tkinter as tk
from tkinter import messagebox, ttk
import os
import pandas as pd
import importlib
import threading
from src.shared.utils.legacy_utils import load_config, data_path, storage_state_path, notify
from src.config_window import show_config_window
from src.config_validator import check_config_or_show_dialog
from src.shared.logging.logger import PerformanceLogger, get_logger
from src.presentation.work_runner import start_worker
from src.presentation.progress_window import ProgressWindow

logger: PerformanceLogger = get_logger()

DEFAULTS = {
    'url': 'https://acumbamail.com/app/newsletter/',
    'url_base': 'https://acumbamail.com',
    'user': 'usuario@correo.com',
    'password': 'clave',
    'headless': False,
    'timeouts': {
        'navigation': 60,
        'element': 15,
        'upload': 120,
        'default': 30
    },
    'api': {
        'base_url': 'https://acumbamail.com/api/1/',
        'api_key': ''
    },
    'lista': {
        'sender_email': 'usuario@correo.com',
        'company': 'Tu Empresa',
        'country': 'España',
        'city': 'Tu Ciudad',
        'address': 'Tu Dirección',
        'phone': '+34 000 000 000'
    }
}

obtener_listas_running = False


def validar_configuracion() -> tuple[bool, str]:
    logger.info("🔍 Validando configuración")
    config = load_config()
    if not config.get("user") or config.get("user") == "usuario@correo.com":
        logger.warning("❌ Configuración inválida: Usuario no configurado", user=config.get("user"))
        return False, "Error: Usuario no configurado. Edite config.yaml con sus credenciales de Acumbamail."
    if not config.get("password") or config.get("password") == "clave":
        logger.warning("❌ Configuración inválida: Contraseña no configurada", user=config.get("user"))
        return False, "Error: Contraseña no configurada. Edite config.yaml con su contraseña de Acumbamail."
    api_config = config.get("api", {})
    if not api_config.get("api_key"):
        logger.warning("⚠️ API Key no configurada", user=config.get("user"))
        return False, "Advertencia: API Key no configurada. Algunas funciones pueden no funcionar. Configure api.api_key en config.yaml."
    logger.success("✅ Configuración válida", user=config.get("user"))
    return True, "Configuración válida"


def validar_archivo_busqueda() -> tuple[bool, str, int]:
    archivo = data_path("Busqueda.xlsx")
    if not os.path.exists(archivo):
        return False, "Error: No existe el archivo Busqueda.xlsx", 0
    try:
        df = pd.read_excel(archivo)
        if 'Buscar' not in df.columns:
            return False, "Error: El archivo Busqueda.xlsx no tiene la columna 'Buscar'", 0
        marcados = df[df['Buscar'].isin(['x', 'X'])].shape[0]
        if marcados == 0:
            return False, "Advertencia: No hay elementos marcados con 'x' en el archivo Busqueda.xlsx", 0
        return True, f"{marcados} elementos marcados para procesar", marcados
    except Exception as e:
        return False, f"Error leyendo Busqueda.xlsx: {e}", 0


def validar_archivo_busqueda_listas() -> tuple[bool, str, int]:
    archivo = data_path("Busqueda_Listas.xlsx")
    if not os.path.exists(archivo):
        return False, "Error: No existe el archivo Busqueda_Listas.xlsx", 0
    try:
        df = pd.read_excel(archivo)
        if 'Buscar' not in df.columns:
            return False, "Error: El archivo Busqueda_Listas.xlsx no tiene la columna 'Buscar'", 0
        marcados = df[df['Buscar'].isin(['x', 'X'])].shape[0]
        if marcados == 0:
            return False, "Advertencia: No hay listas marcadas con 'x' en el archivo Busqueda_Listas.xlsx", 0
        return True, f"{marcados} listas marcadas para procesar", marcados
    except Exception as e:
        return False, f"Error leyendo Busqueda_Listas.xlsx: {e}", 0


def validar_archivo_segmentos() -> tuple[bool, str, int]:
    archivo = data_path("Segmentos.xlsx")
    if not os.path.exists(archivo):
        return False, "Error: No existe el archivo Segmentos.xlsx", 0
    try:
        df = pd.read_excel(archivo)
        required_columns = ['NOMBRE LISTA', 'NOMBRE SEGMENTO']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"Error: Faltan columnas en Segmentos.xlsx: {', '.join(missing_columns)}", 0
        filas = len(df)
        if filas == 0:
            return False, "Advertencia: El archivo Segmentos.xlsx está vacío", 0
        return True, f"{filas} segmentos definidos", filas
    except Exception as e:
        return False, f"Error leyendo Segmentos.xlsx: {e}", 0


def configuracion():
    load_config(DEFAULTS)


def archivo_busqueda():
    archivo = data_path("Busqueda.xlsx")
    if not os.path.exists(archivo):
        df = pd.DataFrame(columns=['Buscar', 'Nombre', 'Tipo', 'Fecha envío', 'Listas', 'Emails', 'Abiertos', 'Clics'])
        df.to_excel(archivo, index=False)
        logger.success("✅ Archivo de búsqueda creado", archivo=archivo)
    else:
        logger.info("✅ Archivo de búsqueda ya existe", archivo=archivo)


def archivo_busqueda_listas():
    archivo = data_path("Busqueda_Listas.xlsx")
    if not os.path.exists(archivo):
        df = pd.DataFrame(columns=['Buscar', 'NOMBRE LISTA', 'SUSCRIPTORES', 'CREACION'])
        df.to_excel(archivo, index=False)
        logger.success("✅ Archivo de búsqueda de listas creado", archivo=archivo)
    else:
        logger.info("✅ Archivo de búsqueda de listas ya existe", archivo=archivo)


def archivo_segmentos():
    archivo = data_path("Segmentos.xlsx")
    if not os.path.exists(archivo):
        df = pd.DataFrame(columns=['CREACION SEGMENTO', 'NOMBRE LISTA', 'NOMBRE SEGMENTO'])
        df.to_excel(archivo, index=False)
        logger.success("✅ Archivo de segmentos creado", archivo=archivo)
    else:
        logger.info("✅ Archivo de segmentos ya existe", archivo=archivo)


def limpiar_sesion():
    logger.info("🚪 Limpiando sesión guardada")
    try:
        path = storage_state_path()
        if not os.path.exists(path):
            messagebox.showinfo("Sesión", "No hay sesión guardada.")
            return
        if not messagebox.askyesno("Confirmar", "¿Eliminar la sesión actual?"):
            return
        os.remove(path)
        logger.success("✅ Sesión eliminada exitosamente", path=path)
        messagebox.showinfo("Sesión", "Sesión eliminada. Se pedirá login en el próximo inicio.")
    except Exception as e:
        logger.error(f"No se pudo limpiar la sesión: {e}", error=str(e))
        messagebox.showerror("Error", f"No se pudo limpiar la sesión: {e}")


def run_listar_campanias(btn):
    logger.info("🚀 Iniciando proceso de listado de campañas")

    def worker():
        if not check_config_or_show_dialog(root):
            return
        import src.listar_campanias as m
        importlib.reload(m)
        m.main()

    start_worker(btn, root, worker, on_success="Listado de campañas finalizado con éxito",
                 on_error=lambda e: f"Error al listar campañas: {e}")


def run_obtener_suscriptores(btn):
    logger.info("🚀 Iniciando proceso de obtención de suscriptores")

    def worker():
        if not check_config_or_show_dialog(root):
            return
        valid_busqueda, message_busqueda, marcados = validar_archivo_busqueda()
        if not valid_busqueda:
            root.after(0, lambda: notify("Error de Archivo", message_busqueda, "warning"))
            return
        import src.demo as m
        importlib.reload(m)
        m.main()

    def on_error(e):
        msg = str(e)
        if "Error en campaña" in msg:
            return f"La campaña seleccionada no está disponible o fue eliminada: {msg}"
        return f"Error al obtener suscriptores: {msg}"

    start_worker(btn, root, worker, on_success="Extracción de suscriptores finalizada con éxito",
                 on_error=on_error)


def run_crear_lista(btn):
    logger.info("🚀 Iniciando proceso de creación de lista(s) con scraping")
    if not check_config_or_show_dialog(root):
        return
    import src.crear_lista_scraping as m
    archivo_excel = data_path("Listas.xlsx")
    if not os.path.exists(archivo_excel):
        logger.error(f"❌ Archivo no encontrado: {archivo_excel}")
        messagebox.showerror("Error", "Archivo no encontrado: Listas.xlsx\nDebes crear el archivo en la carpeta data/")
        return
    try:
        hojas = m.listar_hojas(archivo_excel)
        if not hojas:
            messagebox.showerror("Error", "El archivo Listas.xlsx no contiene hojas")
            return
    except Exception as e:
        messagebox.showerror("Error", f"No se pudieron leer las hojas del archivo: {e}")
        return
    hojas_seleccionadas = m.seleccionar_hoja_tk(archivo_excel, master=root, multiple=True)
    if not hojas_seleccionadas:
        logger.info("↩️ Cancelado por el usuario - no se seleccionaron hojas")
        return
    if isinstance(hojas_seleccionadas, str):
        hojas_seleccionadas = [hojas_seleccionadas]
    logger.info(f"📄 Hojas seleccionadas: {len(hojas_seleccionadas)}")

    def worker():
        m.main(nombre_hoja= hojas_seleccionadas, archivo_excel=archivo_excel, multiple=True)

    msg = f"{len(hojas_seleccionadas)} listas procesadas" if len(hojas_seleccionadas) > 1 else "Lista de suscriptores subida con éxito"
    start_worker(btn, root, worker, on_success=msg,
                 on_error=lambda e: f"Error al crear lista(s): {e}")


def run_obtener_listas(btn):
    global obtener_listas_running
    logger.info("🚀 Iniciando proceso de obtención de listas")
    if not check_config_or_show_dialog(root):
        obtener_listas_running = False
        return

    progress = ProgressWindow(root, "Obteniendo Listas")

    def worker():
        if not check_config_or_show_dialog(root):
            return
        import src.obtener_listas as m
        importlib.reload(m)

        def progress_callback(msg: str):
            if msg.startswith('__ESTIMATED_TIME__:'):
                try:
                    seconds = int(msg.split(':', 1)[1])
                except Exception:
                    seconds = 60
                root.after(0, lambda: (progress.show(), setattr(progress, '_estimated', max(seconds, 60))))
            else:
                root.after(0, lambda: progress.update_message(msg))

        m.main(progress_callback=progress_callback)

        try:
            archivo = data_path("Busqueda_Listas.xlsx")
            df_after = pd.read_excel(archivo)
            filas = len(df_after)
            logger.success(f"✅ Obtención de listas completada: {filas} filas guardadas", archivo=archivo, filas=filas)
            root.after(0, lambda: notify("Completado", f"Obtención de listas finalizada: {filas} filas guardadas", "info"))
        except Exception:
            pass

    def done():
        progress.close()
        obtener_listas_running = False

    start_worker(btn, root, worker, on_success=None,
                 on_error=lambda e: f"Error al obtener listas: {e}",
                 finally_hook=done)


def run_descargar_suscriptores(btn):
    logger.info("🚀 Iniciando proceso de descarga de suscriptores")

    def worker():
        if not check_config_or_show_dialog(root):
            return
        valid_listas, message_listas, marcadas = validar_archivo_busqueda_listas()
        if not valid_listas:
            root.after(0, lambda: notify("Error de Archivo", message_listas, "warning"))
            return
        import src.descargar_suscriptores as m
        importlib.reload(m)
        m.main()

    start_worker(btn, root, worker, on_success="Descarga de suscriptores finalizada con éxito",
                 on_error=lambda e: f"Error al descargar suscriptores: {e}")


def run_eliminar_listas(btn):
    logger.info("🚀 Iniciando proceso de eliminación de listas")
    if not check_config_or_show_dialog(root):
        return
    import src.eliminar_listas as m
    importlib.reload(m)
    valid_listas, message_listas, marcadas = m.validar_archivo_busqueda_listas()
    if not valid_listas:
        notify("Error de Archivo", message_listas, "warning")
        return
    if not messagebox.askyesno("Confirmar eliminación", f"Vas a eliminar {marcadas} listas en Acumbamail. ¿Continuar?"):
        logger.info("↩️ Eliminación cancelada por el usuario")
        return

    def worker():
        exitosas, fallidas, mensaje = m.eliminar_listas_marcadas()
        tipo_notif = "info" if not fallidas else "warning"
        root.after(0, lambda: notify("Resultado Eliminación", mensaje, tipo_notif))

    start_worker(btn, root, worker, on_success=None,
                 on_error=lambda e: f"Error al eliminar listas: {e}")


def run_mapear_segmentos(btn):
    logger.info("🚀 Iniciando proceso de mapeo de segmentos")

    def worker():
        valid, message = validar_configuracion()
        if not valid:
            root.after(0, lambda: notify("Error de Configuración", message, "error"))
            return
        valid_segmentos, message_segmentos, segmentos_count = validar_archivo_segmentos()
        if not valid_segmentos:
            root.after(0, lambda: notify("Error de Archivo", message_segmentos, "error"))
            return
        listas_dir = os.path.join(os.path.dirname(data_path("dummy")), "listas")
        if not os.path.exists(listas_dir):
            os.makedirs(listas_dir)
            root.after(0, lambda: notify("Info",
                "Se creó la carpeta 'data/listas'. Las listas se crearán automáticamente en Acumbamail.", "info"))
        import src.mapeo_segmentos as m
        importlib.reload(m)
        resultado = m.mapear_segmentos_completo()
        if "error" in resultado:
            root.after(0, lambda: notify("Error", f"Error en mapeo: {resultado['error']}", "error"))
            return
        total = len(resultado.get('listas_procesadas', [])) + len(resultado.get('listas_fallidas', []))
        exitosas = len(resultado.get('listas_procesadas', []))
        fallidas = len(resultado.get('listas_fallidas', []))
        mensaje = "Procesamiento de segmentos completado:\n\n"
        mensaje += f"Listas procesadas: {exitosas}\n"
        mensaje += f"Listas fallidas: {fallidas}\n"
        mensaje += f"Total: {total}"
        if resultado.get('listas_procesadas'):
            mensaje += "\n\nListas exitosas:\n"
            for lista in resultado['listas_procesadas']:
                mensaje += f"• {lista}\n"
        if resultado.get('listas_fallidas'):
            mensaje += "\nListas fallidas:\n"
            for lista in resultado['listas_fallidas']:
                mensaje += f"• {lista}\n"
            mensaje += "\nSugerencias:\n"
            mensaje += "- Verifique que los datos en Segmentos.xlsx coincidan con los datos reales\n"
            mensaje += "- Revise que las condiciones de segmentación sean correctas\n"
            mensaje += "- Consulte los logs para más detalles sobre errores específicos"
        tipo = "info" if exitosas > 0 else "warning"
        root.after(0, lambda: notify("Procesamiento Completado" if exitosas > 0 else "Procesamiento Incompleto", mensaje, tipo))

    start_worker(btn, root, worker, on_success=None,
                 on_error=lambda e: f"Error durante el procesamiento: {e}")


if __name__ == "__main__":
    logger.info("🚀 Iniciando aplicación de automatización Acumbamail")
    configuracion()
    archivo_busqueda()
    archivo_busqueda_listas()
    archivo_segmentos()

    logger.info("🎨 Inicializando interfaz gráfica")
    root = tk.Tk()
    root.title("Automatización Acumbamail")
    root.geometry("450x700")

    main_canvas = tk.Canvas(root, highlightthickness=0)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=main_canvas.yview)
    scrollable_frame = tk.Frame(main_canvas)
    scrollable_frame.bind("<Configure>", lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")))
    main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    main_canvas.configure(yscrollcommand=scrollbar.set)
    main_canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
    main_canvas.bind_all("<Button-4>", lambda e: main_canvas.yview_scroll(-1, "units"))
    main_canvas.bind_all("<Button-5>", lambda e: main_canvas.yview_scroll(1, "units"))

    frame_campanias = tk.LabelFrame(scrollable_frame, text="Campañas", font=("Arial", 12, "bold"), pady=5)
    frame_campanias.pack(pady=12, fill="x", padx=25)

    btn_listar = tk.Button(frame_campanias, text="Listar campañas", font=("Arial", 14), height=2,
                           command=lambda: run_listar_campanias(btn_listar))
    btn_listar.pack(pady=8, fill="x", padx=15)

    btn_obtener = tk.Button(frame_campanias, text="Obtener suscriptores de campañas", font=("Arial", 14), height=2,
                            command=lambda: run_obtener_suscriptores(btn_obtener))
    btn_obtener.pack(pady=8, fill="x", padx=15)

    frame_listas = tk.LabelFrame(scrollable_frame, text="Listas", font=("Arial", 12, "bold"), pady=5)
    frame_listas.pack(pady=12, fill="x", padx=25)

    def on_click_obtener_listas():
        global obtener_listas_running
        if obtener_listas_running:
            notify("En curso", "La operación de obtención de listas ya se está ejecutando.", "warning")
            return
        obtener_listas_running = True
        btn_obtener_listas.config(state=tk.DISABLED)
        root.config(cursor="watch")
        run_obtener_listas(btn_obtener_listas)

    btn_obtener_listas = tk.Button(frame_listas, text="Obtener listas", font=("Arial", 14), height=2,
                                   command=on_click_obtener_listas)
    btn_obtener_listas.pack(pady=8, fill="x", padx=15)

    btn_descargar = tk.Button(frame_listas, text="Descargar lista de suscriptores", font=("Arial", 14), height=2,
                              command=lambda: run_descargar_suscriptores(btn_descargar))
    btn_descargar.pack(pady=8, fill="x", padx=15)

    btn_eliminar = tk.Button(frame_listas, text="Eliminar listas marcadas", font=("Arial", 14), height=2,
                             command=lambda: run_eliminar_listas(btn_eliminar), bg="#F44336", fg="white")
    btn_eliminar.pack(pady=8, fill="x", padx=15)

    btn_crear = tk.Button(frame_listas, text="Subir lista(s) de suscriptores", font=("Arial", 14), height=2,
                          command=lambda: run_crear_lista(btn_crear))
    btn_crear.pack(pady=8, fill="x", padx=15)

    btn_mapear = tk.Button(frame_listas, text="Procesar segmentos", font=("Arial", 14), height=2,
                           command=lambda: run_mapear_segmentos(btn_mapear))
    btn_mapear.pack(pady=8, fill="x", padx=15)

    frame_config = tk.LabelFrame(scrollable_frame, text="Configuración", font=("Arial", 12, "bold"), pady=5)
    frame_config.pack(pady=12, fill="x", padx=25)

    btn_config = tk.Button(frame_config, text="⚙️ Configurar Credenciales", font=("Arial", 14), height=2,
                           command=lambda: show_config_window(root), bg="#4CAF50", fg="white")
    btn_config.pack(pady=8, fill="x", padx=15)

    btn_clean = tk.Button(frame_config, text="Limpiar sesión actual", font=("Arial", 14), height=2,
                          command=limpiar_sesion)
    btn_clean.pack(pady=8, fill="x", padx=15)

    root.mainloop()
