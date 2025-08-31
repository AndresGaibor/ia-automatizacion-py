from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page
import yaml

# Lectura de archivo de configuracion YAML
with open('config.yaml', 'r') as file:
	config = yaml.safe_load(file)

username = config["user"]
password = config["password"]
url = config["url"]

def login(page: Page):
	# Esperar a que la página se cargue completamente antes de verificar URL
	try:
		page.wait_for_load_state("domcontentloaded", timeout=30000)
	except PWTimeoutError:
		print("Página tardó en cargar, continuando...")
	
	if(page.url != url):
		print("Realizando autenticación...")
		try:
			page.get_by_role("button", name="Aceptar todas").click();
		except PWTimeoutError:
			print("No se encontró el botón de cookies, continuando...")
			pass

		# page.get_by_role("link", name="Entra").click()
		page.get_by_placeholder("Correo electrónico").fill(username)
		page.get_by_placeholder("Contraseña").fill(password)
		page.locator('label[for="keepme-logged"]').click()

		# <input type="submit" value="Entrar" class="g-recaptcha signup-button" id="login-button" data-sitekey="6LeOaagZAAAAADEGihAZSe2cFNNTWgxfUM5NET9Z" data-callback="onSubmit" data-action="submit">
		with page.expect_navigation(wait_until="domcontentloaded"):
			page.get_by_role("button", name="Entrar").click()
	else:
		print("Sesión ya iniciada")
	
	try:
		page.wait_for_selector("a[href*='/reports']", timeout=15000)
		print("Login OK")
	except PWTimeoutError:
		print("Parece que no se completó el login (¿captcha?).")
		print("Resuelve el captcha manualmente en la ventana y presiona Enter aquí…")
		input()
		# Espera a que aparezca el enlace a informes
		page.wait_for_selector("a[href*='/reports']", timeout=20000)

	