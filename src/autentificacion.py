from playwright.sync_api import BrowserContext, TimeoutError as PWTimeoutError, Page
from .utils import load_config, storage_state_path, notify

def esperar_carga_pagina(page: Page, timeout: int = 60_000):
    """Espera a que la página cargue completamente con manejo de timeout."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        page.wait_for_load_state("networkidle", timeout=timeout)
        # Espera adicional para asegurar que la página esté completamente cargada
        page.wait_for_timeout(2000)
    except Exception as e:
        print(f"Página tardó en cargar: {e}. Continuando...")

def aceptar_cookies(page: Page):
	"""Intenta aceptar cookies si el botón está presente."""
	try:
		page.get_by_role("button", name="Aceptar todas").click(timeout=30_000)
	except Exception as e:
		print(f"No se encontró el botón de cookies: {e}. Continuando...")

def autenticado(page: Page) -> bool:
	"""Verifica si el usuario ya está autenticado."""
	try:
		
		btn_herramientas = page.get_by_role("navigation").get_by_role("link", name="Ir a la herramienta")
		
		esperar_carga_pagina(page)
		
		btn_herramientas.click(timeout=30_000)

		esperar_carga_pagina(page)
		
		return True
	except PWTimeoutError:
		print("No se encontró el botón 'Entra', asumiendo que ya está autenticado.")
		return False

def login(page: Page, context: BrowserContext):
	"""Realiza login leyendo la configuración fresca desde config.yaml."""
	config = load_config()
	username = config.get("user", "")
	password = config.get("password", "")
	url = config.get("url", "")
	url_base = config.get("url_base", "")

	# Validar que las credenciales estén configuradas
	if not username or username == "usuario@correo.com":
		notify("Error de Configuración", "Error: Usuario no configurado. Edite config.yaml con su email de Acumbamail.", "error")
		raise ValueError("Usuario no configurado en config.yaml")
	
	if not password or password == "clave":
		notify("Error de Configuración", "Error: Contraseña no configurada. Edite config.yaml con su contraseña de Acumbamail.", "error")
		raise ValueError("Contraseña no configurada en config.yaml")

	print("🔑 Iniciando proceso de login...")
	
	try:
		page.goto(url, timeout=60_000)
	except Exception as e:
		notify("Error de Conexión", f"Error: No se pudo conectar a Acumbamail: {e}", "error")
		raise

	esperar_carga_pagina(page)

	if f"{url_base}/" != page.url:
		print("✅ Ya estás en la página principal, guardando estado de sesión...")
		context.storage_state(path=storage_state_path())
		page.wait_for_timeout(5_000)
		return

	aceptar_cookies(page)

	if autenticado(page):
		print("✅ Ya estás autenticado.")
		notify("Sesión", "Ya está autenticado en Acumbamail", "info")
	else:
		print("🔐 No estás autenticado. Procediendo a login...")
		notify("Autenticación", "Credenciales requeridas, iniciando login", "info")

		try:
			btn_entrar = page.get_by_role("link", name="Entra")
			btn_entrar.click()
			page.wait_for_load_state("networkidle")

			print("📝 Rellenando formulario de login...")
			page.get_by_role("textbox", name="Correo electrónico").fill(username)
			page.get_by_role("textbox", name="Contraseña").fill(password)
			page.locator('label[for="keepme-logged"]').click()

			print("🚀 Enviando formulario de login...")
			with page.expect_navigation(wait_until="domcontentloaded"):
				page.get_by_role("button", name="Entrar").click()
				esperar_carga_pagina(page)

			print("✅ Login completado exitosamente")
			notify("Autenticación", "Login completado exitosamente", "info")
			
		except Exception as e:
			notify("Error de Login", f"Error durante el login: {e}. Verifique sus credenciales.", "error")
			raise

	print("💾 Guardando estado de sesión...")
	notify("Sesión", "Guardando estado de sesión", "info")
	context.storage_state(path=storage_state_path())

	# Espera adicional para asegurar que la sesión esté completamente establecida
	page.wait_for_timeout(3000)
	print("✅ Estado de sesión guardado correctamente")
