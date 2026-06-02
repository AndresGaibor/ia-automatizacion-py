"""
Funciones utilitarias compartidas para automatización.
"""

import os
import sys
import re
import logging
from pathlib import Path
from playwright.sync_api import BrowserContext, TimeoutError as PWTimeoutError

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from .logger import get_logger

logger = get_logger()

def _early_project_root() -> str:
	if getattr(sys, "frozen", False):
		return os.path.dirname(sys.executable)
	return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Forzar ruta de navegadores de Playwright antes de importar la librería
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(_early_project_root(), "ms-playwright"))
os.makedirs(os.environ["PLAYWRIGHT_BROWSERS_PATH"], exist_ok=True)

from playwright.sync_api import Page
from playwright._impl._errors import Error as PWError
import pandas as pd
import yaml

REAL_UA = (
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/537.36 "
	"(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

def cargar_id_campanias_a_buscar(archivo_busqueda: str) -> list[int]:
	"""
	Carga los términos de búsqueda desde el archivo Excel
	"""
	logger.info("📥 Cargando IDs de campañas desde archivo Excel", archivo=archivo_busqueda)
	ids = []
	df = pd.read_excel(archivo_busqueda, engine="openpyxl")
	logger.info("📊 DataFrame cargado", filas_totales=len(df))

	for index, row in df.iterrows():
		buscar = row['Buscar']
		if(buscar == 'x' or buscar == 'X'):
			id_campania = row['ID Campaña']
			ids.append(id_campania)
			logger.debug("🔍 ID de campaña encontrado", index=index, id_campania=id_campania)

	logger.success("✅ IDs de campañas cargados exitosamente", total_ids=len(ids))
	return ids

def cargar_campanias_a_buscar(archivo_busqueda: str) -> list[tuple[int, str]]:
	"""
	Carga las campañas marcadas desde el archivo Excel
	Retorna lista de tuplas (id, nombre)
	"""
	logger.info("📥 Cargando campañas desde archivo Excel", archivo=archivo_busqueda)
	campanias = []
	df = pd.read_excel(archivo_busqueda, engine="openpyxl")
	logger.info("📊 DataFrame cargado", filas_totales=len(df))

	for index, row in df.iterrows():
		buscar = row['Buscar']
		if(buscar == 'x' or buscar == 'X'):
			id_campania = row['ID Campaña']
			nombre_campania = row.get('Nombre', f'ID {id_campania}')  # Usar ID como fallback
			campanias.append((id_campania, nombre_campania))
			logger.debug("🔍 Campaña encontrada", index=index, id_campania=id_campania, nombre=nombre_campania)

	logger.success("✅ Campañas cargadas exitosamente", total_campanias=len(campanias))
	return campanias

def cargar_terminos_busqueda(archivo_busqueda: str) -> list[list[str]]:
	"""
	Carga los términos de búsqueda desde el archivo Excel
	"""
	logger.info("📥 Cargando términos de búsqueda desde archivo Excel", archivo=archivo_busqueda)
	terminos = []
	df = pd.read_excel(archivo_busqueda, engine="openpyxl")
	logger.info("📊 DataFrame cargado", filas_totales=len(df))

	for index, row in df.iterrows():
		buscar = row['Buscar']
		if(buscar == 'x' or buscar == 'X'):
			terminos.append([row['Nombre'], row['Listas']])
			logger.debug("🔍 Término de búsqueda encontrado", index=index, nombre=row['Nombre'])

	logger.success("✅ Términos de búsqueda cargados exitosamente", total_terminos=len(terminos))
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
	logger.debug("📁 Directorio de datos asegurado", path=d)
	path = os.path.join(d, name)
	logger.debug("📄 Ruta de archivo de datos generada", path=path)
	return path

def load_config(defaults: dict | None = None) -> dict:
	"""Carga config.yaml desde el directorio base. Si no existe, lo crea con defaults (si se proveen)."""
	path = config_path()
	if os.path.exists(path):
		logger.info("⚙️ Cargando configuración", path=path)
		with open(path, "r") as f:
			config = yaml.safe_load(f) or {}
			logger.success("✅ Configuración cargada exitosamente", path=path)
			return config
	logger.info("⚙️ Archivo de configuración no encontrado, creando nuevo archivo", path=path)
	if defaults is None:
		defaults = {}
	logger.debug("📝 Escribiendo configuración por defecto", path=path, defaults=defaults)
	with open(path, "w") as f:
		yaml.safe_dump(defaults, f, sort_keys=False)
	logger.success("✅ Configuración por defecto creada exitosamente", path=path)
	return defaults

def save_config(cfg: dict):
	logger.info("💾 Guardando configuración", path=config_path(), config_keys=list(cfg.keys()))
	with open(config_path(), "w") as f:
		yaml.safe_dump(cfg, f, sort_keys=False)
	logger.success("✅ Configuración guardada exitosamente", path=config_path())

def crear_contexto_navegador(browser, extraccion_oculta: bool = False) -> BrowserContext:
	"""Crea contexto del navegador con configuración de sesión optimizada."""
	storage_state = storage_state_path() if os.path.exists(storage_state_path()) else None
	context = browser.new_context(
		user_agent=REAL_UA,
		viewport={'width': 1366, 'height': 768},
		locale='es-ES',
		timezone_id='Europe/Madrid',
		ignore_https_errors=True,
		storage_state=storage_state,
	)

	# Configurar timeouts conservadores para evitar problemas de 60ms
	context.set_default_timeout(30000)  # 30 segundos por defecto
	context.set_default_navigation_timeout(60000)  # 60 segundos navegación

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

x_candidates = [2560, 1280]  # 2560 píxeles físicos; 1280 = 2560/2 (puntos lógicos)


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
				# "--window-position=2000,0",
					"--window-size=1280,800",
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

# Funciones de scraping migradas a POM:
# - navegar_a_reportes() -> ReportsPage.navigate_to()
# - obtener_total_paginas() -> ReportsPage.get_total_pages()
# - obtener_total_paginas_rapido() -> ReportsPage.get_total_pages()
# - navegar_siguiente_pagina() -> ReportsPage.navigate_to_next_page()

def notify(title: str, message: str, level: str = "info") -> bool:
	"""
	Muestra una notificación segura:
	- Si hay una UI Tk activa (o se puede crear en el hilo principal), usa messagebox.
	- Si no, imprime en consola.
	- También registra en el logger para seguimiento.

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
		logger.info("🔔 Notificación mostrada", title=title, message=message, level=level, ui_used=True)
		return True
	except Exception:
		# Entornos headless o sin Tk: fallback a consola y logger
		print(f"{title}: {message}")
		logger.info("🔔 Notificación mostrada", title=title, message=message, level=level, ui_used=False)
		return False
	

def ejecutando_desde_terminal():
	# Si stdout o stdin están asociados a un TTY -> muy probablemente desde terminal
	if sys.stdout.isatty() or sys.stdin.isatty():
		return True
	
	# Variables de entorno que suelen existir cuando ejecutas desde terminal/terminal emulator
	if os.getenv("TERM") or os.getenv("TERM_PROGRAM") or os.getenv("SSH_TTY"):
		return True

	# En Linux/X11/Wayland, DISPLAY o WAYLAND_DISPLAY suelen indicar entorno gráfico,
	# pero no garantizan que no haya terminal (puedes tener terminal dentro del X session).
	# Aquí asumimos: si no es TTY y hay DISPLAY -> probablemente lanzado desde GUI (doble clic).
	if os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"):
		return False

	# Fallback: si no está claro, devolvemos None
	return None

def get_timeouts() -> dict:
	"""
	Retorna timeouts configurables optimizados para las operaciones de Playwright
	"""
	config = load_config()
	timeouts = config.get("timeouts", {})

	return {
		"default": timeouts.get("default", 25000),        # 25 segundos (reducido de 30)
		"navigation": timeouts.get("navigation", 45000),  # 45 segundos (reducido de 60)
		"element": timeouts.get("element", 10000),        # 10 segundos (reducido de 15)
		"upload": timeouts.get("upload", 60000),          # 1 minuto (reducido de 2)
		"column_mapping": timeouts.get("column_mapping", 30000),  # 30s para mapeo específico
	}

def safe_goto(page: Page, url: str, timeout: int = 60000) -> bool:
	"""
	Navega a una URL de forma segura con manejo de errores detallado
	"""
	try:
		logging.info(f"🌐 Navegando a URL: {url}")
		logging.debug(f"⏱️ Timeout configurado: {timeout}ms")

		page.goto(url, timeout=timeout, wait_until="networkidle")

		logging.success(f"✅ Navegación exitosa a: {url}")
		return True
	except PWTimeoutError as e:
		logging.error(f"❌ PWTimeoutError navegando a {url}: {e}")
		logging.error(f"⏱️ Timeout configurado: {timeout}ms")
		print(f"Timeout navegando a {url}: {e}")
		return False
	except Exception as e:
		logging.error(f"❌ Error navegando a {url}: {e}")
		print(f"Error navegando a {url}: {e}")
		return False

def click_element(element):
	"""
	Hace clic en un elemento de forma segura con manejo de errores
	"""
	try:
		logging.debug("🖱️ Haciendo clic en elemento")
		element.click()
		logging.debug("✅ Clic realizado exitosamente")
		return True
	except PWTimeoutError as e:
		logging.error(f"❌ PWTimeoutError haciendo clic en elemento: {e}")
		print(f"Timeout haciendo clic en elemento: {e}")
		return False
	except Exception as e:
		logging.error(f"❌ Error haciendo clic en elemento: {e}")
		print(f"Error haciendo clic en elemento: {e}")
		return False