import logging
from playwright.sync_api import BrowserContext, TimeoutError as PWTimeoutError, Page
from .utils import load_config, storage_state_path
from .shared.logging.logger import get_logger
from .core.authentication.exceptions import CookiePopupError, AuthenticationFailedError, SessionSaveError

logger = get_logger()

def esperar_carga_pagina(page: Page, timeout: int = 45_000, use_networkidle: bool = False):
    """
    Espera a que la página cargue completamente.

    Args:
        page: Página de Playwright
        timeout: Timeout en milisegundos
        use_networkidle: Si True, espera networkidle además de domcontentloaded (más lento pero más seguro)
    """
    logger.info("⏳ Esperando carga de página", timeout=timeout, networkidle=use_networkidle)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)

        if use_networkidle:
            # Esperar networkidle para conexiones lentas
            page.wait_for_load_state("networkidle", timeout=timeout)
            logger.success("✅ Página cargada exitosamente (con networkidle)")
        else:
            logger.success("✅ Página cargada exitosamente")
    except Exception as e:
        logger.warning(f"Página tardó en cargar: {e}. Continuando...", error=str(e))

def manejar_popup_cookies(page: Page, agresivo: bool = True):
	"""
	Maneja el popup de cookies con enfoque agresivo según la preferencia del usuario.

	Args:
		page: Página de Playwright
		agresivo: Si True, intenta múltiples estrategias con reintentos y esperas largas

	Raises:
		CookiePopupError: Si se detecta popup pero no se puede manejar
	"""
	logger.info("🍪 Iniciando manejo de popup de cookies", agresivo=agresivo)

	# Diferentes estrategias de selectores para encontrar el botón de cookies
	selectores_aceptar = [
		# Prioridad alta: botón por rol y texto específico
		{'type': 'role', 'selector': "button", 'name': "Aceptar todas"},
		{'type': 'role', 'selector': "button", 'name': "Aceptar"},
		{'type': 'role', 'selector': "button", 'name': "Accept all"},
		{'type': 'role', 'selector': "button", 'name': "Accept"},

		# Prioridad media: selectores CSS comunes
		{'type': 'css', 'selector': "button[data-testid='accept-all']"},
		{'type': 'css', 'selector': "button[id*='accept']"},
		{'type': 'css', 'selector': "button[class*='accept']"},
		{'type': 'css', 'selector': "a[data-cy='accept-cookies']"},

		# Prioridad baja: selectores XPath como último recurso
		{'type': 'xpath', 'selector': "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceptar todas')]"},
		{'type': 'xpath', 'selector': "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]"},
		{'type': 'xpath', 'selector': "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceptar')]"},
	]

	max_reintentos = 3 if agresivo else 1
	timeout_base = 10000 if agresivo else 3000  # 10s vs 3s

	for intento in range(max_reintentos):
		logger.debug(f"🔄 Intento {intento + 1}/{max_reintentos} para manejar cookies")

		# Primero verificar si hay algún popup de cookies presente
		popup_detectado = False
		try:
			# Buscar indicadores comunes de popup de cookies
			indicadores_popup = [
				"div[data-testid='cookie-banner']",
				"div[id*='cookie']",
				"div[class*='cookie']",
				"div[id*='consent']",
				"div[class*='consent']",
				"#usercentrics-root",
				"[data-testid='uc-banner']"
			]

			for indicador in indicadores_popup:
				if page.locator(indicador).count() > 0:
					popup_detectado = True
					logger.debug("🔍 Popup de cookies detectado", indicador=indicador)
					break

			if not popup_detectado:
				logger.info("✅ No se detectó popup de cookies, continuando...")
				return

		except Exception as e:
			logger.debug("Error detectando popup de cookies", error=str(e))

		# Intentar hacer clic en el botón de aceptar con diferentes estrategias
		for i, estrategia in enumerate(selectores_aceptar):
			try:
				timeout = timeout_base + (i * 2000)  # Incrementar timeout para estrategias más lentas
				logger.debug(f"🎯 Intentando estrategia {i+1}/{len(selectores_aceptar)}",
						   tipo=estrategia['type'], selector=estrategia['selector'], timeout=timeout)

				if estrategia['type'] == 'role':
					elemento = page.get_by_role(estrategia['selector'], name=estrategia['name'])
				elif estrategia['type'] == 'css':
					elemento = page.locator(estrategia['selector'])
				elif estrategia['type'] == 'xpath':
					elemento = page.locator(f"xpath={estrategia['selector']}")

				# Esperar a que el elemento esté visible y habilitado
				elemento.wait_for(state="visible", timeout=timeout)
				elemento.wait_for(state="enabled", timeout=timeout)

				# Hacer clic
				elemento.click(timeout=timeout)

				logger.success(f"✅ Cookies aceptadas exitosamente con estrategia {i+1}",
							 tipo=estrategia['type'], selector=estrategia['selector'])

				# Esperar a que el popup desaparezca
				page.wait_for_timeout(2000)

				# Verificar que el popup se fue
				popup_aun_presente = False
				for indicador in indicadores_popup:
					if page.locator(indicador).count() > 0:
						popup_aun_presente = True
						break

				if popup_aun_presente:
					logger.warning("⚠️ Popup aún presente después de hacer clic")
					if agresivo and intento < max_reintentos - 1:
						continue  # Reintentar con siguiente estrategia
					else:
						raise CookiePopupError("Popup de cookies detectado pero no se pudo descartar")

				return  # Éxito

			except PWTimeoutError:
				logger.debug(f"⏱️ Timeout con estrategia {i+1}, continuando con siguiente...")
				continue
			except Exception as e:
				logger.debug(f"❌ Error con estrategia {i+1}", error=str(e))
				continue

		# Si llegamos aquí, todas las estrategias fallaron en este intento
		if agresivo and intento < max_reintentos - 1:
			logger.warning(f"⚠️ Todas las estrategias fallaron en intento {intento + 1}, reintentando...")
			page.wait_for_timeout(3000)  # Esperar antes de reintentar
		else:
			# Último intento y todo falló
			if popup_detectado:
				raise CookiePopupError("Popup de cookies detectado pero no se pudo manejar después de todos los intentos")
			else:
				logger.info("✅ No se encontró popup de cookies para manejar")
				return

def aceptar_cookies(page: Page):
	"""Función legacy para compatibilidad - usa el nuevo manejador agresivo."""
	try:
		manejar_popup_cookies(page, agresivo=True)
	except CookiePopupError as e:
		logger.error(f"❌ Error manejando popup de cookies: {e}")
		raise  # Propagar el error para que el código que lo llama pueda manejarlo
	except Exception as e:
		logger.info(f"No se encontró el botón de cookies: {e}. Continuando...", error=str(e))

def verificar_login_exitoso(page: Page) -> dict:
	"""
	Verifica si el login fue exitoso usando múltiples métodos de validación.

	Args:
		page: Página de Playwright a verificar

	Returns:
		Dict con resultados de verificación:
		{
			'success': bool,
			'method': str,
			'details': str,
			'url': str,
			'authenticated_elements': list
		}
	"""
	logger.info("🔍 Verificando éxito del login con múltiples métodos")
	resultado = {
		'success': False,
		'method': None,
		'details': '',
		'url': page.url,
		'authenticated_elements': []
	}

	try:
		# Método 1: Verificación por URL (más rápido)
		current_url = page.url.lower()
		url_indicates_auth = (
			'/login/' not in current_url and
			'/login' not in current_url and
			('acumbamail.com' in current_url or current_url.endswith('/'))
		)

		if url_indicates_auth:
			resultado['method'] = 'url_check'
			resultado['details'] = f"URL {page.url} no es página de login"
			logger.debug("✅ Verificación por URL exitosa", url=page.url)
		else:
			logger.debug("❌ Verificación por URL falló", url=page.url)

		# Método 2: Búsqueda de elementos de usuario autenticado
		elementos_autenticacion = [
			# Navegación principal
			{'selector': "navigation", 'description': 'Navegación principal'},
			{'selector': "nav", 'description': 'Barra de navegación'},

			# Elementos específicos de usuario
			{'selector': "[data-testid='user-menu']", 'description': 'Menú de usuario'},
			{'selector': "a[href*='logout']", 'description': 'Enlace de logout'},
			{'selector': "a[href*='profile']", 'description': 'Enlace de perfil'},
			{'selector': "button[aria-label*='usuario']", 'description': 'Botón de usuario'},

			# Enlaces típicos después del login
			{'selector': "a[href*='/report/']", 'description': 'Enlace a reportes'},
			{'selector': "a[href*='/campaigns/']", 'description': 'Enlace a campañas'},
			{'selector': "a[href*='/subscribers/']", 'description': 'Enlace a suscriptores'},

			# Contenido típico del dashboard
			{'selector': "h1:has-text('Panel')", 'description': 'Título de panel'},
			{'selector': "h1:has-text('Dashboard')", 'description': 'Título de dashboard'},
			{'selector': ".dashboard", 'description': 'Contenedor de dashboard'},
		]

		elementos_encontrados = []
		for elemento in elementos_autenticacion:
			try:
				locator = page.locator(elemento['selector'])
				if locator.count() > 0:
					elementos_encontrados.append(elemento['description'])
					logger.debug("✅ Elemento de autenticación encontrado",
							   selector=elemento['selector'], description=elemento['description'])
			except Exception as e:
				logger.debug("Error buscando elemento", selector=elemento['selector'], error=str(e))

		resultado['authenticated_elements'] = elementos_encontrados

		# Método 3: Verificación de ausencia de elementos de login
		login_elements = [
			"input[type='email']",
			"input[type='password']",
			"button[name='login']",
			"button:has-text('Entrar')",
			"button:has-text('Login')",
			"a:has-text('¿Olvidaste tu contraseña?')"
		]

		login_elements_found = []
		for login_element in login_elements:
			try:
				if page.locator(login_element).count() > 0:
					login_elements_found.append(login_element)
			except Exception:
				pass

		# Decisión final basada en toda la evidencia
		if len(elementos_encontrados) >= 2:  # Al menos 2 elementos de autenticación
			resultado['success'] = True
			if not resultado['method']:
				resultado['method'] = 'content_verification'
			resultado['details'] = f"Se encontraron {len(elementos_encontrados)} elementos de autenticación"
			logger.success("✅ Login verificado exitosamente por contenido",
						  elementos_encontrados=len(elementos_encontrados),
						  elementos_lista=elementos_encontrados)

		elif url_indicates_auth and len(elementos_encontrados) >= 1:
			resultado['success'] = True
			resultado['details'] = f"URL válida y {len(elementos_encontrados)} elemento de autenticación"
			logger.success("✅ Login verificado por URL + contenido",
						  url=page.url, elementos=len(elementos_encontrados))

		elif len(login_elements_found) == 0 and url_indicates_auth:
			resultado['success'] = True
			if not resultado['method']:
				resultado['method'] = 'url_only'
			resultado['details'] = "URL válida y sin elementos de login detectados"
			logger.success("✅ Login verificado por URL (sin elementos de login)")

		else:
			resultado['details'] = f"No se pudo verificar autenticación: {len(elementos_encontrados)} elementos encontrados, {len(login_elements_found)} elementos de login"
			logger.warning("⚠️ No se pudo verificar login exitoso",
						  elementos_auth=len(elementos_encontrados),
						  elementos_login=len(login_elements_found),
						  url=page.url)

		return resultado

	except Exception as e:
		resultado['details'] = f"Error durante verificación: {str(e)}"
		logger.error("❌ Error verificando login exitoso", error=str(e))
		return resultado

def autenticado(page: Page) -> bool:
	"""Verifica si el usuario ya está autenticado (versión mejorada)."""
	logger.info("🔐 Verificando estado de autenticación")
	try:
		# Usar la nueva función de verificación
		resultado = verificar_login_exitoso(page)
		return resultado['success']
	except Exception as e:
		logger.error("❌ Error en verificación de autenticación", error=str(e))
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
		raise ValueError("Usuario no configurado en config.yaml")

	if not password or password == "clave":
		logger.error("❌ Contraseña no configurada en config.yaml", user=username)
		raise ValueError("Contraseña no configurada en config.yaml")

	logger.info(f"🔑 Iniciando proceso de login para usuario: {username}")

	try:
		logger.info(f"🌐 Navegando a URL: {url}")
		# Use domcontentloaded first for faster initial load
		page.goto(url, wait_until="domcontentloaded", timeout=60_000)
		logger.info("✅ Navegación inicial completada (domcontentloaded)")

		# Then wait for page to stabilize with networkidle
		esperar_carga_pagina(page, timeout=45_000, use_networkidle=True)
	except Exception as e:
		logger.error(f"❌ Error conectando a Acumbamail: {e}", url=url, error=str(e))
		raise

	if f"{url_base}/" != page.url:
		logger.info("🔍 Verificando que la sesión existente sea válida...")
		resultado_verificacion = verificar_login_exitoso(page)

		if resultado_verificacion['success']:
			logger.success("✅ Sesión existente verificada correctamente",
						  metodo=resultado_verificacion['method'],
						  detalles=resultado_verificacion['details'])
			logger.info("💾 Guardando estado de sesión verificada...")
			try:
				context.storage_state(path=storage_state_path())
				logger.success("✅ Estado de sesión existente guardado correctamente")
				return
			except Exception as e:
				logger.error("❌ Error guardando estado de sesión existente", error=str(e))
				raise SessionSaveError(f"No se pudo guardar la sesión existente: {e}")
		else:
			logger.warning("⚠️ Sesión existente no válida, se requiere nuevo login",
						  detalles=resultado_verificacion['details'])
			# Continuar con el proceso de login normal

	# Manejar popup de cookies agresivamente antes de cualquier verificación
	logger.info("🍪 Manejando popup de cookies antes de verificación...")
	manejar_popup_cookies(page, agresivo=True)

	# Verificar estado de autenticación actual
	if autenticado(page):
		logger.success("✅ Ya estás autenticado y verificado.")

		# Guardar sesión solo después de verificación exitosa
		logger.info("💾 Guardando estado de sesión ya autenticado...")
		try:
			context.storage_state(path=storage_state_path())
			logger.success("✅ Estado de sesión autenticado guardado correctamente")
			return
		except Exception as e:
			logger.error("❌ Error guardando estado de sesión autenticado", error=str(e))
			raise SessionSaveError(f"No se pudo guardar la sesión autenticada: {e}")

	# Si no está autenticado, proceder con login
	logger.info("🔐 No estás autenticado. Procediendo con login...")

	login_realizado = False
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

		login_realizado = True
		logger.success("✅ Formulario de login enviado")

		# Espera adicional para asegurar que la sesión se establezca completamente
		logger.info("⏳ Esperando estabilización de sesión post-login...")
		page.wait_for_load_state("networkidle", timeout=30_000)
		page.wait_for_timeout(2000)  # 2 segundos adicionales para estabilidad
		logger.success("✅ Sesión estabilizada")

	except Exception as e:
		logger.error(f"❌ Error durante el login: {e}", error=str(e))
		raise AuthenticationFailedError(f"Falló el login: {e}")

	# VERIFICACIÓN CRÍTICA: Solo guardar sesión si el login fue exitoso
	if login_realizado:
		logger.info("🔍 Verificando éxito del login después de autenticación...")
		resultado_verificacion = verificar_login_exitoso(page)

		if resultado_verificacion['success']:
			logger.success("✅ Login verificado exitosamente",
						  metodo=resultado_verificacion['method'],
						  detalles=resultado_verificacion['details'],
						  elementos=len(resultado_verificacion['authenticated_elements']))

			# Guardar sesión solo después de verificación exitosa
			logger.info("💾 Guardando estado de sesión verificado...")
			try:
				context.storage_state(path=storage_state_path())
				logger.success("✅ Estado de sesión verificado guardado correctamente")
			except Exception as e:
				logger.error("❌ Error guardando estado de sesión verificado", error=str(e))
				raise SessionSaveError(f"No se pudo guardar la sesión verificada: {e}")
		else:
			logger.error("❌ Login no pudo ser verificado exitosamente",
						 detalles=resultado_verificacion['details'],
						 url=page.url)
			raise AuthenticationFailedError(f"Login completado pero verificación falló: {resultado_verificacion['details']}")

	# Espera final para asegurar persistencia
	page.wait_for_timeout(2000)
	logger.success("✅ Proceso de autenticación completado y verificado")
