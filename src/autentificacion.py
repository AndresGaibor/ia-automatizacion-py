from playwright.sync_api import Page, TimeoutError as PWTimeoutError
from .utils import load_config, get_timeouts, click_element, fill_field, retry
from .logger import get_logger as get_old_logger
from .enhanced_logger import get_auth_logger, log_operation, log_errors

@retry(max_attempts=2, delay=1.0, exceptions=(PWTimeoutError, Exception))
@log_operation("accept_cookies", "auth")
def accept_cookies(page: Page):
	"""Acepta cookies si el botón está disponible"""
	logger = get_auth_logger()
	logger.log_browser_action("Intentando aceptar cookies")
	try:
		click_element(page.get_by_role("button", name="Aceptar todas"))
		logger.info("✅ Cookies aceptadas exitosamente")
	except Exception as e:
		logger.warning(f"No se pudo aceptar cookies: {e}")
		raise

@retry(max_attempts=3, delay=1.0, exceptions=(PWTimeoutError, Exception))
@log_operation("fill_credentials", "auth")
def fill_login_credentials(page: Page, username: str, password: str):
	"""Llena las credenciales de login"""
	logger = get_auth_logger()
	logger.info(f"Llenando credenciales para usuario: {username[:3]}***", context={"username_prefix": username[:3]})

	try:
		fill_field(page.get_by_placeholder("Correo electrónico"), username)
		logger.debug("Campo de email completado")

		fill_field(page.get_by_placeholder("Contraseña"), password)
		logger.debug("Campo de contraseña completado")

		click_element(page.locator('label[for="keepme-logged"]'))
		logger.debug("Opción 'mantener sesión' seleccionada")

		logger.info("✅ Credenciales llenadas exitosamente")
	except Exception as e:
		logger.error("Error llenando credenciales", error=e, context={"username": username[:3] + "***"})
		raise

@retry(max_attempts=3, delay=2.0, exceptions=(PWTimeoutError, Exception))
@log_operation("submit_login", "auth")
def submit_login(page: Page):
	"""Envía el formulario de login"""
	logger = get_auth_logger()
	logger.log_browser_action("Enviando formulario de login")

	try:
		with page.expect_navigation(wait_until="domcontentloaded"):
			click_element(page.get_by_role("button", name="Entrar"))
		logger.info("✅ Formulario de login enviado exitosamente")
	except Exception as e:
		logger.error("Error enviando formulario de login", error=e)
		raise

@retry(max_attempts=2, delay=3.0, exceptions=(PWTimeoutError,))
@log_operation("wait_dashboard", "auth")
def wait_for_dashboard(page: Page, timeout: int):
	"""Espera a que aparezca el dashboard después del login"""
	logger = get_auth_logger()
	logger.info(f"Esperando dashboard (timeout: {timeout}ms)", context={"timeout_ms": timeout})

	try:
		page.wait_for_selector("a[href*='/reports']", timeout=timeout)
		logger.info("✅ Dashboard cargado exitosamente")
	except PWTimeoutError as e:
		logger.warning(f"Timeout esperando dashboard después de {timeout}ms")
		raise
	except Exception as e:
		logger.error("Error esperando dashboard", error=e, context={"timeout_ms": timeout})
		raise

def login(page: Page):
	"""Realiza login limpio y organizado"""
	auth_logger = get_auth_logger()
	old_logger = get_old_logger()  # Mantener compatibilidad

	with auth_logger.operation("full_login_process") as op:
		config = load_config()
		timeouts = get_timeouts()

		username = config.get("user", "")
		password = config.get("password", "")
		url = config.get("url", "")

		auth_logger.info(f"Iniciando proceso de login para usuario: {username[:3]}***",
						context={"username_prefix": username[:3], "target_url": url})

		# Mantener compatibilidad con logger anterior
		old_logger.start_timer("login_process")
		old_logger.log_browser_action("Iniciando proceso de login", f"usuario: {username[:3]}***")
	
		# Esperar carga inicial
		try:
			auth_logger.info("Esperando carga inicial de página")
			page.wait_for_load_state("domcontentloaded", timeout=timeouts['page_load'])
			auth_logger.info("✅ Página cargada correctamente")
			old_logger.log_success("login_process", "Página cargada correctamente")
		except PWTimeoutError:
			auth_logger.warning("Página tardó en cargar, continuando...")
			old_logger.log_warning("login_process", "Página tardó en cargar, continuando...")
	
		# Solo hacer login si no estamos ya en la página correcta
		if page.url != url:
			auth_logger.info(f"Requiere autenticación - URL actual: {page.url}")
			old_logger.start_timer("authentication")
			old_logger.log_browser_action("Realizando autenticación", f"URL actual: {page.url}")

			# Intentar aceptar cookies (puede fallar sin problema)
			try:
				accept_cookies(page)
				auth_logger.info("✅ Cookies aceptadas")
				old_logger.log_success("authentication", "Cookies aceptadas")
			except Exception as e:
				auth_logger.warning(f"No se encontró el botón de cookies: {e}")
				old_logger.log_warning("authentication", "No se encontró el botón de cookies")

			page.wait_for_load_state("load")

			# Llenar credenciales
			auth_logger.log_browser_action("Llenando credenciales")
			old_logger.log_browser_action("Llenando credenciales")
			fill_login_credentials(page, username, password)

			# Enviar formulario
			auth_logger.log_browser_action("Enviando formulario de login")
			old_logger.log_browser_action("Enviando formulario de login")
			submit_login(page)

			auth_logger.info("✅ Proceso de autenticación completado")
			old_logger.end_timer("authentication")
		else:
			auth_logger.info("✅ Sesión ya iniciada - no requiere login")
			old_logger.log_success("login_process", "Sesión ya iniciada")
	
		# Verificar login exitoso
		auth_logger.info("Verificando login exitoso")
		old_logger.start_timer("login_verification")
		try:
			wait_for_dashboard(page, timeouts['elements'])
			auth_logger.info("✅ Login completado exitosamente")
			old_logger.end_timer("login_verification")
			old_logger.end_timer("login_process")
			old_logger.log_success("login_process", "Login completado exitosamente")
		except PWTimeoutError:
			auth_logger.warning("Login incompleto - posible captcha detectado")
			old_logger.log_warning("login_process", "Login incompleto - posible captcha")
			auth_logger.info("🔐 Intervención manual requerida - resuelve el captcha")
			old_logger.logger.info("Resuelve el captcha manualmente en la ventana y presiona Enter aquí…")
			input()
			wait_for_dashboard(page, timeouts['long_operations'])
			auth_logger.info("✅ Login completado tras intervención manual")
			old_logger.end_timer("login_verification")
			old_logger.end_timer("login_process")
			old_logger.log_success("login_process", "Login completado tras intervención manual")

	