import tkinter as tk
from tkinter import messagebox, ttk
import os
import pandas as pd
import importlib
import threading
import time
from src.shared.utils.legacy_utils import load_config, data_path, storage_state_path, notify
from src.config_window import show_config_window
from src.config_validator import check_config_or_show_dialog
from src.shared.logging.legacy_logger import get_logger

# Initialize logger
logger = get_logger()

# Config por defecto (usada para crear y para "Restaurar")
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

# Variables globales para contadores de progreso
progress_window = None
progress_var = None
progress_label = None
time_label = None
start_time = None
# Lock flag to prevent concurrent obtener_listas runs
obtener_listas_running = False

def validar_configuracion() -> tuple[bool, str]:
    """Valida que la configuración esté completa"""
    logger.info("🔍 Validando configuración")
    config = load_config()
    
    # Validar credenciales básicas
    if not config.get("user") or config.get("user") == "usuario@correo.com":
        logger.warning("❌ Configuración inválida: Usuario no configurado", user=config.get("user"))
        return False, "Error: Usuario no configurado. Edite config.yaml con sus credenciales de Acumbamail."
    
    if not config.get("password") or config.get("password") == "clave":
        logger.warning("❌ Configuración inválida: Contraseña no configurada", user=config.get("user"))
        return False, "Error: Contraseña no configurada. Edite config.yaml con su contraseña de Acumbamail."
    
    # Validar API key si se necesita
    api_config = config.get("api", {})
    if not api_config.get("api_key"):
        logger.warning("⚠️ API Key no configurada", user=config.get("user"))
        return False, "Advertencia: API Key no configurada. Algunas funciones pueden no funcionar. Configure api.api_key en config.yaml."
    
    logger.success("✅ Configuración válida", user=config.get("user"))
    return True, "Configuración válida"

def validar_archivo_busqueda() -> tuple[bool, str, int]:
    """Valida el archivo de búsqueda y cuenta elementos marcados"""
    archivo = data_path("Busqueda.xlsx")
    logger.info("🔍 Validando archivo de búsqueda", archivo=archivo)
    if not os.path.exists(archivo):
        logger.error("❌ Archivo de búsqueda no encontrado", archivo=archivo)
        return False, "Error: No existe el archivo Busqueda.xlsx", 0
    
    try:
        logger.info("📊 Leyendo archivo de búsqueda", archivo=archivo)
        df = pd.read_excel(archivo)
        if 'Buscar' not in df.columns:
            logger.error("❌ Columna 'Buscar' no encontrada en archivo", archivo=archivo)
            return False, "Error: El archivo Busqueda.xlsx no tiene la columna 'Buscar'", 0
        
        marcados = df[df['Buscar'].isin(['x', 'X'])].shape[0]
        if marcados == 0:
            logger.warning("⚠️ No hay elementos marcados en archivo", archivo=archivo)
            return False, "Advertencia: No hay elementos marcados con 'x' en el archivo Busqueda.xlsx", 0
        
        logger.success(f"✅ Archivo de búsqueda válido: {marcados} elementos marcados", archivo=archivo, elementos_marcados=marcados)
        return True, f"{marcados} elementos marcados para procesar", marcados
    except Exception as e:
        logger.error(f"❌ Error leyendo archivo de búsqueda: {e}", archivo=archivo, error=str(e))
        return False, f"Error leyendo Busqueda.xlsx: {e}", 0

def validar_archivo_busqueda_listas() -> tuple[bool, str, int]:
    """Valida el archivo de búsqueda de listas y cuenta elementos marcados"""
    archivo = data_path("Busqueda_Listas.xlsx")
    logger.info("🔍 Validando archivo de búsqueda de listas", archivo=archivo)
    if not os.path.exists(archivo):
        logger.error("❌ Archivo de búsqueda de listas no encontrado", archivo=archivo)
        return False, "Error: No existe el archivo Busqueda_Listas.xlsx", 0
    
    try:
        logger.info("📊 Leyendo archivo de búsqueda de listas", archivo=archivo)
        df = pd.read_excel(archivo)
        if 'Buscar' not in df.columns:
            logger.error("❌ Columna 'Buscar' no encontrada en archivo de listas", archivo=archivo)
            return False, "Error: El archivo Busqueda_Listas.xlsx no tiene la columna 'Buscar'", 0
        
        marcados = df[df['Buscar'].isin(['x', 'X'])].shape[0]
        if marcados == 0:
            logger.warning("⚠️ No hay listas marcadas en archivo", archivo=archivo)
            return False, "Advertencia: No hay listas marcadas con 'x' en el archivo Busqueda_Listas.xlsx", 0
        
        logger.success(f"✅ Archivo de búsqueda de listas válido: {marcados} listas marcadas", archivo=archivo, listas_marcadas=marcados)
        return True, f"{marcados} listas marcadas para procesar", marcados
    except Exception as e:
        logger.error(f"❌ Error leyendo archivo de búsqueda de listas: {e}", archivo=archivo, error=str(e))
        return False, f"Error leyendo Busqueda_Listas.xlsx: {e}", 0

def validar_archivo_segmentos() -> tuple[bool, str, int]:
    """Valida el archivo de segmentos"""
    archivo = data_path("Segmentos.xlsx")
    logger.info("🔍 Validando archivo de segmentos", archivo=archivo)
    if not os.path.exists(archivo):
        logger.error("❌ Archivo de segmentos no encontrado", archivo=archivo)
        return False, "Error: No existe el archivo Segmentos.xlsx", 0
    
    try:
        logger.info("📊 Leyendo archivo de segmentos", archivo=archivo)
        df = pd.read_excel(archivo)
        required_columns = ['NOMBRE LISTA', 'NOMBRE SEGMENTO']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error("❌ Columnas requeridas faltantes en archivo de segmentos", archivo=archivo, missing_columns=missing_columns)
            return False, f"Error: Faltan columnas en Segmentos.xlsx: {', '.join(missing_columns)}", 0
        
        filas = len(df)
        if filas == 0:
            logger.warning("⚠️ Archivo de segmentos está vacío", archivo=archivo)
            return False, "Advertencia: El archivo Segmentos.xlsx está vacío", 0
        
        logger.success(f"✅ Archivo de segmentos válido: {filas} segmentos definidos", archivo=archivo, segmentos_definidos=filas)
        return True, f"{filas} segmentos definidos", filas
    except Exception as e:
        logger.error(f"❌ Error leyendo archivo de segmentos: {e}", archivo=archivo, error=str(e))
        return False, f"Error leyendo Segmentos.xlsx: {e}", 0

def mostrar_contador_progreso(titulo: str, tiempo_estimado: int):
    """Muestra una ventana con contador de progreso y tiempo estimado"""
    global progress_window, progress_var, progress_label, time_label, start_time
    
    start_time = time.time()
    
    progress_window = tk.Toplevel(root)
    progress_window.title(titulo)
    progress_window.geometry("400x150")
    progress_window.resizable(False, False)
    
    # Centrar la ventana
    progress_window.transient(root)
    progress_window.grab_set()
    
    # Frame principal
    main_frame = tk.Frame(progress_window, padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Etiqueta de estado
    progress_label = tk.Label(main_frame, text="Iniciando...", font=("Arial", 10))
    progress_label.pack(pady=(0, 10))
    
    # Barra de progreso indeterminada
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')
    progress_bar.pack(fill=tk.X, pady=(0, 10))
    progress_bar.start(10)
    
    # Etiqueta de tiempo
    time_label = tk.Label(main_frame, text=f"Tiempo estimado: {tiempo_estimado//60}m {tiempo_estimado%60}s", 
                         font=("Arial", 9), fg="gray")
    time_label.pack()
    
    # Actualizar tiempo transcurrido
    def actualizar_tiempo():
        if progress_window and progress_window.winfo_exists() and start_time is not None:
            elapsed = int(time.time() - start_time)
            if time_label and time_label.winfo_exists():
                time_label.config(text=f"Tiempo estimado: {tiempo_estimado//60}m {tiempo_estimado%60}s | Transcurrido: {elapsed//60}m {elapsed%60}s")
            progress_window.after(1000, actualizar_tiempo)
    
    actualizar_tiempo()

def actualizar_progreso(mensaje: str):
    """Actualiza el mensaje de progreso"""
    global progress_label
    if progress_label and progress_label.winfo_exists():
        progress_label.config(text=mensaje)

def cerrar_contador_progreso():
    """Cierra la ventana de progreso"""
    global progress_window
    if progress_window and progress_window.winfo_exists():
        progress_window.destroy()
        progress_window = None

def configuracion():
    # Crea config.yaml si no existe; no sobrescribe si ya existe
    load_config(DEFAULTS)

def archivo_busqueda():
    archivo = data_path("Busqueda.xlsx")
    logger.info("📁 Verificando archivo de búsqueda", archivo=archivo)
    if not os.path.exists(archivo):
        logger.info("🆕 Creando archivo de búsqueda", archivo=archivo)
        df = pd.DataFrame(columns=['Buscar', 'Nombre', 'Tipo', 'Fecha envío', 'Listas', 'Emails', 'Abiertos', 'Clics'])
        df.to_excel(archivo, index=False)
        logger.success("✅ Archivo de búsqueda creado", archivo=archivo)
    else:
        logger.info("✅ Archivo de búsqueda ya existe", archivo=archivo)


def archivo_busqueda_listas():
	archivo = data_path("Busqueda_Listas.xlsx")
	logger.info("📁 Verificando archivo de búsqueda de listas", archivo=archivo)
	if not os.path.exists(archivo):
		logger.info("🆕 Creando archivo de búsqueda de listas", archivo=archivo)
		df = pd.DataFrame(columns=['Buscar', 'NOMBRE LISTA', 'SUSCRIPTORES', 'CREACION'])
		df.to_excel(archivo, index=False)
		logger.success("✅ Archivo de búsqueda de listas creado", archivo=archivo)
	else:
		logger.info("✅ Archivo de búsqueda de listas ya existe", archivo=archivo)

def archivo_segmentos():
	archivo = data_path("Segmentos.xlsx")
	logger.info("📁 Verificando archivo de segmentos", archivo=archivo)
	if not os.path.exists(archivo):
		logger.info("🆕 Creando archivo de segmentos", archivo=archivo)
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
            logger.info("📭 No hay sesión guardada para limpiar", path=path)
            messagebox.showinfo("Sesión", "No hay sesión guardada.")
            return
        if not messagebox.askyesno("Confirmar", "¿Eliminar la sesión actual?"):
            logger.info("↩️ Cancelado por el usuario")
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
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                logger.warning("❌ Configuración no válida, cancelando proceso")
                return

            logger.info("📥 Importando módulo listar_campanias")
            import src.listar_campanias as m
            importlib.reload(m)

            logger.info("⚙️ Ejecutando función principal de listado de campañas")
            m.main()
            logger.success("✅ Listado de campañas completado exitosamente")
            root.after(0, lambda: notify("Completado", "Listado de campañas finalizado con éxito", "info"))

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error al listar campañas: {error_msg}", error=error_msg)
            root.after(0, lambda: notify("Error", f"Error al listar campañas: {error_msg}", "error"))
        finally:
            logger.info("🔄 Restaurando estado de la interfaz")
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))

    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    logger.info("🧵 Iniciando hilo de trabajo para listado de campañas")
    threading.Thread(target=worker, daemon=True).start()

def run_obtener_suscriptores(btn):
    logger.info("🚀 Iniciando proceso de obtención de suscriptores")
    def worker():
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                logger.warning("❌ Configuración no válida, cancelando proceso")
                return
            
            # Validar archivo de búsqueda
            logger.info("🔍 Validando archivo de búsqueda")
            valid_busqueda, message_busqueda, marcados = validar_archivo_busqueda()
            if not valid_busqueda:
                logger.warning(f"❌ Archivo de búsqueda inválido: {message_busqueda}")
                root.after(0, lambda: notify("Error de Archivo", message_busqueda, "warning"))
                return
            
            # Mostrar contador (estimado 5-15 minutos dependiendo de campañas)
            # tiempo_estimado = min(marcados * 30, 900)  # 30 segundos por campaña, máximo 15 minutos
            # root.after(0, lambda: mostrar_contador_progreso("Obteniendo Suscriptores", tiempo_estimado))
            # root.after(0, lambda: actualizar_progreso("Conectando a Acumbamail"))
            
            logger.info(f"📥 Importando módulo demo - Campañas a procesar: {marcados}")
            import src.demo as m
            importlib.reload(m)
            
            # root.after(0, lambda: actualizar_progreso("Procesando campañas y extrayendo suscriptores"))
            logger.info("⚙️ Ejecutando función principal de extracción de suscriptores")
            m.main()
            
            # root.after(0, lambda: cerrar_contador_progreso())
            logger.success("✅ Extracción de suscriptores completada exitosamente")
            root.after(0, lambda: notify("Completado", "Extracción de suscriptores finalizada con éxito", "info"))
            
        except Exception as e:
            logger.error(f"❌ Error al obtener suscriptores: {e}", error=str(e))
            # root.after(0, lambda: cerrar_contador_progreso())
            error_msg = str(e)
            if "Error en campaña" in error_msg:
                root.after(0, lambda: notify("Error de Campaña", f"La campaña seleccionada no está disponible o fue eliminada: {error_msg}", "error"))
            else:
                root.after(0, lambda: notify("Error", f"Error al obtener suscriptores: {error_msg}", "error"))
        finally:
            logger.info("🔄 Restaurando estado de la interfaz")
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
    
    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    logger.info("🧵 Iniciando hilo de trabajo para obtención de suscriptores")
    threading.Thread(target=worker, daemon=True).start()

def run_crear_lista(btn):
    """
    Nueva implementación mejorada que:
    1. Permite seleccionar archivo Excel
    2. Automáticamente usa la hoja "Datos"
    3. Nombre de lista = nombre del archivo
    4. Valida diferencias con hoja "Cambios"
    5. Sube automáticamente sin pedir confirmación
    """
    logger.info("🚀 Iniciando proceso de creación de lista")
    def worker():
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                logger.warning("❌ Configuración no válida, cancelando proceso")
                return
            
            # Verificar que hay configuración de lista
            logger.info("🔍 Validando configuración de lista")
            config = load_config()
            lista_config = config.get('lista', {})
            if not lista_config.get('sender_email') or lista_config.get('sender_email') == 'usuario@correo.com':
                logger.error("❌ Configuración de lista incompleta", sender_email=lista_config.get('sender_email'))
                root.after(0, lambda: notify("Error de Configuración", 
                    "Error: Falta configurar los datos de la lista (sender_email, company, etc.) en config.yaml", "error"))
                return
            
            # Mostrar información previa
            logger.info("📤 Preparando subida de lista de suscriptores")
            root.after(0, lambda: notify("Iniciando", "Preparando subida de lista de suscriptores", "info"))
            
            # Mostrar contador (estimado 2-5 minutos dependiendo del tamaño del archivo)
            # root.after(0, lambda: mostrar_contador_progreso("Subiendo Lista", 180))  # 3 minutos estimado
            # root.after(0, lambda: actualizar_progreso("Seleccionando archivo Excel"))
            
            logger.info("📥 Importando módulo crear_lista_mejorado")
            import src.crear_lista_mejorado as m
            importlib.reload(m)
            
            # root.after(0, lambda: actualizar_progreso("Validando datos y subiendo a Acumbamail"))
            # Ejecutar creación automática
            logger.info("⚙️ Ejecutando función principal de creación de lista")
            m.main_automatico()
            
            # root.after(0, lambda: cerrar_contador_progreso())
            logger.success("✅ Creación de lista completada exitosamente")
            root.after(0, lambda: notify("Completado", "Lista de suscriptores subida con éxito", "info"))
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error al crear lista: {error_msg}", error=error_msg)
            # root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: notify("Error", f"Error al crear lista: {error_msg}", "error"))
        finally:
            logger.info("🔄 Restaurando estado de la interfaz")
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))

    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    logger.info("🧵 Iniciando hilo de trabajo para creación de lista")
    threading.Thread(target=worker, daemon=True).start()

def run_obtener_listas(btn):
    logger.info("🚀 Iniciando proceso de obtención de listas")
    def worker():
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                logger.warning("❌ Configuración no válida, cancelando proceso")
                return

            # Mostrar información previa
            logger.info("📤 Preparando obtención de todas las listas vía API")
            # root.after(0, lambda: notify("Iniciando", "Obteniendo todas las listas vía API", "info"))

            # Mostrar contador (estimado 1-3 minutos)
            # root.after(0, lambda: mostrar_contador_progreso("Obteniendo Listas", 180))
            # root.after(0, lambda: actualizar_progreso("Conectando a Acumbamail API"))

            logger.info("📥 Importando módulo obtener_listas")
            import src.obtener_listas as m
            importlib.reload(m)

            # running flag already set by button handler

            # Preparar ventana/barras de progreso lazily desde el callback
            progress_shown = {'shown': False}

            def progress_callback(msg: str):
                # special estimated time message
                if msg.startswith('__ESTIMATED_TIME__:'):
                    try:
                        seconds = int(msg.split(':', 1)[1])
                    except Exception:
                        seconds = 0
                    # show progress window on main thread
                    def show():
                        nonlocal progress_shown
                        if not progress_shown['shown']:
                            mostrar_contador_progreso("Obteniendo Listas", max(seconds, 60))
                            progress_shown['shown'] = True
                    root.after(0, show)
                    return

                # Otherwise update progress label
                root.after(0, lambda: actualizar_progreso(msg))

            # Ejecutar con callback
            logger.info("⚙️ Ejecutando función principal de obtención de listas")
            m.main(progress_callback=progress_callback)

            # Leer excel resultante y notificar ruta + filas guardadas para evitar confusiones
            try:
                import pandas as _pd
                archivo = data_path("Busqueda_Listas.xlsx")
                df_after = _pd.read_excel(archivo)
                filas = len(df_after)
                logger.success(f"✅ Obtención de listas completada: {filas} filas guardadas", archivo=archivo, filas=filas)
                root.after(0, lambda: notify("Completado", f"Obtención de listas finalizada: {filas} filas guardadas en {archivo}", "info"))
            except Exception as e:
                logger.success("✅ Obtención de listas completada exitosamente", error=str(e))
                root.after(0, lambda: notify("Completado", "Obtención de listas finalizada con éxito", "info"))

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error al obtener listas: {error_msg}", error=error_msg)
            # root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: notify("Error", f"Error al obtener listas: {error_msg}", "error"))
        finally:
            # Cerrar ventana de progreso si está abierta
            logger.info("🔄 Restaurando estado de la interfaz")
            root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
            # release running flag
            try:
                global obtener_listas_running
                obtener_listas_running = False
            except Exception:
                pass

    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    logger.info("🧵 Iniciando hilo de trabajo para obtención de listas")
    threading.Thread(target=worker, daemon=True).start()


def run_descargar_suscriptores(btn):
    logger.info("🚀 Iniciando proceso de descarga de suscriptores")
    def worker():
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                logger.warning("❌ Configuración no válida, cancelando proceso")
                return
            
            # Validar archivo de búsqueda de listas
            logger.info("🔍 Validando archivo de búsqueda de listas")
            valid_listas, message_listas, marcadas = validar_archivo_busqueda_listas()
            if not valid_listas:
                logger.warning(f"❌ Archivo de búsqueda de listas inválido: {message_listas}")
                root.after(0, lambda: notify("Error de Archivo", message_listas, "warning"))
                return
            
            # Mostrar información previa
            logger.info(f"📥 Iniciando descarga de suscriptores - Listas a procesar: {marcadas}")
            root.after(0, lambda: notify("Iniciando", f"Descargando suscriptores de {marcadas} listas", "info"))
            
            # Mostrar contador (estimado 2-10 minutos dependiendo del tamaño de las listas)
            # tiempo_estimado = min(marcadas * 60, 600)  # 1 minuto por lista, máximo 10 minutos
            # root.after(0, lambda: mostrar_contador_progreso("Descargando Suscriptores", tiempo_estimado))
            # root.after(0, lambda: actualizar_progreso("Conectando a Acumbamail"))
            
            logger.info("📥 Importando módulo descargar_suscriptores")
            import src.descargar_suscriptores as m
            importlib.reload(m)
            
            # root.after(0, lambda: actualizar_progreso("Descargando datos de suscriptores"))
            logger.info("⚙️ Ejecutando función principal de descarga de suscriptores")
            m.main()
            
            # root.after(0, lambda: cerrar_contador_progreso())
            logger.success("✅ Descarga de suscriptores completada exitosamente")
            root.after(0, lambda: notify("Completado", "Descarga de suscriptores finalizada con éxito", "info"))
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error al descargar suscriptores: {error_msg}", error=error_msg)
            # root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: notify("Error", f"Error al descargar suscriptores: {error_msg}", "error"))
        finally:
            logger.info("🔄 Restaurando estado de la interfaz")
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
    
    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    logger.info("🧵 Iniciando hilo de trabajo para descarga de suscriptores")
    threading.Thread(target=worker, daemon=True).start()

def run_eliminar_listas(btn):
    logger.info("🚀 Iniciando proceso de eliminación de listas")
    def worker():
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                logger.warning("❌ Configuración no válida, cancelando proceso")
                return

            logger.info("📥 Importando módulo eliminar_listas")
            import src.eliminar_listas as m
            importlib.reload(m)
            
            # Validar archivo antes de continuar
            logger.info("🔍 Validando archivo de búsqueda de listas para eliminación")
            valid_listas, message_listas, marcadas = m.validar_archivo_busqueda_listas()
            if not valid_listas:
                logger.warning(f"❌ Archivo de búsqueda de listas inválido: {message_listas}")
                root.after(0, lambda: notify("Error de Archivo", message_listas, "warning"))
                return

            logger.info(f"⚠️ Solicitando confirmación para eliminar {marcadas} listas")
            # Confirmación del usuario
            if not messagebox.askyesno("Confirmar eliminación", f"Vas a eliminar {marcadas} listas en Acumbamail. ¿Continuar?"):
                logger.info("↩️ Eliminación cancelada por el usuario")
                return

            # Ejecutar eliminación
            logger.info("🗑️ Ejecutando eliminación de listas")
            exitosas, fallidas, mensaje = m.eliminar_listas_marcadas()
            
            # Mostrar resultado
            logger.success(f"✅ Eliminación completada: {exitosas} exitosas, {fallidas} fallidas", exitosas=exitosas, fallidas=fallidas)
            tipo_notif = "info" if not fallidas else "warning"
            root.after(0, lambda: notify("Resultado Eliminación", mensaje, tipo_notif))

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error al eliminar listas: {error_msg}", error=error_msg)
            root.after(0, lambda: notify("Error", f"Error al eliminar listas: {error_msg}", "error"))
        finally:
            logger.info("🔄 Restaurando estado de la interfaz")
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))

    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    logger.info("🧵 Iniciando hilo de trabajo para eliminación de listas")
    threading.Thread(target=worker, daemon=True).start()

def run_mapear_segmentos(btn):
	logger.info("🚀 Iniciando proceso de mapeo de segmentos")
	def worker():
		try:
			# Validar configuración
			logger.info("🔍 Validando configuración de mapeo de segmentos")
			valid, message = validar_configuracion()
			if not valid:
				logger.error(f"❌ Configuración inválida para mapeo de segmentos: {message}")
				root.after(0, lambda: notify("Error de Configuración", message, "error"))
				return
			
			# Validar archivo de segmentos
			logger.info("🔍 Validando archivo de segmentos")
			valid_segmentos, message_segmentos, segmentos_count = validar_archivo_segmentos()
			if not valid_segmentos:
				logger.error(f"❌ Archivo de segmentos inválido: {message_segmentos}")
				root.after(0, lambda: notify("Error de Archivo", message_segmentos, "error"))
				return
			
			# Verificar que hay listas para procesar (opcional - se pueden crear automáticamente)
			listas_dir = os.path.join(os.path.dirname(data_path("dummy")), "listas")
			if not os.path.exists(listas_dir):
				os.makedirs(listas_dir)
				logger.info(f"📁 Creando directorio de listas: {listas_dir}")
				root.after(0, lambda: notify("Info", 
					"Se creó la carpeta 'data/listas'. Las listas se crearán automáticamente en Acumbamail.", "info"))
			
			# Mostrar información previa
			logger.info(f"📥 Iniciando procesamiento de {segmentos_count} segmentos")
			root.after(0, lambda: notify("Iniciando", f"Procesando {segmentos_count} segmentos definidos", "info"))
			
			# Mostrar contador (estimado 5-15 minutos dependiendo del número de segmentos)
			# tiempo_estimado = min(segmentos_count * 30, 900)  # 30 segundos por segmento, máximo 15 minutos
			# root.after(0, lambda: mostrar_contador_progreso("Procesando Segmentos", tiempo_estimado))
			# root.after(0, lambda: actualizar_progreso("Conectando a Acumbamail"))

			logger.info("📥 Importando módulo mapeo_segmentos")
			import src.mapeo_segmentos as m
			importlib.reload(m)

			# root.after(0, lambda: actualizar_progreso("Mapeando y creando segmentos"))
			# Ejecutar mapeo completo
			logger.info("⚙️ Ejecutando mapeo completo de segmentos")
			resultado = m.mapear_segmentos_completo()

			# root.after(0, lambda: cerrar_contador_progreso())

			if "error" in resultado:
				logger.error(f"❌ Error en mapeo de segmentos: {resultado['error']}", error=resultado['error'])
				root.after(0, lambda: notify("Error", f"Error en mapeo: {resultado['error']}", "error"))
				return

			# Mostrar resultado
			total = len(resultado.get('listas_procesadas', [])) + len(resultado.get('listas_fallidas', []))
			exitosas = len(resultado.get('listas_procesadas', []))
			fallidas = len(resultado.get('listas_fallidas', []))

			logger.success(f"✅ Mapeo de segmentos completado: {exitosas} exitosas, {fallidas} fallidas", 
				exitosas=exitosas, fallidas=fallidas, total=total)
			
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

			if exitosas > 0:
				root.after(0, lambda: notify("Procesamiento Completado", mensaje, "info"))
			else:
				root.after(0, lambda: notify("Procesamiento Incompleto", mensaje, "warning"))

		except Exception as e:
			error_msg = str(e)
			logger.error(f"❌ Error durante el procesamiento de segmentos: {error_msg}", error=error_msg)
			# root.after(0, lambda: cerrar_contador_progreso())
			root.after(0, lambda: notify("Error", f"Error durante el procesamiento: {error_msg}", "error"))
		finally:
			logger.info("🔄 Restaurando estado de la interfaz")
			root.after(0, lambda: btn.config(state=tk.NORMAL))
			root.after(0, lambda: root.config(cursor=""))

	btn.config(state=tk.DISABLED)
	root.config(cursor="watch")
	logger.info("🧵 Iniciando hilo de trabajo para mapeo de segmentos")
	threading.Thread(target=worker, daemon=True).start()

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
    
    logger.success("✅ Aplicación iniciada exitosamente, mostrando interfaz")

    # === SECCIÓN CAMPAÑAS ===
    frame_campanias = tk.LabelFrame(root, text="Campañas", font=("Arial", 12, "bold"), pady=5)
    frame_campanias.pack(pady=12, fill="x", padx=25)

    btn_listar = tk.Button(frame_campanias, text="Listar campañas", font=("Arial", 14), height=2, command=lambda: run_listar_campanias(btn_listar))
    btn_listar.pack(pady=8, fill="x", padx=15)

    btn_obtener = tk.Button(frame_campanias, text="Obtener suscriptores de campañas", font=("Arial", 14), height=2, command=lambda: run_obtener_suscriptores(btn_obtener))
    btn_obtener.pack(pady=8, fill="x", padx=15)

    # === SECCIÓN LISTAS ===
    frame_listas = tk.LabelFrame(root, text="Listas", font=("Arial", 12, "bold"), pady=5)
    frame_listas.pack(pady=12, fill="x", padx=25)
    
    def on_click_obtener_listas():
        try:
            global obtener_listas_running
            if obtener_listas_running:
                notify("En curso", "La operación de obtención de listas ya se está ejecutando.", "warning")
                return
            # Set the flag immediately to avoid race from quick double-clicks
            obtener_listas_running = True
        except Exception:
            pass
        try:
            # Disable button and set busy cursor immediately to give feedback
            btn_obtener_listas.config(state=tk.DISABLED)
            root.config(cursor="watch")
        except Exception:
            pass
        run_obtener_listas(btn_obtener_listas)

    btn_obtener_listas = tk.Button(frame_listas, text="Obtener listas", font=("Arial", 14), height=2, command=on_click_obtener_listas)
    btn_obtener_listas.pack(pady=8, fill="x", padx=15)

    btn_descargar = tk.Button(frame_listas, text="Descargar lista de suscriptores", font=("Arial", 14), height=2, command=lambda: run_descargar_suscriptores(btn_descargar))
    btn_descargar.pack(pady=8, fill="x", padx=15)
    
    btn_eliminar = tk.Button(frame_listas, text="Eliminar listas marcadas", font=("Arial", 14), height=2, command=lambda: run_eliminar_listas(btn_eliminar), bg="#F44336", fg="white")
    btn_eliminar.pack(pady=8, fill="x", padx=15)
    
    btn_crear = tk.Button(frame_listas, text="Subir lista de suscriptores", font=("Arial", 14), height=2, command=lambda: run_crear_lista(btn_crear))
    btn_crear.pack(pady=8, fill="x", padx=15)

    btn_mapear = tk.Button(frame_listas, text="Procesar segmentos", font=("Arial", 14), height=2, command=lambda: run_mapear_segmentos(btn_mapear))
    btn_mapear.pack(pady=8, fill="x", padx=15)

    # === CONFIGURACIÓN ===
    frame_config = tk.LabelFrame(root, text="Configuración", font=("Arial", 12, "bold"), pady=5)
    frame_config.pack(pady=12, fill="x", padx=25)

    btn_config = tk.Button(frame_config, text="⚙️ Configurar Credenciales", font=("Arial", 14), height=2,
                          command=lambda: show_config_window(root), bg="#4CAF50", fg="white")
    btn_config.pack(pady=8, fill="x", padx=15)

    btn_clean = tk.Button(frame_config, text="Limpiar sesión actual", font=("Arial", 14), height=2, command=limpiar_sesion)
    btn_clean.pack(pady=8, fill="x", padx=15)

    root.mainloop()