"""
Funciones utilitarias compartidas para automatización.
"""

import os
import sys
import re
from playwright.sync_api import BrowserContext

try:
    from ..logging import get_logger
except ImportError:
    try:
        from .logger import get_logger
    except ImportError:
        from src.logger import get_logger

logger = get_logger()

def _early_project_root() -> str:
	if getattr(sys, "frozen", False):
		return os.path.dirname(sys.executable)
	# From src/shared/utils/legacy_utils.py, go up 3 levels to reach project root
	return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

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
	# From src/shared/utils/legacy_utils.py, go up 3 levels to reach project root
	return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

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
	logger.info("🌐 Creando contexto de navegador", extraccion_oculta=extraccion_oculta)

	storage_state = storage_state_path() if os.path.exists(storage_state_path()) else None
	if storage_state:
		logger.debug("💾 Usando estado de sesión guardado", path=storage_state)
	else:
		logger.debug("🆕 Creando contexto sin sesión guardada")

	context = browser.new_context(
		user_agent=REAL_UA,
		viewport={'width': 1366, 'height': 768},
		locale='es-ES',
		timezone_id='Europe/Madrid',
		ignore_https_errors=True,
		storage_state=storage_state,
	)

	# Configurar timeouts básicos
	logger.debug("⏱️ Configurando timeouts del contexto: 120s")
	context.set_default_timeout(120000)  # 2 minutos
	context.set_default_navigation_timeout(120000)  # 2 minutos

	logger.success("✅ Contexto de navegador creado exitosamente")
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
	logger.info("🚀 Configurando navegador Chromium", headless=extraccion_oculta)
	ensure_playwright_browsers_path()

	try:
		logger.debug("🔧 Lanzando Chromium con configuración anti-detección")
		browser = p.chromium.launch(
			headless=extraccion_oculta,
			args=[
				"--disable-blink-features=AutomationControlled",
				"--no-sandbox",
				# "--window-position=2000,0",
					"--window-size=1280,800",
			],
		)
		logger.success("✅ Navegador Chromium lanzado exitosamente")
		return browser
	except PWError as e:
		msg = str(e)
		logger.error("❌ Error lanzando navegador", error=msg)
		if "Executable doesn't exist" in msg or "playwright install" in msg:
			logger.warning("⚠️ Chromium no instalado, intentando instalación automática")
			try:
				notify("Playwright", "Descargando Chromium (solo la primera vez)...")
			except Exception:
				pass
			# Ejecutar el CLI sin cerrar el proceso
			logger.info("📥 Instalando Chromium automáticamente...")
			from playwright.__main__ import main as playwright_main
			old_argv = sys.argv[:]
			try:
				for args in (["playwright", "install", "chromium"],
							["playwright", "install", "--force", "chromium"]):
					try:
						logger.debug(f"🔧 Intentando instalación con: {' '.join(args)}")
						sys.argv = args
						ensure_playwright_browsers_path()
						playwright_main()
						logger.success("✅ Chromium instalado exitosamente")
						break  # instalación OK
					except SystemExit as se:
						# Evitar que cierre la app; solo propagar si es error real
						if se.code not in (0, None):
							logger.error(f"❌ Error en instalación: código {se.code}")
							raise
					except Exception as e:
						logger.warning(f"⚠️ Intento de instalación falló: {e}")
						# Intentará con --force en el siguiente ciclo
						continue
			finally:
				sys.argv = old_argv

			# Reintento de lanzamiento tras instalar
			logger.info("🔄 Reintentando lanzamiento de Chromium tras instalación")
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
	logger.info("📊 Navegando a sección de reportes")
	try:
		page.click("a[href*='/reports']")
		logger.debug("✅ Click en enlace de reportes ejecutado")
		page.wait_for_load_state('networkidle')
		logger.success("✅ Navegación a reportes completada", url=page.url)
	except Exception as e:
		logger.error("❌ Error navegando a reportes", error=str(e))
		raise

def obtener_total_paginas(page: Page) -> int:
	"""
	Obtiene el número total de páginas de reportes calculando desde elementos totales.
	Optimiza automáticamente a la máxima cantidad de elementos por página disponible.
	"""
	logger.info("📊 Iniciando cálculo de total de páginas con optimización")
	items_por_pagina = 15  # Valor por defecto
	total_elementos = None

	# PASO 1: Obtener el total de elementos ANTES de cambiar el selector
	# Esto evita el error "Execution context was destroyed" que ocurre después de la navegación
	logger.debug("🔍 PASO 1: Obteniendo total de elementos")
	try:
		# Buscar el total de elementos en el texto "de X elementos"
		elementos_info = page.locator("text=/de \\d+ elementos/i")

		if elementos_info.count() > 0:
			total_elementos_texto = elementos_info.first.inner_text(timeout=5000)
			logger.debug("📋 Texto de elementos encontrado", texto=total_elementos_texto)

			# Extraer el número del texto (e.g., "de 396 elementos")
			match = re.search(r'de\s+(\d+)\s+elementos', total_elementos_texto, re.IGNORECASE)
			if match:
				total_elementos = int(match.group(1))
				logger.info(f"✅ Total de elementos extraído: {total_elementos}")
			else:
				# Fallback: extraer cualquier número
				numeros = re.findall(r"\d+", total_elementos_texto)
				if numeros:
					total_elementos = int(numeros[-1])
					logger.warning(f"⚠️ Total extraído con fallback regex: {total_elementos}")

	except Exception as e:
		logger.error("❌ Error obteniendo total de elementos", error=str(e))
		print(f"⚠️ Error obteniendo total de elementos: {e}")

	# PASO 2: Optimizar items por página (esto causa navegación/recarga)
	logger.debug("🔍 PASO 2: Optimizando items por página")
	try:
		print("🔍 Optimizando elementos por página...")

		# Buscar el selector de items por página
		items_selector = page.locator('select').filter(has=page.locator('option', has_text="15"))
		if items_selector.count() > 0:
			logger.debug("✅ Selector de items encontrado")
			# Obtener la última opción (máximo disponible)
			ultimo_option = items_selector.locator('option').last
			value_ultimo_option = ultimo_option.get_attribute('value')
			text_ultimo_option = ultimo_option.inner_text()

			logger.debug(f"🎯 Seleccionando opción máxima: {text_ultimo_option} items")
			# Seleccionar la última opción
			items_selector.select_option(value=value_ultimo_option)

			# Esperar a que la página se recargue completamente con los nuevos items
			# Usar networkidle para asegurar que la página está completamente cargada
			logger.debug("⏳ Esperando recarga de página (networkidle)...")
			page.wait_for_load_state("networkidle", timeout=30000)
			# Espera adicional para que la tabla se renderice completamente
			page.wait_for_timeout(2000)

			print(f"✅ Optimizado a {text_ultimo_option} elementos por página")
			items_por_pagina = int(text_ultimo_option)
			logger.success(f"✅ Optimización completada: {items_por_pagina} elementos por página")

	except Exception as e:
		logger.error("❌ Error optimizando items por página", error=str(e))
		print(f"⚠️ Error optimizando items por página: {e}")

	# PASO 3: Calcular páginas usando el total de elementos obtenido antes de la navegación
	logger.debug("🔍 PASO 3: Calculando total de páginas")
	if total_elementos is not None:
		# Calcular total de páginas
		total_paginas = (total_elementos + items_por_pagina - 1) // items_por_pagina
		print(f"📊 {total_elementos} elementos total, {items_por_pagina} por página = {total_paginas} páginas")
		logger.success(f"✅ Total de páginas calculado: {total_paginas}",
		              total_elementos=total_elementos,
		              items_por_pagina=items_por_pagina)
		return max(1, total_paginas)

	# Fallback: buscar navegación tradicional
	logger.debug("🔄 Intentando método fallback: navegación tradicional")
	try:
		navegacion = page.locator('ul').filter(has=page.locator('li').locator('a', has_text="1")).last
		if navegacion.count() > 0:
			ultimo_elemento = navegacion.locator('li').last
			texto = ultimo_elemento.inner_text(timeout=5000)
			if texto.isdigit():
				print(f"📄 Páginas encontradas por navegación: {texto}")
				logger.info(f"✅ Páginas encontradas por navegación fallback: {texto}")
				return int(texto)
	except Exception as e:
		logger.debug("⚠️ Método fallback también falló", error=str(e))
		pass

	logger.warning("⚠️ No se pudo determinar total de páginas, usando 1 por defecto")
	print("⚠️ No se pudo determinar total de páginas, usando 1")
	return 1

def obtener_total_paginas_rapido(page: Page) -> int:
	"""
	Versión rápida para obtener total de páginas sin optimizar items por página.
	Útil cuando sabemos que hay pocos elementos o queremos máxima velocidad.
	"""
	logger.debug("⚡ Obteniendo total de páginas (modo rápido, sin optimización)")
	try:
		# Solo buscar navegación, sin intentar optimizar items por página
		navegacion = page.locator('ul').filter(has=page.locator('li').locator('a', has_text="1")).last

		if navegacion.count() > 0:
			ultimo_elemento = navegacion.locator('li').last
			texto = ultimo_elemento.inner_text(timeout=3000)

			if texto.isdigit():
				logger.info(f"✅ Total de páginas encontrado (rápido): {texto}")
				return int(texto)

		logger.debug("⚠️ No se encontró navegación, retornando 1")
		return 1
	except Exception as e:
		logger.warning("⚠️ Error en obtener_total_paginas_rapido, retornando 1", error=str(e))
		return 1

def navegar_siguiente_pagina(page: Page, pagina_actual: int) -> bool:
	"""
	Navega a la siguiente página si existe (optimizado)
	"""
	siguiente_pagina = pagina_actual + 1
	logger.debug(f"➡️ Intentando navegar a página {siguiente_pagina}", pagina_actual=pagina_actual)

	try:
		# Buscar navegación con timeout reducido
		navegacion = page.locator('ul').filter(
			has=page.locator('li').locator('a', has_text=f"{siguiente_pagina}")
		).last

		enlace = navegacion.locator('a', has_text=f"{siguiente_pagina}").first

		if enlace.count() > 0:
			logger.debug(f"✅ Enlace a página {siguiente_pagina} encontrado")
			# Timeout más corto para el enlace
			enlace.wait_for(timeout=8000)
			enlace.click()
			logger.debug("⏳ Esperando carga de página (domcontentloaded)...")
			# Usar domcontentloaded para mayor velocidad
			page.wait_for_load_state("domcontentloaded", timeout=15000)
			# Pequeña espera para asegurar que la tabla se actualiza
			page.wait_for_timeout(1500)
			print(f"➡️ Navegando a página {siguiente_pagina}...")
			logger.success(f"✅ Navegación a página {siguiente_pagina} completada", url=page.url)
			return True
		else:
			logger.debug(f"⚠️ No se encontró enlace a página {siguiente_pagina}")
			return False
	except Exception as e:
		print(f"❌ Error navegando a página {siguiente_pagina}: {e}")
		logger.error(f"❌ Error navegando a página {siguiente_pagina}", error=str(e))
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
	logger.debug("🌐 Navegando de forma segura", url=url, timeout=timeout)
	try:
		page.goto(url, timeout=timeout, wait_until="networkidle")
		logger.success("✅ Navegación segura completada", url=url)
		return True
	except Exception as e:
		print(f"Error navegando a {url}: {e}")
		logger.error("❌ Error en navegación segura", url=url, error=str(e))
		return False

def click_element(element):
	"""
	Hace clic en un elemento de forma segura con manejo de errores
	"""
	logger.debug("🖱️ Haciendo clic en elemento de forma segura")
	try:
		element.click()
		logger.debug("✅ Click ejecutado exitosamente")
		return True
	except Exception as e:
		print(f"Error haciendo clic en elemento: {e}")
		logger.error("❌ Error haciendo clic en elemento", error=str(e))
		return False

def is_on_login_page(page: Page) -> bool:
	"""
	Verifica si la página actual es la página de login.

	Args:
		page: Página de Playwright a verificar

	Returns:
		True si está en la página de login, False en caso contrario
	"""
	try:
		current_url = page.url
		is_login = '/login/' in current_url or '/login' in current_url.lower()

		if is_login:
			logger.warning("⚠️ Redirección a login detectada", url=current_url)

		return is_login
	except Exception as e:
		logger.error("❌ Error verificando página de login", error=str(e))
		return False

def validate_session(page: Page) -> bool:
	"""
	Valida si la sesión actual sigue activa navegando a una página de prueba.

	Args:
		page: Página de Playwright para validar

	Returns:
		True si la sesión es válida, False si expiró
	"""
	try:
		logger.info("🔍 Validando sesión activa...")

		# Guardar URL actual para regresar después
		current_url = page.url

		# Navegar a página de prueba (reportes)
		test_url = "https://acumbamail.com/report/campaign/"
		page.goto(test_url, wait_until="networkidle", timeout=30000)

		# Verificar si fue redirigido a login
		if is_on_login_page(page):
			logger.warning("⚠️ Sesión expirada - se requiere re-autenticación")
			return False

		logger.success("✅ Sesión válida")

		# Intentar regresar a la URL original si es diferente
		if current_url and current_url != test_url:
			try:
				page.goto(current_url, wait_until="networkidle", timeout=30000)
			except Exception:
				pass  # No es crítico si falla

		return True

	except Exception as e:
		logger.error("❌ Error validando sesión", error=str(e))
		return False