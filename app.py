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
    'headless': False
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

def abrir_configuracion():
    cfg = load_config(DEFAULTS)

    top = tk.Toplevel(root)
    top.title("Configuración")
    top.geometry("640x540")
    top.grab_set()  # modal simple

    # Slider headless (0/1)
    headless_var = tk.IntVar(value=1 if cfg.get("headless", False) else 0)

    frm_top = tk.Frame(top)
    frm_top.pack(fill="x", padx=12, pady=(12, 6))

    lbl = tk.Label(frm_top, text="Headless (navegador oculto)")
    lbl.pack(side="left")

    estado_lbl = tk.Label(frm_top, text="Desactivado" if headless_var.get() == 0 else "Activado")
    estado_lbl.pack(side="right")

    def on_slider(_=None):
        estado_lbl.config(text="Desactivado" if headless_var.get() == 0 else "Activado")

    scale = tk.Scale(frm_top, from_=0, to=1, orient="horizontal", showvalue=True,
                     variable=headless_var, command=on_slider, length=220)
    scale.pack(pady=4)

    # Editor YAML
    frm_edit = tk.Frame(top)
    frm_edit.pack(fill="both", expand=True, padx=12, pady=6)

    txt = tk.Text(frm_edit, wrap="none")
    txt.pack(side="left", fill="both", expand=True)

    scroll = tk.Scrollbar(frm_edit, command=txt.yview)
    scroll.pack(side="right", fill="y")
    txt.configure(yscrollcommand=scroll.set)

    # Cargar YAML actual
    txt.delete("1.0", "end")
    txt.insert("1.0", yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))

    # Botones
    frm_btn = tk.Frame(top)
    frm_btn.pack(fill="x", padx=12, pady=10)

    def guardar():
        try:
            nuevo = yaml.safe_load(txt.get("1.0", "end-1c")) or {}
            # Forzar headless según slider
            nuevo["headless"] = bool(headless_var.get())
            save_config(nuevo)
            messagebox.showinfo("Configuración", "Configuración guardada correctamente.")
            top.destroy()
        except yaml.YAMLError as e:
            messagebox.showerror("Error", f"YAML inválido:\n{e}")

    def restaurar():
        if messagebox.askyesno("Restaurar", "¿Restaurar valores por defecto?"):
            save_config(DEFAULTS.copy())
            messagebox.showinfo("Configuración", "Valores por defecto restaurados.")
            top.destroy()

    tk.Button(frm_btn, text="Restaurar por defecto", command=restaurar).pack(side="left")
    tk.Button(frm_btn, text="Guardar", command=guardar).pack(side="right")
    tk.Button(frm_btn, text="Cancelar", command=top.destroy).pack(side="right", padx=6)

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
    def worker():
        try:
            import src.crear_lista as m
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

if __name__ == "__main__":
    configuracion()
    archivo_busqueda()
    archivo_lista_envio()

    root = tk.Tk()
    root.title("Automatización")
    root.geometry("360x280")

    btn_listar = tk.Button(root, text="Listar campañas", command=lambda: run_listar_campanias(btn_listar))
    btn_listar.pack(pady=8, fill="x", padx=20)

    btn_obtener = tk.Button(root, text="Obtener suscriptores de campañas", command=lambda: run_obtener_suscriptores(btn_obtener))
    btn_obtener.pack(pady=8, fill="x", padx=20)

    btn_crear = tk.Button(root, text="Crear lista de suscriptores", command=lambda: run_crear_lista(btn_crear))
    btn_crear.pack(pady=8, fill="x", padx=20)

    # Botón limpiar sesión
    btn_clean = tk.Button(root, text="Limpiar sesión actual", command=limpiar_sesion)
    btn_clean.pack(pady=8, fill="x", padx=20)

    root.mainloop()