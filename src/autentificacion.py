from playwright.sync_api import BrowserContext, TimeoutError as PWTimeoutError, Page
from .utils import load_config, storage_state_path, notify
from .logger import get_logger

logger = get_logger()

def esperar_carga_pagina(page: Page, timeout: int = 60_000):
    """Espera a que la página cargue completamente con manejo de timeout."""
    logger.info("⏳ Esperando carga de página", timeout=timeout)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        page.wait_for_load_state("networkidle", timeout=timeout)
        # Espera adicional para asegurar que la página esté completamente cargada
        page.wait_for_timeout(2000)
        logger.success("✅ Página cargada exitosamente")
    except Exception as e:
        logger.warning(f"Página tardó en cargar: {e}. Continuando...", error=str(e))

def aceptar_cookies(page: Page):
	"""Intenta aceptar cookies si el botón está presente."""
	logger.info("🍪 Intentando aceptar cookies")
	try:
		page.get_by_role("button", name="Aceptar todas").click(timeout=30_000)
		logger.success("✅ Cookies aceptadas exitosamente")
	except Exception as e:
		logger.info(f"No se encontró el botón de cookies: {e}. Continuando...", error=str(e))

def autenticado(page: Page) -> bool:
	"""Verifica si el usuario ya está autenticado."""
	logger.info("🔐 Verificando estado de autenticación")
	try:
		
		btn_herramientas = page.get_by_role("navigation").get_by_role("link", name="Ir a la herramienta")
		
		esperar_carga_pagina(page)
		
		btn_herramientas.click(timeout=30_000)

		esperar_carga_pagina(page)
		
		logger.success("✅ Usuario ya autenticado")
		return True
	except PWTimeoutError:
		logger.info("🔓 No se encontró el botón 'Entra', asumiendo que ya está autenticado")
		return False

def login(page: Page, context: BrowserContext):
	"""Realiza login leyendo la configuración fresca desde config.yaml."""
	logger.info("🔐 Iniciando proceso de autenticación")
	config = load_config()
	username = config.get("user", "")
	password = config.get("password", "")
	url = config.get("url", "")
	url_base = config.get("url_base", "")

	# Validar que las credenciales estén configuradas
	if not username or username == "usuario@correo.com":
		logger.error("❌ Usuario no configurado en config.yaml", user=username)
		notify("Error de Configuración", "Error: Usuario no configurado. Edite config.yaml con su email de Acumbamail.", "error")
		raise ValueError("Usuario no configurado en config.yaml")
	
	if not password or password == "clave":
		logger.error("❌ Contraseña no configurada en config.yaml", user=username)
		notify("Error de Configuración", "Error: Contraseña no configurada. Edite config.yaml con su contraseña de Acumbamail.", "error")
		raise ValueError("Contraseña no configurada en config.yaml")

	logger.info(f"🔑 Iniciando proceso de login para usuario: {username}")
	
	try:
		logger.info(f"🌐 Navegando a URL: {url}")
		page.goto(url, timeout=60_000)
	except Exception as e:
		logger.error(f"❌ Error conectando a Acumbamail: {e}", url=url, error=str(e))
		notify("Error de Conexión", f"Error: No se pudo conectar a Acumbamail: {e}", "error")
		raise

	esperar_carga_pagina(page)

	if f"{url_base}/" != page.url:
		logger.success("✅ Ya estás en la página principal, guardando estado de sesión...")
		context.storage_state(path=storage_state_path())
		page.wait_for_timeout(5_000)
		logger.info("🔄 Sesion guardada exitosamente")
		return

	logger.info("🍪 Aceptando cookies si están presentes")
	aceptar_cookies(page)

	if autenticado(page):
		logger.success("✅ Ya estás autenticado.")
		notify("Sesión", "Ya está autenticado en Acumbamail", "info")
	else:
		logger.info("🔐 No estás autenticado. Procediendo a login...")
		notify("Autenticación", "Credenciales requeridas, iniciando login", "info")

		try:
			logger.info("🖱️ Haciendo clic en botón de entrada")
			btn_entrar = page.get_by_role("link", name="Entra")
			btn_entrar.click()
			page.wait_for_load_state("networkidle")

			logger.info("📝 Rellenando formulario de login...")
			page.get_by_role("textbox", name="Correo electrónico").fill(username)
			page.get_by_role("textbox", name="Contraseña").fill(password)
			page.locator('label[for="keepme-logged"]').click()

			logger.info("🚀 Enviando formulario de login...")
			with page.expect_navigation(wait_until="domcontentloaded"):
				page.get_by_role("button", name="Entrar").click()
				esperar_carga_pagina(page)

			logger.success("✅ Login completado exitosamente")
			notify("Autenticación", "Login completado exitosamente", "info")
			
		except Exception as e:
			logger.error(f"❌ Error durante el login: {e}", error=str(e))
			notify("Error de Login", f"Error durante el login: {e}. Verifique sus credenciales.", "error")
			raise

	logger.info("💾 Guardando estado de sesión...")
	notify("Sesión", "Guardando estado de sesión", "info")
	context.storage_state(path=storage_state_path())

	# Espera adicional para asegurar que la sesión esté completamente establecida
	page.wait_for_timeout(3000)
	logger.success("✅ Estado de sesión guardado correctamente")
