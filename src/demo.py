import csv
from pathlib import Path
from playwright.sync_api import sync_playwright
from datetime import datetime
from typing import List

try:
    # Intentar imports relativos (cuando se ejecuta como módulo)
    from .excel_utils import agregar_datos, crear_hoja_con_datos, obtener_o_crear_hoja
    from .shared.utils.legacy_utils import cargar_campanias_a_buscar, crear_contexto_navegador, configurar_navegador, load_config, data_path, notify
    from .shared.logging.logger import get_logger
    from .structured_logger import log_success, log_error, log_warning, log_info, log_performance, log_data_extraction
    from .hybrid_service import HybridDataService
    # Campaign URLs functionality will be handled by existing infrastructure
    # Legacy authentication wrapper
    from .core.authentication.authentication_service import AuthenticationService
    from .core.config.config_manager import ConfigManager
    from .shared.utils.legacy_utils import storage_state_path

    class FileSessionStorage:
        def __init__(self, session_path: str):
            self.session_path = session_path
        def save_session(self, context):
            context.storage_state(path=self.session_path)
        def get_session_path(self) -> str:
            return self.session_path

    def login(page, context):
        config_manager = ConfigManager()
        session_storage = FileSessionStorage(storage_state_path())
        auth_service = AuthenticationService(config_manager, session_storage)
        return auth_service.authenticate(page, context)

except ImportError:
    # Imports absolutos (cuando se ejecuta como script independiente)
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from excel_utils import agregar_datos, crear_hoja_con_datos, obtener_o_crear_hoja
    from shared.utils.legacy_utils import cargar_campanias_a_buscar, crear_contexto_navegador, configurar_navegador, load_config, data_path, notify
    from structured_logger import log_success, log_error, log_warning, log_info, log_data_extraction
    from hybrid_service import HybridDataService
    # Campaign URLs functionality will be handled by existing infrastructure
    # Legacy authentication wrapper
    from core.authentication.authentication_service import AuthenticationService
    from core.config.config_manager import ConfigManager
    from shared.utils.legacy_utils import storage_state_path

    class FileSessionStorage:
        def __init__(self, session_path: str):
            self.session_path = session_path
        def save_session(self, context):
            context.storage_state(path=self.session_path)
        def get_session_path(self) -> str:
            return self.session_path

    def login(page, context):
        config_manager = ConfigManager()
        session_storage = FileSessionStorage(storage_state_path())
        auth_service = AuthenticationService(config_manager, session_storage)
        return auth_service.authenticate(page, context)

from openpyxl import Workbook
import re

ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")
ARCHIVO_INFORMES_PREFIX = data_path("informes")

def generar_nombre_archivo_informe(nombre_campania: str = "", fecha_envio: str = "") -> str:
	ahora = datetime.now()
	fecha_extraccion = ahora.strftime("%Y%m%d%H%M")
	
	if nombre_campania and fecha_envio:
		# Limpiar nombre de campaña de caracteres problemáticos para nombres de archivo
		nombre_limpio = re.sub(r'[<>:"/\\|?*]', '_', nombre_campania)
		nombre_archivo = f"{nombre_limpio}-{fecha_envio}_{fecha_extraccion}.xlsx"
	else:
		# Fallback al formato anterior si no se proporcionan los parámetros
		nombre_archivo = f"{ARCHIVO_INFORMES_PREFIX}_{fecha_extraccion}.xlsx"
	
	# Asegurar que el nombre de archivo esté en el directorio data/suscriptores
	if nombre_campania and fecha_envio:
		nombre_archivo = data_path(f"suscriptores/{nombre_archivo}")
	else:
		nombre_archivo = data_path(nombre_archivo.replace(f"{ARCHIVO_INFORMES_PREFIX}_", ""))
		
	return nombre_archivo

def crear_archivo_csv(general: list[list[str]], informe_detallado: list[list[list[str]]], nombre_campania: str = "", fecha_envio: str = ""):
    """
    Crea archivos CSV con los informes recopilados (uno por hoja)
    """
    try:
        log_info("Iniciando creación de archivos CSV", 
                campania=nombre_campania, fecha_envio=fecha_envio)
        
        [abiertos, no_abiertos, clics, hard_bounces, soft_bounces] = informe_detallado
        
        # Generar nombre base para los archivos CSV
        nombre_archivo_base = Path(generar_nombre_archivo_informe(nombre_campania, fecha_envio))
        nombre_base = nombre_archivo_base.stem  # Nombre sin extensión
        directorio = nombre_archivo_base.parent
        directorio_csv = directorio / "csv"
        directorio_csv.mkdir(parents=True, exist_ok=True)  # Crear directorio CSV si no existe
        
        # Crear archivo CSV para la hoja general
        encabezados_general = ["Nombre", "Tipo", "Fecha envio", "Listas", "Emails", "Abiertos", "Clics", "URL de Correo"]
        archivo_general = directorio_csv / f"{nombre_base}_General.csv"
        
        with open(archivo_general, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(encabezados_general)  # Escribir encabezados
            writer.writerows(general)  # Escribir datos
        log_data_extraction("General", len(general), "CSV")
        
        # Definir configuraciones para los archivos CSV detallados
        archivos_config = [
            ("Abiertos", abiertos, ["Proyecto", "Lista", "Correo", "Fecha apertura", "País apertura", "Aperturas", "Lista", "Estado", "Calidad"]),
            ("No abiertos", no_abiertos, ["Proyecto", "Lista", "Correo", "Lista", "Estado", "Calidad"]),
            ("Clics", clics, ["Proyecto", "Lista", "Correo", "Fecha primer clic", "País apertura", "Lista", "Estado", "Calidad"]),
            ("Hard bounces", hard_bounces, ["Proyecto", "Lista", "Correo", "Lista", "Estado", "Calidad"]),
            ("Soft bounces", soft_bounces, ["Proyecto", "Lista", "Correo", "Lista", "Estado", "Calidad"])
        ]

        # Crear archivos CSV detallados usando la configuración
        for nombre_archivo, datos, columnas in archivos_config:
            archivo_path = directorio_csv / f"{nombre_base}_{nombre_archivo}.csv"
            with open(archivo_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(columnas)  # Escribir encabezados
                writer.writerows(datos)  # Escribir datos
            log_data_extraction(nombre_archivo, len(datos), "CSV")

        log_success(f"Archivos CSV creados exitosamente en: {directorio_csv}", 
                   total_archivos=len(archivos_config)+1, directorio=directorio_csv)
        
        return str(directorio_csv)
        
    except Exception as e:
        log_error(f"Error creando archivos CSV: {e}", 
                 campania=nombre_campania, fecha_envio=fecha_envio)
        raise


def crear_archivo_excel(general: list[list[str]], informe_detallado: list[list[list[str]]], nombre_campania: str = "", fecha_envio: str = ""):
    """
    Crea el archivo Excel con los informes recopilados
    """
    try:
        # Cargar la configuración para verificar si estamos en modo debug
        config = load_config()
        debug_mode = config.get("debug", False)
        
        if debug_mode:
            log_info("Modo debug activado, generando archivos CSV en lugar de Excel", 
                    campania=nombre_campania, fecha_envio=fecha_envio, debug_mode=debug_mode)
            return crear_archivo_csv(general, informe_detallado, nombre_campania, fecha_envio)
        else:
            log_info("Modo normal, generando archivo Excel", 
                    campania=nombre_campania, fecha_envio=fecha_envio, debug_mode=debug_mode)
        
        [abiertos, no_abiertos, clics, hard_bounces, soft_bounces] = informe_detallado
        
        # Crear libro y hoja general
        wb = Workbook()

        # Eliminar la hoja por defecto "Sheet" creada automáticamente
        if "Sheet" in wb.sheetnames:
            wb.remove(wb["Sheet"])

        encabezados_general = ["Nombre", "Tipo", "Fecha envio", "Listas", "Emails", "Abiertos", "Clics", "URL de Correo"]
        ws_general = obtener_o_crear_hoja(wb, "General", encabezados_general)
        agregar_datos(ws_general, general)

        # Definir configuraciones para las hojas detalladas
        hojas_config = [
            ("Abiertos", abiertos, ["Proyecto", "Lista", "Correo", "Fecha apertura", "País apertura", "Aperturas", "Lista", "Estado", "Calidad"]),
            ("No abiertos", no_abiertos, ["Proyecto", "Lista", "Correo", "Lista", "Estado", "Calidad"]),
            ("Clics", clics, ["Proyecto", "Lista", "Correo", "Fecha primer clic", "País apertura", "Lista", "Estado", "Calidad"]),
            ("Hard bounces", hard_bounces, ["Proyecto", "Lista", "Correo", "Lista", "Estado", "Calidad"]),
            ("Soft bounces", soft_bounces, ["Proyecto", "Lista", "Correo", "Lista", "Estado", "Calidad"])
        ]

        # Crear hojas detalladas usando la configuración
        for nombre_hoja, datos, columnas in hojas_config:
            crear_hoja_con_datos(wb, nombre_hoja, datos, columnas)
            log_data_extraction(nombre_hoja, len(datos), "base de datos")

        nombre_archivo = generar_nombre_archivo_informe(nombre_campania, fecha_envio)
        wb.save(nombre_archivo)
        
        log_success(f"Archivo Excel creado exitosamente: {nombre_archivo}", 
                   total_hojas=len(hojas_config)+1, archivo=nombre_archivo)
        
        return nombre_archivo
        
    except Exception as e:
        log_error(f"Error creando archivo Excel: {e}", 
                 campania=nombre_campania, fecha_envio=fecha_envio)
        raise

def get_campaign_urls_with_fallback(page, campaign_id: int) -> str:
	"""
	Obtiene las URLs de una campaña mediante scraping.
	Extrae las URLs de la página de seguimiento de URLs y las separa por comas.
	"""
	from src.shared.logging.logger import get_logger
	logger = get_logger()

	try:
		logger.start_timer(f"scraping_urls_campaign_{campaign_id}")
		logger.info(f"🔗 Extrayendo URLs de la campaña {campaign_id}")

		# Navegar a la página de seguimiento de URLs
		url_tracking_page = f"https://acumbamail.com/report/campaign/{campaign_id}/url/"
		page.goto(url_tracking_page, wait_until="networkidle")
		logger.debug(f"   Navegado a: {url_tracking_page}")

		# Esperar a que la página cargue completamente
		page.wait_for_load_state("domcontentloaded")

		# Intentar diferentes selectores para encontrar los elementos de URL
		# La estructura puede variar, así que probamos varios selectores
		url_elements = []

		# Intento 1: Buscar tabla con clase específica
		try:
			# Esperar un momento para que el contenido dinámico cargue
			page.wait_for_timeout(2000)

			# Buscar todos los list items que contengan URLs (http:// o https://)
			url_elements = page.locator("li:has-text('http')").all()
			logger.debug(f"   Encontrados {len(url_elements)} elementos con 'http'")
		except Exception as e:
			logger.debug(f"   Intento 1 falló: {e}")

		# Si no encontramos elementos, intentar extraer del HTML directamente
		if not url_elements or len(url_elements) == 0:
			logger.debug("   Intentando extracción directa del contenido de la página")
			page_content = page.content()
			import re

			# Buscar URLs en el contenido HTML que tengan el formato esperado
			# Patrón: URL seguida de número y porcentaje
			pattern = r'(https?://[^\s<>"]+)\s+\d+\s+\([^)]+abridores\)'
			matches = re.findall(pattern, page_content)

			if matches:
				logger.debug(f"   Encontradas {len(matches)} URLs mediante regex en HTML")
				result = ", ".join(matches)
				logger.end_timer(f"scraping_urls_campaign_{campaign_id}",
				                f"Extraídas {len(matches)} URLs (método directo)")
				logger.success(f"✅ URLs de campaña {campaign_id} extraídas exitosamente: {len(matches)} URLs")
				return result

		# Extraer las URLs del texto de cada elemento
		urls: List[str] = []
		import re

		for elem in url_elements:
			text = elem.inner_text().strip()
			# Saltar el header "Url Han hecho clic Acciones"
			if "Url" in text and "Han hecho clic" in text:
				continue

			# Saltar elementos que no contengan URLs
			if not text or not ("http://" in text or "https://" in text):
				continue

			# Extraer URL usando regex - captura todo antes del primer espacio seguido de números
			# Formato esperado: "http://example.com 67 (13,8% abridores)"
			match = re.match(r'^(https?://[^\s]+)', text)
			if match:
				url: str = match.group(1)
				urls.append(url)
				logger.debug(f"   URL extraída: {url}")

		# Unir las URLs con comas
		result = ", ".join(urls)
		logger.end_timer(f"scraping_urls_campaign_{campaign_id}",
		                f"Extraídas {len(urls)} URLs")
		logger.success(f"✅ URLs de campaña {campaign_id} extraídas exitosamente: {len(urls)} URLs")

		return result

	except Exception as e:
		logger.error(f"❌ Error extrayendo URLs de campaña {campaign_id}: {e}")
		logger.end_timer(f"scraping_urls_campaign_{campaign_id}", f"Error: {e}")
		# En caso de error, devolver cadena vacía para no bloquear el proceso
		return ""

def generar_listas(todas_listas, id_listas: list[str]) -> str:
	listas_ar = []
	for lista in todas_listas:
		if lista.id in id_listas:
			listas_ar.append(lista.name or "")
	listas = ", ".join(listas_ar)
	return listas

def crear_mapa_email_lista(todas_listas, api) -> dict[str, str]:
	"""
	Crea un mapa email -> nombre_lista consultando cada lista una sola vez
	para evitar el rate limit de la API
	"""
	mapa_email_lista = {}

	try:
		log_info("Iniciando creación de mapa email-lista", total_listas=len(todas_listas))

		for i, lista in enumerate(todas_listas):
			try:
				log_info(f"Procesando lista {i+1}/{len(todas_listas)}: {lista.name}", 
						lista_id=lista.id, progreso=f"{i+1}/{len(todas_listas)}")

				# Obtener todos los suscriptores de esta lista
				suscriptores = api.suscriptores.get_subscribers(lista.id)

				# Mapear cada email a esta lista
				for suscriptor in suscriptores:
					email = suscriptor.email.lower().strip()
					mapa_email_lista[email] = lista.name or ""

				log_success(f"Lista {lista.name} procesada exitosamente", 
						   lista_id=lista.id, suscriptores_mapeados=len(suscriptores))

			except Exception as e:
				log_warning(f"Error procesando lista {lista.name}: {e}", 
						   lista_id=lista.id, error_type=type(e).__name__)
				continue

		log_success("Mapa email-lista completado", 
				   emails_mapeados=len(mapa_email_lista), listas_procesadas=len(todas_listas))
		return mapa_email_lista

	except Exception as e:
		log_error(f"Error creando mapa email-lista: {e}", 
				 total_listas=len(todas_listas), error_type=type(e).__name__)
		return {}

def obtener_lista_suscriptor(email: str, mapa_email_lista: dict[str, str]) -> str:
	"""
	Obtiene la lista específica a la que pertenece un suscriptor
	usando el mapa precalculado
	"""
	email_clean = email.lower().strip()
	return mapa_email_lista.get(email_clean, "Lista no encontrada")

def generar_general(campania, campania_complete, campaign_clics, todas_listas, page, campaign_id=None) -> list[str]:
	from .logger import get_logger
	logger = get_logger()
	
	logger.debug("🚀 Iniciando generación de datos generales para campaña")
	logger.debug(f"   - Nombre campaña: {campania.name if campania.name else 'Sin nombre'}")
	logger.debug(f"   - ID pasado como parámetro: {campaign_id}")
	logger.debug(f"   - Objeto campania tiene atributo 'id': {hasattr(campania, 'id')}")
	if hasattr(campania, 'id'):
		logger.debug(f"   - Valor de campania.id: {getattr(campania, 'id', 'NO_DISPONIBLE')}")
	
	nombre = campania.name or ""
	tipo = ""
	fecha = campania.date
	
	id_listas = campania.lists or []
	listas = generar_listas(todas_listas, id_listas)
	emails = str(campania_complete.total_delivered)
	opens = str(campania_complete.opened or 0)
	clicks = str(len(campaign_clics))
	
	# Obtener URLs de la campaña mediante scraping
	# Prioritize the passed campaign_id, but fall back to campania.id if available
	actual_campaign_id = campaign_id if campaign_id is not None else (campania.id if hasattr(campania, 'id') else None)
	logger.debug(f"   - ID usado para scraping de URLs: {actual_campaign_id}")
	
	if actual_campaign_id:
		url_email = get_campaign_urls_with_fallback(page, actual_campaign_id)
		logger.debug(f"   - URLs obtenidas: '{url_email}'")
	else:
		logger.warning("⚠️ No se pudo determinar ID de campaña para scraping de URLs")
		url_email = ""
	
	logger.debug(f"✅ Finalizada generación de datos generales. URLs incluidas: {bool(url_email)}")
	return [nombre, tipo, fecha, listas, emails, opens, clicks, url_email]

def generar_abiertos(campania, openers, mapa_email_lista) -> list[list[str]]:
	abiertos: list[list[str]] = []

	for opener in openers:
		proyecto = campania.name or ""
		correo = opener.email or ""
		fecha_apertura = opener.open_datetime or ""
		pais = ""
		aperturas = ""
		estado = "Activo"
		calidad = ""

		# Obtener la lista específica del suscriptor usando el mapa
		lista = obtener_lista_suscriptor(correo, mapa_email_lista)
		lista2 = lista

		abiertos.append([proyecto, lista, correo, fecha_apertura, pais, aperturas, lista2, estado, calidad])
	return abiertos

def generar_clics(campania, campaign_clics, mapa_email_lista) -> list[list[str]]:
	clics: list[list[str]] = []

	for click in campaign_clics:
		proyecto = campania.name or ""
		correo = click.email or ""
		fecha_clic = click.click_datetime or ""
		pais = ""
		estado = "Activo"
		calidad = ""

		# Obtener la lista específica del suscriptor usando el mapa
		lista = obtener_lista_suscriptor(correo, mapa_email_lista)
		lista2 = lista

		clics.append([proyecto, lista, correo, fecha_clic, pais, lista2, estado, calidad])
	return clics

def generar_soft_bounces(campania, soft_bounce_list, mapa_email_lista) -> list[list[str]]:
	soft_bounces: list[list[str]] = []

	for bounce in soft_bounce_list:
		proyecto = campania.name or ""
		correo = bounce.email or ""
		estado = "Activo"
		calidad = ""

		# Obtener la lista específica del suscriptor usando el mapa
		lista = obtener_lista_suscriptor(correo, mapa_email_lista)
		lista2 = lista

		soft_bounces.append([proyecto, lista, correo, lista2, estado, calidad])
	return soft_bounces

# Las funciones de scraping han sido movidas a src/scrapping/endpoints/
# Este archivo ahora usa el HybridDataService para combinar API y scraping

def convert_hard_bounces_to_rows(hard_bounces) -> List[List[str]]:
	"""
	Convierte objetos HardBounceSubscriber a filas para Excel:
	[Proyecto, Lista, Correo, Lista, Estado, Calidad]
	"""
	rows: List[List[str]] = []
	for bounce in hard_bounces:
		rows.append([
			bounce.proyecto,
			bounce.lista,
			bounce.email,
			bounce.lista,  # Lista duplicada según formato original
			bounce.estado.value if hasattr(bounce.estado, 'value') else str(bounce.estado),
			bounce.calidad.value if hasattr(bounce.calidad, 'value') else str(bounce.calidad)
		])
	return rows

def convert_no_opens_to_rows(no_opens) -> List[List[str]]:
	"""
	Convierte objetos NoOpenSubscriber a filas para Excel:
	[Proyecto, Lista, Correo, Lista, Estado, Calidad]
	"""
	rows: List[List[str]] = []
	for no_open in no_opens:
		rows.append([
			no_open.proyecto,
			no_open.lista,
			no_open.email,
			no_open.lista,  # Lista duplicada según formato original
			no_open.estado.value if hasattr(no_open.estado, 'value') else str(no_open.estado),
			no_open.calidad.value if hasattr(no_open.calidad, 'value') else str(no_open.calidad)
		])
	return rows

def formatear_fecha_envio(fecha_str: str) -> str:
	"""
	Convierte una fecha en formato 'DD/MM/YY HH:MM' o 'DD/MM/YYYY HH:MM' a 'YYYYMMDD'
	Si no se puede parsear, devuelve una cadena vacía.
	"""
	fecha_envio_param = ""

	try:
		# Try different common date formats including 2-digit year
		date_formats = [
			"%d/%m/%y %H:%M",  # Formato DD/MM/YY HH:MM (añadido primero)
			"%d/%m/%Y %H:%M",  # DD/MM/YYYY HH:MM
			"%d-%m-%Y %H:%M", 
			"%Y-%m-%d %H:%M",
			"%Y-%m-%d %H:%M:%S",  # YYYY-MM-DD HH:MM:SS
			"%d/%m/%Y %H:%M:%S",  # DD/MM/YYYY HH:MM:SS
			"%d-%m-%Y %H:%M:%S",  # DD-MM-YYYY HH:MM:SS
			"%d/%m/%Y",  # DD/MM/YYYY
			"%d-%m-%Y",
			"%Y-%m-%d",
			"%d/%m/%y"  # Formato DD/MM/YY
		]
		
		fecha_envio_dt = None
		for fmt in date_formats:
			try:
				fecha_envio_dt = datetime.strptime(fecha_str, fmt)
				break
			except ValueError:
				continue
		
		if fecha_envio_dt:
			fecha_envio_param = fecha_envio_dt.strftime("%Y%m%d")
		else:
			# Si no se puede parsear, intentar extraer solo la parte de fecha
			# Buscar patrones como YYYY-MM-DD, DD/MM/YYYY, o DD-MM-YYYY
			date_match = re.search(r'(\d{4})[-/](\d{2})[-/](\d{2})', fecha_str)  # YYYY-MM-DD o YYYY/MM/DD
			if date_match:
				year, month, day = date_match.groups()
				fecha_envio_param = f"{year}{month}{day}"
			else:
				# Intentar formato DD/MM/YYYY o DD-MM-YYYY
				date_match = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', fecha_str)
				if date_match:
					day, month, year = date_match.groups()
					fecha_envio_param = f"{year}{month}{day}"
				else:
					# Último recurso: limpiar caracteres problemáticos
					fecha_envio_param = re.sub(r'[<>:"/\\|?*\s]', '', fecha_str)
	except Exception:
		fecha_envio_param = re.sub(r'[<>:"/\\|?*\s]', '', fecha_str)

	return fecha_envio_param

def main():
	try:
		log_info("🚀 Iniciando proceso de extracción de campañas")
		
		config = load_config()
		extraccion_oculta = bool(config.get("headless", False))
		log_info("Configuración cargada", headless=extraccion_oculta)

		campanias_a_buscar = cargar_campanias_a_buscar(ARCHIVO_BUSQUEDA)
		log_info("Campañas a procesar", total_campanias=len(campanias_a_buscar))
		
		with sync_playwright() as p:
			log_info("🌐 Iniciando navegador")
			browser = configurar_navegador(p, extraccion_oculta)
			context = crear_contexto_navegador(browser, extraccion_oculta)

			page = context.new_page()

			log_info("🔐 Iniciando proceso de autenticación")
			login(page, context=context)
			log_success("Autenticación completada exitosamente")

			# Inicializar servicio híbrido con la página autenticada
			hybrid_service = HybridDataService(page)
			api = hybrid_service.api  # Obtener instancia de API para consultas adicionales
			log_info("🔧 Servicio híbrido inicializado")

			errores_campanias = []
			campanias_exitosas = 0

			for i, (id, nombre_campania) in enumerate(campanias_a_buscar):
				log_info(f"📊 Procesando campaña {i+1}/{len(campanias_a_buscar)}", 
						campania_id=id, nombre=nombre_campania, progreso=f"{i+1}/{len(campanias_a_buscar)}")

				# Obtener datos completos usando servicio híbrido
				try:
					complete_data = hybrid_service.get_complete_campaign_data(id)
					if not complete_data or not complete_data.get("campaign_basic"):
						raise Exception(f"No se pudieron obtener datos para la campaña '{nombre_campania}'")
					
					log_success("Datos de campaña obtenidos", campania_id=id, 
							   tiene_datos_basicos=bool(complete_data.get("campaign_basic")),
							   tiene_scraping=bool(complete_data.get("scraping_result")))
					
				except Exception as e:
					error_msg = f"La campaña '{nombre_campania}' no está disponible"
					log_error(f"{error_msg}: {e}", campania_id=id, error_type=type(e).__name__)
					errores_campanias.append(error_msg)
					continue  # Continuar con la siguiente campaña

				# Extraer datos para compatibilidad con formato Excel existente
				campania = complete_data["campaign_basic"]
				campania_complete = complete_data["campaign_detailed"]
				campaign_clics = complete_data["clicks"]
				todas_listas = complete_data["lists"]
				openers = complete_data["openers"]
				soft_bounce_list = complete_data["soft_bounces"]

				log_data_extraction("datos básicos de campaña", 1, "API")
				log_data_extraction("clics", len(campaign_clics), "API")
				log_data_extraction("listas", len(todas_listas), "API")
				log_data_extraction("aperturas", len(openers), "API")
				log_data_extraction("soft bounces", len(soft_bounce_list), "API")

				# Crear mapa email->lista SOLO para las listas usadas por esta campaña
				# Esto reduce llamadas únicas a get_subscribers y evita el rate limit
				listas_campania_ids = campania.lists or []
				listas_campania = [l for l in todas_listas if l.id in listas_campania_ids]
				mapa_email_lista = crear_mapa_email_lista(listas_campania, api)

				# Datos básicos
				general = [generar_general(campania, campania_complete, campaign_clics, todas_listas, page, campania.id if hasattr(campania, 'id') else id)]
				abiertos2 = generar_abiertos(campania, openers, mapa_email_lista)
				clics = generar_clics(campania, campaign_clics, mapa_email_lista)
				soft_bounces = generar_soft_bounces(campania, soft_bounce_list, mapa_email_lista)

				# Datos de scraping (convertir a formato Excel)
				hard_bounces = []
				no_abiertos = []

				if complete_data.get("scraping_result"):
					scraping_result = complete_data["scraping_result"]
					hard_bounces = convert_hard_bounces_to_rows(scraping_result.hard_bounces)
					no_abiertos = convert_no_opens_to_rows(scraping_result.no_opens)
					log_success("Scraping completado", 
							   hard_bounces=len(hard_bounces), no_abiertos=len(no_abiertos))
				else:
					log_warning("No se pudieron obtener datos de scraping", campania_id=id)

				# Crear archivo Excel con los resultados
				if general or abiertos2 or no_abiertos or clics or hard_bounces or soft_bounces:
					# Extraer nombre de campaña y fecha de envío del primer elemento procesado
					nombre_campania_param = ""
					fecha_envio_param = ""
					
					if general and len(general) > 0 and len(general[0]) >= 3:
						nombre_campania_param = general[0][0]  # Primer campo: nombre de campaña
						fecha_envio_raw = general[0][2]  # Tercer campo: fecha de envío
						fecha_envio_param = formatear_fecha_envio(fecha_envio_raw)

					config = load_config()
					debug_mode = config.get("debug", False)
					log_info(f"📁 Generando archivo ({'CSV' if debug_mode else 'Excel'}) para campaña: {nombre_campania_param or id}, debug_mode: {debug_mode}")
					archivo_creado = crear_archivo_excel(
						general,
						[abiertos2, no_abiertos, clics, hard_bounces, soft_bounces],
						nombre_campania_param,
						fecha_envio_param
					)
					log_success(f"Archivo {'CSV' if debug_mode else 'Excel'} creado", archivo=archivo_creado, campania_id=id, debug_mode=debug_mode)
					campanias_exitosas += 1

			browser.close()
			log_info("🌐 Navegador cerrado")

			# Verificar si hubo errores en alguna campaña
			if errores_campanias:
				if campanias_exitosas == 0:
					# Todas las campañas fallaron
					if len(errores_campanias) == 1:
						error_summary = errores_campanias[0]
					else:
						error_summary = "Todas las campañas seleccionadas fallaron: " + "; ".join(errores_campanias[:2])
						if len(errores_campanias) > 2:
							error_summary += f" (y {len(errores_campanias) - 2} más)"
				else:
					# Algunas campañas fallaron
					error_summary = f"Errores en {len(errores_campanias)} de {len(campanias_a_buscar)} campañas: " + "; ".join(errores_campanias[:2])
					if len(errores_campanias) > 2:
						error_summary += f" (y {len(errores_campanias) - 2} más)"
				
				log_error("Proceso completado con errores", 
						 campanias_exitosas=campanias_exitosas, 
						 campanias_fallidas=len(errores_campanias),
						 total_campanias=len(campanias_a_buscar))
				raise Exception(error_summary)
			
			log_success("🎉 Proceso completado exitosamente", 
					   campanias_procesadas=campanias_exitosas, 
					   total_campanias=len(campanias_a_buscar))
					
				
	
	except Exception as e:
		log_error(f"Error en proceso principal: {e}", error_type=type(e).__name__)
		notify("Error en proceso", str(e))
		
if __name__ == "__main__":
	main()