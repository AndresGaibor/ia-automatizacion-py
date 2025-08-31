"""
Funciones utilitarias compartidas para automatización.
"""

import os
import sys

def _early_project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Forzar ruta de navegadores de Playwright antes de importar la librería
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(_early_project_root(), "ms-playwright"))
os.makedirs(os.environ["PLAYWRIGHT_BROWSERS_PATH"], exist_ok=True)

from playwright.sync_api import Page, TimeoutError as PWTimeoutError
from playwright._impl._errors import Error as PWError
import pandas as pd
import json
import yaml

REAL_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

def cargar_terminos_busqueda(archivo_busqueda: str) -> list[list[str]]:
    """
    Carga los términos de búsqueda desde el archivo Excel
    """
    terminos = []
    df = pd.read_excel(archivo_busqueda, engine="openpyxl")
    
    for index, row in df.iterrows():
        buscar = row['Buscar']
        if(buscar == 'x' or buscar == 'X'):
            terminos.append([row['Nombre'], row['Listas']])
    
    return terminos

def project_root() -> str:
    """Directorio base de la app:
    - Si está congelada (PyInstaller), carpeta del ejecutable.
    - En desarrollo, raíz del proyecto (carpeta que contiene app.py).
    """
    if getattr(sys, "frozen", False):  # PyInstaller --onefile
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def config_path() -> str:
    return os.path.join(project_root(), "config.yaml")

def data_path(name: str) -> str:
    d = os.path.join(project_root(), "data")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, name)

def load_config(defaults: dict | None = None) -> dict:
    """Carga config.yaml desde el directorio base. Si no existe, lo crea con defaults (si se proveen)."""
    path = config_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    if defaults is None:
        defaults = {}
    with open(path, "w") as f:
        yaml.safe_dump(defaults, f, sort_keys=False)
    return defaults

def save_config(cfg: dict):
    with open(config_path(), "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)

## NOTA: se elimina la antigua función load_config basada en project_root,
## ya que ahora toda configuración vive en app_data_dir (compatible con PyInstaller).

def crear_contexto_navegador(browser, extraccion_oculta: bool = False):
    """
    Crea y configura el contexto del navegador
    """
    storage_state = storage_state_path()
    if not os.path.exists(storage_state):
        # asegurar carpeta data y archivo
        os.makedirs(os.path.dirname(storage_state), exist_ok=True)
        with open(storage_state, "w") as f:
            json.dump({}, f)

    context = browser.new_context(
        viewport={"width": 1400, "height": 900},
        user_agent=REAL_UA,
        locale="es-ES",
        timezone_id="Europe/Madrid",
        ignore_https_errors=True,
        storage_state=storage_state,
    )
    return context

def storage_state_path() -> str:
    """Ruta al archivo de estado de sesión persistente."""
    return data_path("datos_sesion.json")

def ensure_playwright_browsers_path() -> str:
    """
    Garantiza la ruta (ya establecida arriba) y la devuelve.
    """
    path = os.environ["PLAYWRIGHT_BROWSERS_PATH"]
    os.makedirs(path, exist_ok=True)
    return path

def configurar_navegador(p, extraccion_oculta: bool = False):
    """
    Configura y lanza el navegador
    """
    ensure_playwright_browsers_path()
    try:
        browser = p.chromium.launch(
            headless=extraccion_oculta,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        return browser
    except PWError as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            try:
                notify("Playwright", "Descargando Chromium (solo la primera vez)...")
            except Exception:
                pass
            # Ejecutar el CLI sin cerrar el proceso
            from playwright.__main__ import main as playwright_main
            old_argv = sys.argv[:]
            try:
                for args in (["playwright", "install", "chromium"],
                             ["playwright", "install", "--force", "chromium"]):
                    try:
                        sys.argv = args
                        ensure_playwright_browsers_path()
                        playwright_main()
                        break  # instalación OK
                    except SystemExit as se:
                        # Evitar que cierre la app; solo propagar si es error real
                        if se.code not in (0, None):
                            raise
                    except Exception:
                        # Intentará con --force en el siguiente ciclo
                        continue
            finally:
                sys.argv = old_argv

            # Reintento de lanzamiento tras instalar
            return p.chromium.launch(
                headless=extraccion_oculta,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
        raise

def navegar_a_reportes(page: Page):
    """
    Navega a la sección de reportes
    """
    page.click("a[href*='/reports']")
    page.wait_for_load_state('networkidle')


def obtener_total_paginas(page: Page) -> int:
	"""
	Obtiene el número total de páginas de reportes
	"""
	try:
		items_por_pagina = page.locator('select').filter(has=page.locator('option', has_text="15"))
		# items_por_pagina.wait_for(timeout=2000)
		
		ultimo_option = items_por_pagina.locator('option').last
		value_ultimo_option = ultimo_option.get_attribute('value')
		items_por_pagina.select_option(value=value_ultimo_option)
		page.wait_for_load_state("networkidle")
	except Exception as e:
		print(f"No se encontro o hubo un error en la opcion de aumentar items por pagina")

	try:
		navegacion = page.locator('ul').filter(has=page.locator('li').locator('a', has_text="1")).last
		# navegacion.wait_for(timeout=2000)
		
		ultimo_elemento = navegacion.locator('li').last
		texto = ultimo_elemento.inner_text()
		
		if texto.isdigit():
			return int(texto)
		else:
			return 1
	except Exception as e:
		# print(f"No se pudo obtener el total de páginas: {e}")
		return 1

def navegar_siguiente_pagina(page: Page, pagina_actual: int) -> bool:
	"""
	Navega a la siguiente página si existe
	"""
	siguiente_pagina = pagina_actual + 1
	
	try:
		navegacion = page.locator('ul').filter(
			has=page.locator('li').locator('a', has_text=f"{siguiente_pagina}")
		).last
		
		enlace = navegacion.locator('a', has_text=f"{siguiente_pagina}").first
		
		if enlace.count() > 0:
			enlace.click()
			page.wait_for_load_state("networkidle")
			return True
		else:
			return False
			
	except Exception as e:
		print(f"⚠️ Advertencia al navegar a la página {siguiente_pagina}: {e}")
		# print(f"No se pudo navegar a la página {siguiente_pagina}")
		return False


def notify(title: str, message: str, level: str = "info") -> bool:
    """
    Muestra una notificación segura:
    - Si hay una UI Tk activa (o se puede crear en el hilo principal), usa messagebox.
    - Si no, imprime en consola.

    Retorna True si se mostró con Tk, False si se hizo fallback a print.
    """
    try:
        import tkinter as tk  # type: ignore
        from tkinter import messagebox  # type: ignore
        import threading

        root = getattr(tk, "_default_root", None)
        created = False

        if root is None:
            # Solo crear una raíz si estamos en el hilo principal para evitar errores.
            if threading.current_thread() is not threading.main_thread():
                raise RuntimeError("No hay Tk root y no estamos en el hilo principal")
            root = tk.Tk()
            root.withdraw()
            created = True

        if level == "error":
            messagebox.showerror(title, message)
        elif level == "warning":
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)

        if created:
            # Cerrar la raíz temporal para no dejar ventanas ocultas vivas.
            try:
                root.destroy()
            except Exception:
                pass
        return True
    except Exception:
        # Entornos headless o sin Tk: fallback a consola
        print(f"{title}: {message}")
        return False

