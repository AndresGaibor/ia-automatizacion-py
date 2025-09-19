import tkinter as tk
from tkinter import messagebox
import os
import pandas as pd
import importlib
import threading
from src.utils import load_config, data_path, storage_state_path
from src.crear_lista import seleccionar_hoja_tk

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

def archivo_lista_envio():
    archivo = data_path("Lista_envio.xlsx")
    if not os.path.exists(archivo):
        df = pd.DataFrame(columns=['Email'])
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
    # Pedimos la hoja en el hilo principal (Tk es single-thread)
    hojas = seleccionar_hoja_tk(data_path("Lista_envio.xlsx"), master=root, multiple=True)
    if not hojas:
        return  # cancelado por el usuario

    def worker(hojas_sel: list[str]):
        try:
            import src.crear_lista as m
            importlib.reload(m)
            # Pasamos la lista de hojas directamente a main
            m.main(nombre_hoja=hojas_sel, multiple=True)
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")
    threading.Thread(target=worker, args=(hojas,), daemon=True).start()

if __name__ == "__main__":
    configuracion()
    archivo_busqueda()
    archivo_lista_envio()

    root = tk.Tk()
    root.title("Automatización Acumbamail")
    root.geometry("360x280")

    btn_listar = tk.Button(root, text="Listar campañas", command=lambda: run_listar_campanias(btn_listar))
    btn_listar.pack(pady=8, fill="x", padx=20)

    btn_obtener = tk.Button(root, text="Obtener suscriptores de campañas", command=lambda: run_obtener_suscriptores(btn_obtener))
    btn_obtener.pack(pady=8, fill="x", padx=20)
    
    btn_obtener_listas = tk.Button(root, text="Obtener listas suscriptores", command=lambda: run_listar_campanias(btn_listar))
    btn_obtener_listas.pack(pady=8, fill="x", padx=20)

    btn_crear = tk.Button(root, text="Crear lista de suscriptores", command=lambda: run_crear_lista(btn_crear))
    btn_crear.pack(pady=8, fill="x", padx=20)

    # Botón limpiar sesión
    btn_clean = tk.Button(root, text="Limpiar sesión actual", command=limpiar_sesion)
    btn_clean.pack(pady=8, fill="x", padx=20)

    root.mainloop()