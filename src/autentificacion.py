from playwright.sync_api import Page, TimeoutError as PWTimeoutError
from .utils import load_config, get_timeouts, click_element, fill_field, retry
from .logger import get_logger

@retry(max_attempts=2, delay=1.0, exceptions=(PWTimeoutError, Exception))
def accept_cookies(page: Page):
	"""Acepta cookies si el botón está disponible"""
	click_element(page.get_by_role("button", name="Aceptar todas"))

@retry(max_attempts=3, delay=1.0, exceptions=(PWTimeoutError, Exception))
def fill_login_credentials(page: Page, username: str, password: str):
	"""Llena las credenciales de login"""
	fill_field(page.get_by_placeholder("Correo electrónico"), username)
	fill_field(page.get_by_placeholder("Contraseña"), password)
	click_element(page.locator('label[for="keepme-logged"]'))

@retry(max_attempts=3, delay=2.0, exceptions=(PWTimeoutError, Exception))
def submit_login(page: Page):
	"""Envía el formulario de login"""
	with page.expect_navigation(wait_until="domcontentloaded"):
		click_element(page.get_by_role("button", name="Entrar"))

@retry(max_attempts=2, delay=3.0, exceptions=(PWTimeoutError,))
def wait_for_dashboard(page: Page, timeout: int):
	"""Espera a que aparezca el dashboard después del login"""
	page.wait_for_selector("a[href*='/reports']", timeout=timeout)

def login(page: Page):
	"""Realiza login limpio y organizado"""
	logger = get_logger()
	logger.start_timer("login_process")
	
	config = load_config()
	timeouts = get_timeouts()
	
	username = config.get("user", "")
	password = config.get("password", "")
	url = config.get("url", "")
	
	logger.log_browser_action("Iniciando proceso de login", f"usuario: {username[:3]}***")
	
	# Esperar carga inicial
	try:
		page.wait_for_load_state("domcontentloaded", timeout=timeouts['page_load'])
		logger.log_success("login_process", "Página cargada correctamente")
	except PWTimeoutError:
		logger.log_warning("login_process", "Página tardó en cargar, continuando...")
	
	# Solo hacer login si no estamos ya en la página correcta
	if page.url != url:
		logger.start_timer("authentication")
		logger.log_browser_action("Realizando autenticación", f"URL actual: {page.url}")
		
		# Intentar aceptar cookies (puede fallar sin problema)
		try:
			accept_cookies(page)
			logger.log_success("authentication", "Cookies aceptadas")
		except Exception:
			logger.log_warning("authentication", "No se encontró el botón de cookies")

		page.wait_for_load_state("load")

		# Llenar credenciales
		logger.log_browser_action("Llenando credenciales")
		fill_login_credentials(page, username, password)

		# Enviar formulario
		logger.log_browser_action("Enviando formulario de login")
		submit_login(page)
		
		logger.end_timer("authentication")
	else:
		logger.log_success("login_process", "Sesión ya iniciada")
	
	# Verificar login exitoso
	logger.start_timer("login_verification")
	try:
		wait_for_dashboard(page, timeouts['elements'])
		logger.end_timer("login_verification")
		logger.end_timer("login_process")
		logger.log_success("login_process", "Login completado exitosamente")
	except PWTimeoutError:
		logger.log_warning("login_process", "Login incompleto - posible captcha")
		logger.logger.info("Resuelve el captcha manualmente en la ventana y presiona Enter aquí…")
		input()
		wait_for_dashboard(page, timeouts['long_operations'])
		logger.end_timer("login_verification")
		logger.end_timer("login_process")
		logger.log_success("login_process", "Login completado tras intervención manual")

	