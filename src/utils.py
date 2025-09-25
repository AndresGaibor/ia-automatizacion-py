"""
Funciones utilitarias compartidas para automatización.
"""

import os
import sys
import re
from playwright.sync_api import BrowserContext

try:
    from .logger import get_logger
except ImportError:
    from src.logger import get_logger

logger = get_logger()

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
	"""Crea contexto del navegador con configuración de sesión."""
	storage_state = storage_state_path() if os.path.exists(storage_state_path()) else None
	context = browser.new_context(
		user_agent=REAL_UA,
		viewport={'width': 1366, 'height': 768},
		locale='es-ES',
		timezone_id='Europe/Madrid',
		ignore_https_errors=True,
		storage_state=storage_state,
	)

	# Configurar timeouts básicos
	context.set_default_timeout(120000)  # 2 minutos
	context.set_default_navigation_timeout(120000)  # 2 minutos

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

def navegar_a_reportes(page: Page):
	"""
	Navega a la sección de reportes
	"""
	page.click("a[href*='/reports']")
	page.wait_for_load_state('networkidle')

def obtener_total_paginas(page: Page) -> int:
	"""
	Obtiene el número total de páginas de reportes calculando desde elementos totales
	"""
	try:
		print("🔍 Optimizando elementos por página...")

		# Intentar optimizar a 200 elementos por página primero
		items_selector = page.locator('select').filter(has=page.locator('option', has_text="15"))
		if items_selector.count() > 0:
			# Seleccionar 200 elementos por página para optimizar
			ultimo_option = items_selector.locator('option').last
			value_ultimo_option = ultimo_option.get_attribute('value')
			items_selector.select_option(value=value_ultimo_option)
			# Usar domcontentloaded en lugar de networkidle para mayor velocidad
			page.wait_for_load_state("domcontentloaded", timeout=15000)
			page.wait_for_timeout(2000)  # Espera mínima para que se actualice
			print("✅ Optimizado a 200 elementos por página")

	except Exception as e:
		print(f"⚠️ Error optimizando items por página: {e}")

	# Calcular páginas usando elementos totales
	try:
		# Buscar el total de elementos en el texto "de X elementos"
		elementos_info = page.locator("span.font-color-darkblue-1").filter(
			has_text=re.compile(r"elementos", re.IGNORECASE)
		)
		info_count = elementos_info.count()
		if info_count > 0:
			# Si hay varios, tomar el último (suele ser el de la paginación)
			target = elementos_info.last if info_count > 1 else elementos_info.first
			total_elementos_texto = target.inner_text(timeout=5000)

			# Extraer el último número del texto (e.g., "de 1.234 elementos")
			numeros = re.findall(r"\d[\d\.,]*", total_elementos_texto)
			if not numeros:
				raise ValueError(f"No se encontraron números en: {total_elementos_texto}")
			total_elementos = int(numeros[-1].replace('.', '').replace(',', ''))

			# Obtener elementos por página actual
			items_por_pagina = 200  # Por defecto después de optimización
			try:
				# Algunos navegadores no mantienen el atributo [selected], usar :checked como alternativa
				select_actual = page.locator('select option[selected], select option:checked')
				if select_actual.count() > 0:
					option_value = select_actual.first.get_attribute('value')
					if option_value and 'items_per_page=' in option_value:
						items_text = option_value.split('items_per_page=')[1].split('&')[0]
						items_por_pagina = int(items_text)
			except Exception:
				pass

			# Calcular total de páginas
			total_paginas = (total_elementos + items_por_pagina - 1) // items_por_pagina
			print(f"📊 {total_elementos} elementos total, {items_por_pagina} por página = {total_paginas} páginas")
			return max(1, total_paginas)

	except Exception as e:
		print(f"⚠️ Error calculando desde elementos totales: {e}")

	# Fallback: buscar navegación tradicional
	try:
		navegacion = page.locator('ul').filter(has=page.locator('li').locator('a', has_text="1")).last
		if navegacion.count() > 0:
			ultimo_elemento = navegacion.locator('li').last
			texto = ultimo_elemento.inner_text(timeout=5000)
			if texto.isdigit():
				print(f"📄 Páginas encontradas por navegación: {texto}")
				return int(texto)
	except Exception:
		pass

	print("⚠️ No se pudo determinar total de páginas, usando 1")
	return 1

def obtener_total_paginas_rapido(page: Page) -> int:
	"""
	Versión rápida para obtener total de páginas sin optimizar items por página.
	Útil cuando sabemos que hay pocos elementos o queremos máxima velocidad.
	"""
	try:
		# Solo buscar navegación, sin intentar optimizar items por página
		navegacion = page.locator('ul').filter(has=page.locator('li').locator('a', has_text="1")).last

		if navegacion.count() > 0:
			ultimo_elemento = navegacion.locator('li').last
			texto = ultimo_elemento.inner_text(timeout=3000)

			if texto.isdigit():
				return int(texto)

		return 1
	except Exception:
		return 1

def navegar_siguiente_pagina(page: Page, pagina_actual: int) -> bool:
	"""
	Navega a la siguiente página si existe (optimizado)
	"""
	siguiente_pagina = pagina_actual + 1

	try:
		# Buscar navegación con timeout reducido
		navegacion = page.locator('ul').filter(
			has=page.locator('li').locator('a', has_text=f"{siguiente_pagina}")
		).last

		enlace = navegacion.locator('a', has_text=f"{siguiente_pagina}").first

		if enlace.count() > 0:
			# Timeout más corto para el enlace
			enlace.wait_for(timeout=8000)
			enlace.click()
			# Usar domcontentloaded para mayor velocidad
			page.wait_for_load_state("domcontentloaded", timeout=15000)
			# Pequeña espera para asegurar que la tabla se actualiza
			page.wait_for_timeout(1500)
			print(f"➡️ Navegando a página {siguiente_pagina}...")
			return True
		else:
			return False
	except Exception as e:
		print(f"❌ Error navegando a página {siguiente_pagina}: {e}")
		return False

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
	Retorna timeouts configurables para las operaciones de Playwright
	"""
	config = load_config()
	timeouts = config.get("timeouts", {})
	
	return {
		"default": timeouts.get("default", 30000),        # 30 segundos
		"navigation": timeouts.get("navigation", 60000),  # 60 segundos  
		"element": timeouts.get("element", 15000),        # 15 segundos
		"upload": timeouts.get("upload", 120000),         # 2 minutos
	}

def safe_goto(page: Page, url: str, timeout: int = 60000) -> bool:
	"""
	Navega a una URL de forma segura con manejo de errores
	"""
	try:
		page.goto(url, timeout=timeout, wait_until="networkidle")
		return True
	except Exception as e:
		print(f"Error navegando a {url}: {e}")
		return False

def click_element(element):
	"""
	Hace clic en un elemento de forma segura con manejo de errores
	"""
	try:
		element.click()
		return True
	except Exception as e:
		print(f"Error haciendo clic en elemento: {e}")
		return False