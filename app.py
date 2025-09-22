import tkinter as tk
from tkinter import messagebox
import os
import pandas as pd
import importlib
import threading
from src.utils import load_config, data_path, storage_state_path

# Config por defecto (usada para crear y para "Restaurar")
DEFAULTS = {
    'url': 'https://google.com/pagina/etc',
    'url_base': 'https://google.com',
    'user': 'usuario@correo.com',
    'password': 'clave',
    'headless': False,
    'velocidad_internet': 'normal'
}

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
            import src.listar_campanias as m
            importlib.reload(m)
            m.main()
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    threading.Thread(target=worker, daemon=True).start()

def run_obtener_suscriptores(btn):
    def worker():
        try:
            import src.demo as m
            importlib.reload(m)
            m.main()
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    threading.Thread(target=worker, daemon=True).start()

def run_crear_lista(btn):
    # Verificar y crear directorio de listas si no existe
    listas_dir = os.path.join(os.path.dirname(data_path("dummy")), "listas")
    if not os.path.exists(listas_dir):
        os.makedirs(listas_dir)

    # Crear Plantilla.xlsx si no hay archivos en el directorio
    archivos_excel = [f for f in os.listdir(listas_dir) if f.endswith('.xlsx') and f != 'Plantilla.xlsx']
    if not archivos_excel:
        plantilla_path = os.path.join(listas_dir, "Plantilla.xlsx")
        if not os.path.exists(plantilla_path):
            df_plantilla = pd.DataFrame(columns=['email', 'nombre', 'apellido'])
            df_plantilla.to_excel(plantilla_path, index=False)

    # Mostrar selector de archivos del directorio listas
    from src.crear_lista_api import seleccionar_archivo_tk
    archivo_seleccionado = seleccionar_archivo_tk(listas_dir, master=root)
    if not archivo_seleccionado:
        return  # cancelado por el usuario

    # Seleccionar hojas del archivo elegido
    from src.crear_lista_api import seleccionar_hoja_tk
    hojas = seleccionar_hoja_tk(archivo_seleccionado, master=root, multiple=True)
    if not hojas:
        return  # cancelado por el usuario

    def worker(archivo: str, hojas_sel: list[str]):
        try:
            import src.crear_lista_api as m
            importlib.reload(m)
            # Pasamos el archivo y la lista de hojas directamente a main
            m.main(archivo=archivo, nombre_hoja=hojas_sel, multiple=True)
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    threading.Thread(target=worker, args=(archivo_seleccionado, hojas), daemon=True).start()

def run_obtener_listas(btn):
    def worker():
        try:
            import src.obtener_listas as m
            importlib.reload(m)
            m.main()
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    threading.Thread(target=worker, daemon=True).start()


def run_mapear_segmentos(btn):
	def worker():
		try:
			# Verificar que existe el archivo de segmentos
			segmentos_file = data_path("Segmentos.xlsx")
			if not os.path.exists(segmentos_file):
				root.after(0, lambda: messagebox.showerror(
					"Error",
					"No se encontró el archivo Segmentos.xlsx.\n\n"
					"Este archivo debe contener las definiciones de segmentos.\n"
					"Verifique que existe en la carpeta 'data'."
				))
				return

			# Verificar que hay listas para procesar (opcional - se pueden crear automáticamente)
			listas_dir = os.path.join(os.path.dirname(data_path("dummy")), "listas")
			if not os.path.exists(listas_dir):
				os.makedirs(listas_dir)
				root.after(0, lambda: messagebox.showinfo(
					"Info",
					"Se creó la carpeta 'data/listas'.\n\n"
					"Si desea procesar listas existentes, coloque los archivos Excel en esa carpeta.\n"
					"Las listas se crearán automáticamente en Acumbamail si no existen."
				))

			import src.mapeo_segmentos as m
			importlib.reload(m)

			# Ejecutar mapeo completo
			resultado = m.mapear_segmentos_completo()

			if "error" in resultado:
				root.after(0, lambda: messagebox.showerror("Error", f"Error en mapeo: {resultado['error']}"))
				return

			# Mostrar resultado
			total = len(resultado.get('listas_procesadas', [])) + len(resultado.get('listas_fallidas', []))
			exitosas = len(resultado.get('listas_procesadas', []))
			fallidas = len(resultado.get('listas_fallidas', []))

			mensaje = f"Procesamiento de segmentos completado:\n\n"
			mensaje += f"✅ Listas procesadas: {exitosas}\n"
			mensaje += f"❌ Listas fallidas: {fallidas}\n"
			mensaje += f"📋 Total: {total}"

			if resultado.get('listas_procesadas'):
				mensaje += f"\n\nListas exitosas:\n"
				for lista in resultado['listas_procesadas']:
					mensaje += f"• {lista}\n"

			if resultado.get('listas_fallidas'):
				mensaje += f"\nListas fallidas:\n"
				for lista in resultado['listas_fallidas']:
					mensaje += f"• {lista}\n"
				mensaje += f"\n💡 Sugerencias:\n"
				mensaje += f"- Verifique que los datos en Segmentos.xlsx coincidan con los datos reales\n"
				mensaje += f"- Revise que las condiciones de segmentación sean correctas\n"
				mensaje += f"- Consulte los logs para más detalles sobre errores específicos"

			if exitosas > 0:
				root.after(0, lambda: messagebox.showinfo("Procesamiento Completado", mensaje))
			else:
				root.after(0, lambda: messagebox.showwarning("Procesamiento Incompleto", mensaje))

		except Exception as e:
			root.after(0, lambda: messagebox.showerror("Error", f"Ocurrió un error durante el procesamiento: {e}"))
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
    root.geometry("450x600")

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

    btn_crear = tk.Button(frame_listas, text="Crear lista de suscriptores", font=("Arial", 14), height=2, command=lambda: run_crear_lista(btn_crear))
    btn_crear.pack(pady=8, fill="x", padx=15)
    

    btn_mapear = tk.Button(frame_listas, text="Procesar segmentos", font=("Arial", 14), height=2, command=lambda: run_mapear_segmentos(btn_mapear))
    btn_mapear.pack(pady=8, fill="x", padx=15)

    # === CONFIGURACIÓN ===
    frame_config = tk.LabelFrame(root, text="Configuración", font=("Arial", 12, "bold"), pady=5)
    frame_config.pack(pady=12, fill="x", padx=25)

    btn_clean = tk.Button(frame_config, text="Limpiar sesión actual", font=("Arial", 14), height=2, command=limpiar_sesion)
    btn_clean.pack(pady=8, fill="x", padx=15)

    root.mainloop()