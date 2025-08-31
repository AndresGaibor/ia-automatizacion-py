import tkinter as tk
from tkinter import messagebox
import yaml
import os
import pandas as pd
import importlib
from src.utils import load_config, data_path

def configuracion():
    defaults = {
        'url': 'https://google.com/pagina/etc',
        'url_base': 'https://google.com',
        'user': 'usuario@correo.com',
        'password': 'clave',
        'headless': False
    }
    # Crea config.yaml en app_data_dir si no existe; no sobrescribe ediciones
    load_config(defaults)


def archivo_busqueda():
    # Crear Busqueda.xlsx una sola vez en la carpeta de datos del usuario
    archivo = data_path("Busqueda.xlsx")
    if not os.path.exists(archivo):
        df = pd.DataFrame(columns=['Buscar', 'Nombre', 'Tipo', 'Fecha envío', 'Listas', 'Emails', 'Abiertos', 'Clics'])
        df.to_excel(archivo, index=False)

def archivo_lista_envio():
    archivo = data_path("Lista_envio.xlsx")
    if not os.path.exists(archivo):
        df = pd.DataFrame(columns=['Email'])
        df.to_excel(archivo, index=False)

def accion_1():
    messagebox.showinfo("Acción 1", "Ejecutando función 1")

def accion_2():
    messagebox.showinfo("Acción 2", "Ejecutando función 2")

def accion_3():
    messagebox.showinfo("Acción 3", "Ejecutando función 3")

def accion_4():
    messagebox.showinfo("Acción 4", "Ejecutando función 4")

def run_listar_campanias():
    import src.listar_campanias as m
    importlib.reload(m)
    m.main()

def run_obtener_suscriptores():
    import src.demo as m
    importlib.reload(m)
    m.main()

def run_crear_lista():
    import src.crear_lista as m
    importlib.reload(m)
    m.main()

if __name__ == "__main__":
    configuracion()
    archivo_busqueda()
    archivo_lista_envio()

    root = tk.Tk()
    root.title("Automatización")
    root.geometry("320x220")

    tk.Button(root, text="Listar campañas", command=run_listar_campanias).pack(pady=8, fill="x", padx=20)
    tk.Button(root, text="Obtener suscriptores de campañas", command=run_obtener_suscriptores).pack(pady=8, fill="x", padx=20)
    tk.Button(root, text="Crear lista de suscriptores", command=run_crear_lista).pack(pady=8, fill="x", padx=20)

    root.mainloop()