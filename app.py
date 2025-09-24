import tkinter as tk
from tkinter import messagebox, ttk
import os
import pandas as pd
import importlib
import threading
import time
from src.utils import load_config, data_path, storage_state_path, notify
from src.config_window import show_config_window
from src.config.settings import settings
from src.config_validator import check_config_or_show_dialog

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

def validar_configuracion() -> tuple[bool, str]:
    """Valida que la configuración esté completa"""
    config = load_config()
    
    # Validar credenciales básicas
    if not config.get("user") or config.get("user") == "usuario@correo.com":
        return False, "Error: Usuario no configurado. Edite config.yaml con sus credenciales de Acumbamail."
    
    if not config.get("password") or config.get("password") == "clave":
        return False, "Error: Contraseña no configurada. Edite config.yaml con su contraseña de Acumbamail."
    
    # Validar API key si se necesita
    api_config = config.get("api", {})
    if not api_config.get("api_key"):
        return False, "Advertencia: API Key no configurada. Algunas funciones pueden no funcionar. Configure api.api_key en config.yaml."
    
    return True, "Configuración válida"

def validar_archivo_busqueda() -> tuple[bool, str, int]:
    """Valida el archivo de búsqueda y cuenta elementos marcados"""
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
    """Valida el archivo de búsqueda de listas y cuenta elementos marcados"""
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
    """Valida el archivo de segmentos"""
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
    if not os.path.exists(archivo):
        df = pd.DataFrame(columns=['Buscar', 'Nombre', 'Tipo', 'Fecha envío', 'Listas', 'Emails', 'Abiertos', 'Clics'])
        df.to_excel(archivo, index=False)


def archivo_busqueda_listas():
	archivo = data_path("Busqueda_Listas.xlsx")
	if not os.path.exists(archivo):
		df = pd.DataFrame(columns=['Buscar', 'NOMBRE LISTA', 'SUSCRIPTORES', 'CREACION'])
		df.to_excel(archivo, index=False)

def archivo_segmentos():
	archivo = data_path("Segmentos.xlsx")
	if not os.path.exists(archivo):
		df = pd.DataFrame(columns=['CREACION SEGMENTO', 'NOMBRE LISTA', 'NOMBRE SEGMENTO'])
		df.to_excel(archivo, index=False)

def limpiar_sesion():
    try:
        path = storage_state_path()
        if not os.path.exists(path):
            messagebox.showinfo("Sesión", "No hay sesión guardada.")
            return
        if not messagebox.askyesno("Confirmar", "¿Eliminar la sesión actual?"):
            return
        os.remove(path)
        messagebox.showinfo("Sesión", "Sesión eliminada. Se pedirá login en el próximo inicio.")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo limpiar la sesión: {e}")

def run_listar_campanias(btn):
    def worker():
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                return

            import src.listar_campanias as m
            importlib.reload(m)

            m.main()
            root.after(0, lambda: notify("Completado", "Listado de campañas finalizado con éxito", "info"))

        except Exception as e:
            root.after(0, lambda: notify("Error", f"Error al listar campañas: {e}", "error"))
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))

    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    threading.Thread(target=worker, daemon=True).start()

def run_obtener_suscriptores(btn):
    def worker():
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                return
            
            # Validar archivo de búsqueda
            valid_busqueda, message_busqueda, marcados = validar_archivo_busqueda()
            if not valid_busqueda:
                root.after(0, lambda: notify("Error de Archivo", message_busqueda, "warning"))
                return
            
            # Mostrar contador (estimado 5-15 minutos dependiendo de campañas)
            # tiempo_estimado = min(marcados * 30, 900)  # 30 segundos por campaña, máximo 15 minutos
            # root.after(0, lambda: mostrar_contador_progreso("Obteniendo Suscriptores", tiempo_estimado))
            # root.after(0, lambda: actualizar_progreso("Conectando a Acumbamail"))
            
            import src.demo as m
            importlib.reload(m)
            
            # root.after(0, lambda: actualizar_progreso("Procesando campañas y extrayendo suscriptores"))
            m.main()
            
            # root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: notify("Completado", "Extracción de suscriptores finalizada con éxito", "info"))
            
        except Exception as e:
            # root.after(0, lambda: cerrar_contador_progreso())
            error_msg = str(e)
            if "Error en campaña" in error_msg:
                root.after(0, lambda: notify("Error de Campaña", f"La campaña seleccionada no está disponible o fue eliminada: {error_msg}", "error"))
            else:
                root.after(0, lambda: notify("Error", f"Error al obtener suscriptores: {error_msg}", "error"))
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
    
    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
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
    def worker():
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                return
            
            # Verificar que hay configuración de lista
            config = load_config()
            lista_config = config.get('lista', {})
            if not lista_config.get('sender_email') or lista_config.get('sender_email') == 'usuario@correo.com':
                root.after(0, lambda: notify("Error de Configuración", 
                    "Error: Falta configurar los datos de la lista (sender_email, company, etc.) en config.yaml", "error"))
                return
            
            # Mostrar información previa
            root.after(0, lambda: notify("Iniciando", "Preparando subida de lista de suscriptores", "info"))
            
            # Mostrar contador (estimado 2-5 minutos dependiendo del tamaño del archivo)
            # root.after(0, lambda: mostrar_contador_progreso("Subiendo Lista", 180))  # 3 minutos estimado
            # root.after(0, lambda: actualizar_progreso("Seleccionando archivo Excel"))
            
            import src.crear_lista_mejorado as m
            importlib.reload(m)
            
            # root.after(0, lambda: actualizar_progreso("Validando datos y subiendo a Acumbamail"))
            # Ejecutar creación automática
            m.main_automatico()
            
            # root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: notify("Completado", "Lista de suscriptores subida con éxito", "info"))
            
        except Exception as e:
            # root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: notify("Error", f"Error al crear lista: {e}", "error"))
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))

    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    threading.Thread(target=worker, daemon=True).start()

def run_obtener_listas(btn):
    def worker():
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                return

            # Mostrar información previa
            root.after(0, lambda: notify("Iniciando", "Obteniendo todas las listas vía API", "info"))

            # Mostrar contador (estimado 1-3 minutos)
            # root.after(0, lambda: mostrar_contador_progreso("Obteniendo Listas", 180))
            # root.after(0, lambda: actualizar_progreso("Conectando a Acumbamail API"))

            import src.obtener_listas as m
            importlib.reload(m)

            # root.after(0, lambda: actualizar_progreso("Extrayendo información de listas vía API"))
            m.main()

            # root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: notify("Completado", "Obtención de listas finalizada con éxito", "info"))

        except Exception as e:
            # root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: notify("Error", f"Error al obtener listas: {e}", "error"))
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))

    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    threading.Thread(target=worker, daemon=True).start()


def run_descargar_suscriptores(btn):
    def worker():
        try:
            # Validar configuración con diálogo automático
            if not check_config_or_show_dialog(root):
                return
            
            # Validar archivo de búsqueda de listas
            valid_listas, message_listas, marcadas = validar_archivo_busqueda_listas()
            if not valid_listas:
                root.after(0, lambda: notify("Error de Archivo", message_listas, "warning"))
                return
            
            # Mostrar información previa
            root.after(0, lambda: notify("Iniciando", f"Descargando suscriptores de {marcadas} listas", "info"))
            
            # Mostrar contador (estimado 2-10 minutos dependiendo del tamaño de las listas)
            # tiempo_estimado = min(marcadas * 60, 600)  # 1 minuto por lista, máximo 10 minutos
            # root.after(0, lambda: mostrar_contador_progreso("Descargando Suscriptores", tiempo_estimado))
            # root.after(0, lambda: actualizar_progreso("Conectando a Acumbamail"))
            
            import src.descargar_suscriptores as m
            importlib.reload(m)
            
            # root.after(0, lambda: actualizar_progreso("Descargando datos de suscriptores"))
            m.main()
            
            # root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: notify("Completado", "Descarga de suscriptores finalizada con éxito", "info"))
            
        except Exception as e:
            # root.after(0, lambda: cerrar_contador_progreso())
            root.after(0, lambda: notify("Error", f"Error al descargar suscriptores: {e}", "error"))
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
    
    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    threading.Thread(target=worker, daemon=True).start()

def run_mapear_segmentos(btn):
	def worker():
		try:
			# Validar configuración
			valid, message = validar_configuracion()
			if not valid:
				root.after(0, lambda: notify("Error de Configuración", message, "error"))
				return
			
			# Validar archivo de segmentos
			valid_segmentos, message_segmentos, segmentos_count = validar_archivo_segmentos()
			if not valid_segmentos:
				root.after(0, lambda: notify("Error de Archivo", message_segmentos, "error"))
				return
			
			# Verificar que hay listas para procesar (opcional - se pueden crear automáticamente)
			listas_dir = os.path.join(os.path.dirname(data_path("dummy")), "listas")
			if not os.path.exists(listas_dir):
				os.makedirs(listas_dir)
				root.after(0, lambda: notify("Info", 
					"Se creó la carpeta 'data/listas'. Las listas se crearán automáticamente en Acumbamail.", "info"))
			
			# Mostrar información previa
			root.after(0, lambda: notify("Iniciando", f"Procesando {segmentos_count} segmentos definidos", "info"))
			
			# Mostrar contador (estimado 5-15 minutos dependiendo del número de segmentos)
			# tiempo_estimado = min(segmentos_count * 30, 900)  # 30 segundos por segmento, máximo 15 minutos
			# root.after(0, lambda: mostrar_contador_progreso("Procesando Segmentos", tiempo_estimado))
			# root.after(0, lambda: actualizar_progreso("Conectando a Acumbamail"))

			import src.mapeo_segmentos as m
			importlib.reload(m)

			# root.after(0, lambda: actualizar_progreso("Mapeando y creando segmentos"))
			# Ejecutar mapeo completo
			resultado = m.mapear_segmentos_completo()

			# root.after(0, lambda: cerrar_contador_progreso())

			if "error" in resultado:
				root.after(0, lambda: notify("Error", f"Error en mapeo: {resultado['error']}", "error"))
				return

			# Mostrar resultado
			total = len(resultado.get('listas_procesadas', [])) + len(resultado.get('listas_fallidas', []))
			exitosas = len(resultado.get('listas_procesadas', []))
			fallidas = len(resultado.get('listas_fallidas', []))

			mensaje = f"Procesamiento de segmentos completado:\n\n"
			mensaje += f"Listas procesadas: {exitosas}\n"
			mensaje += f"Listas fallidas: {fallidas}\n"
			mensaje += f"Total: {total}"

			if resultado.get('listas_procesadas'):
				mensaje += f"\n\nListas exitosas:\n"
				for lista in resultado['listas_procesadas']:
					mensaje += f"• {lista}\n"

			if resultado.get('listas_fallidas'):
				mensaje += f"\nListas fallidas:\n"
				for lista in resultado['listas_fallidas']:
					mensaje += f"• {lista}\n"
				mensaje += f"\nSugerencias:\n"
				mensaje += f"- Verifique que los datos en Segmentos.xlsx coincidan con los datos reales\n"
				mensaje += f"- Revise que las condiciones de segmentación sean correctas\n"
				mensaje += f"- Consulte los logs para más detalles sobre errores específicos"

			if exitosas > 0:
				root.after(0, lambda: notify("Procesamiento Completado", mensaje, "info"))
			else:
				root.after(0, lambda: notify("Procesamiento Incompleto", mensaje, "warning"))

		except Exception as e:
			# root.after(0, lambda: cerrar_contador_progreso())
			root.after(0, lambda: notify("Error", f"Error durante el procesamiento: {e}", "error"))
		finally:
			root.after(0, lambda: btn.config(state=tk.NORMAL))
			root.after(0, lambda: root.config(cursor=""))

	btn.config(state=tk.DISABLED)
	root.config(cursor="watch")
	threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    configuracion()
    archivo_busqueda()
    archivo_busqueda_listas()
    archivo_segmentos()

    root = tk.Tk()
    root.title("Automatización Acumbamail")
    root.geometry("450x700")

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
    
    btn_obtener_listas = tk.Button(frame_listas, text="Obtener listas", font=("Arial", 14), height=2, command=lambda: run_obtener_listas(btn_obtener_listas))
    btn_obtener_listas.pack(pady=8, fill="x", padx=15)

    btn_descargar = tk.Button(frame_listas, text="Descargar lista de suscriptores", font=("Arial", 14), height=2, command=lambda: run_descargar_suscriptores(btn_descargar))
    btn_descargar.pack(pady=8, fill="x", padx=15)
    
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