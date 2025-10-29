import csv
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from datetime import datetime
from typing import List

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from .infrastructure.api.models.campanias import CampaignBasicInfo
from .excel_utils import agregar_datos, crear_hoja_con_datos, obtener_o_crear_hoja
from .shared.utils.legacy_utils import cargar_campanias_a_buscar, crear_contexto_navegador, configurar_navegador, load_config, data_path, notify, storage_state_path
from .shared.logging.logger import get_logger
from .structured_logger import log_success, log_error, log_warning, log_info, log_performance, log_data_extraction
from .hybrid_service import HybridDataService
from .core.authentication.authentication_service import AuthenticationService
from .core.config.config_manager import ConfigManager
from .shared.utils.retry_utils import retry_with_backoff, is_connection_error
from .infrastructure.scraping.endpoints.campanias import CampaignsScraper

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
	logger.debug("📝 Generando nombre de archivo de informe", nombre_campania=nombre_campania, fecha_envio=fecha_envio)

	ahora = datetime.now()
	fecha_extraccion = ahora.strftime("%Y%m%d%H%M")

	if nombre_campania and fecha_envio:
		# Limpiar nombre de campaña de caracteres problemáticos para nombres de archivo
		nombre_limpio = re.sub(r'[<>:"/\\|?*]', '_', nombre_campania)
		nombre_archivo = f"{nombre_limpio}-{fecha_envio}_{fecha_extraccion}.xlsx"
		logger.debug("✅ Nombre generado con formato personalizado", nombre_limpio=nombre_limpio)
	else:
		# Fallback al formato anterior si no se proporcionan los parámetros
		nombre_archivo = f"{ARCHIVO_INFORMES_PREFIX}_{fecha_extraccion}.xlsx"
		logger.debug("✅ Nombre generado con formato por defecto")

	# Asegurar que el nombre de archivo esté en el directorio data/suscriptores
	if nombre_campania and fecha_envio:
		nombre_archivo = data_path(f"suscriptores/{nombre_archivo}")
	else:
		nombre_archivo = data_path(nombre_archivo.replace(f"{ARCHIVO_INFORMES_PREFIX}_", ""))

	logger.info("✅ Nombre de archivo de informe generado", archivo=nombre_archivo)
	return nombre_archivo

def crear_archivo_csv(general: list[list[str]], informe_detallado: list[list[list[str]]], nombre_campania: str = "", fecha_envio: str = "", campaign_urls: list[list] = None):
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

        # Crear archivo CSV para URLs de Clics si están disponibles
        total_archivos = len(archivos_config) + 1  # +1 por General
        if campaign_urls:
            archivo_urls = directorio_csv / f"{nombre_base}_URLs_de_Clics.csv"
            with open(archivo_urls, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["URL", "Clics Totales", "Porcentaje de Abridores"])
                writer.writerows(campaign_urls)
            log_data_extraction("URLs de Clics", len(campaign_urls), "CSV")
            total_archivos += 1

        log_success(f"Archivos CSV creados exitosamente en: {directorio_csv}",
                   total_archivos=total_archivos, directorio=directorio_csv)
        
        return str(directorio_csv)
        
    except Exception as e:
        log_error(f"Error creando archivos CSV: {e}", 
                 campania=nombre_campania, fecha_envio=fecha_envio)
        raise


def crear_archivo_excel(general: list[list[str]], informe_detallado: list[list[list[str]]], nombre_campania: str = "", fecha_envio: str = "", campaign_urls: list[list] = None):
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
            return crear_archivo_csv(general, informe_detallado, nombre_campania, fecha_envio, campaign_urls)
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
        total_hojas = len(hojas_config) + 1  # +1 por General
        for nombre_hoja, datos, columnas in hojas_config:
            crear_hoja_con_datos(wb, nombre_hoja, datos, columnas)
            log_data_extraction(nombre_hoja, len(datos), "base de datos")

            # Log adicional para "No abiertos" para diagnosticar problemas
            if nombre_hoja == "No abiertos":
                if len(datos) == 0:
                    log_warning("⚠️ Hoja 'No abiertos' creada pero SIN DATOS",
                              nombre_hoja=nombre_hoja,
                              campania=nombre_campania)
                else:
                    log_info("✅ Hoja 'No abiertos' creada con datos exitosamente",
                            nombre_hoja=nombre_hoja,
                            total_registros=len(datos),
                            muestra_primer_registro=datos[0] if datos else None)

        # Crear hoja de URLs de Clics si están disponibles
        if campaign_urls:
            crear_hoja_con_datos(
                wb,
                "URLs de Clics",
                campaign_urls,
                ["URL", "Clics Totales", "Porcentaje de Abridores"]
            )
            log_data_extraction("URLs de Clics", len(campaign_urls), "base de datos")
            total_hojas += 1

        nombre_archivo = generar_nombre_archivo_informe(nombre_campania, fecha_envio)
        wb.save(nombre_archivo)

        log_success(f"Archivo Excel creado exitosamente: {nombre_archivo}",
                   total_hojas=total_hojas, archivo=nombre_archivo)
        
        return nombre_archivo
        
    except Exception as e:
        log_error(f"Error creando archivo Excel: {e}", 
                 campania=nombre_campania, fecha_envio=fecha_envio)
        raise

def get_campaign_urls_with_fallback(page, campaign_id: int) -> str:
	"""
	Obtiene la URL del correo de una campaña mediante scraping.
	Extrae la URL del botón "Ver email" que enlaza a clickacm.com desde la página de suscriptores.
	"""
	from .shared.logging.logger import get_logger
	logger = get_logger()

	try:
		logger.start_timer(f"scraping_email_url_campaign_{campaign_id}")
		logging.info(f"📧 Extrayendo URL del correo de la campaña {campaign_id}")

		# Paso 1: Navegar a la página de suscriptores (donde está el botón "Ver email")
		logging.debug("📌 Paso 1: Navegando a página de suscriptores de la campaña")
		try:
			# CORREGIDO: Navegar a página /subscribers/ en lugar de /report/
			subscribers_page = f"https://acumbamail.com/report/campaign/{campaign_id}/subscribers/"
			logging.debug(f"🌐 Navegando a: {subscribers_page}")

			page.goto(subscribers_page, wait_until="networkidle", timeout=60000)
			logger.debug(f"   Navegado a: {subscribers_page}")
			logging.debug("✅ Navegación a suscriptores completada")

			# Esperar a que la página cargue completamente con networkidle
			page.wait_for_load_state("networkidle", timeout=30000)
			page.wait_for_timeout(2000)  # Espera aumentada para conexiones lentas
			logging.debug("✅ Página completamente cargada (networkidle + 2s)")

			# Verificar si fuimos redirigidos a login
			try:
				from .shared.utils.legacy_utils import is_on_login_page
				if is_on_login_page(page):
					logging.error(f"❌ Redirigido a login al intentar acceder a URL de correo de campaña {campaign_id}")
					logging.warning("⚠️ Sesión expirada - no se puede extraer URL del correo")
					logger.end_timer(f"scraping_email_url_campaign_{campaign_id}", "Sesión expirada")
					return ""
			except ImportError:
				logging.warning("⚠️ No se pudo importar is_on_login_page")

		except PWTimeoutError as e:
			logging.error(f"❌ ERROR PASO 1 - Timeout navegando a suscriptores: {e}")
			logging.error(f"⏱️ URL intentada: {subscribers_page}")
			logger.end_timer(f"scraping_email_url_campaign_{campaign_id}", f"Timeout: {e}")
			return ""
		except Exception as e:
			logging.error(f"❌ ERROR PASO 1 - Error navegando a suscriptores: {e}")
			logger.end_timer(f"scraping_email_url_campaign_{campaign_id}", f"Error: {e}")
			return ""

		# Buscar el enlace "Ver email" que contiene la URL de clickacm.com
		import re

		# Método 1: Buscar elemento con texto "Ver email"
		try:
			email_link = page.get_by_text("Ver email").get_attribute("href", timeout=5000)
			if email_link and "clickacm.com" in email_link:
				logger.debug(f"   URL del email encontrada (método 1): {email_link}")
				logger.end_timer(f"scraping_email_url_campaign_{campaign_id}",
				                f"URL extraída exitosamente")
				logger.success(f"✅ URL del email de campaña {campaign_id} extraída: {email_link}")
				return email_link
		except Exception as e:
			logger.debug(f"   Método 1 falló: {e}")

		# Método 2: Buscar en el HTML usando regex
		page_content = page.content()

		# Buscar URL de clickacm.com en el HTML
		# Patrón: https://clickacm.com/show/[ID alfanumérico]/
		pattern = r'(https://clickacm\.com/show/[a-zA-Z0-9-]+/)'
		matches = re.findall(pattern, page_content)

		if matches:
			# Tomar la primera coincidencia (debería ser única por campaña)
			email_url = matches[0]
			logger.debug(f"   URL del email encontrada (método 2): {email_url}")
			logger.end_timer(f"scraping_email_url_campaign_{campaign_id}",
			                f"URL extraída exitosamente")
			logger.success(f"✅ URL del email de campaña {campaign_id} extraída: {email_url}")
			return email_url

		# Si no encontramos nada
		logger.warning(f"⚠️ No se encontró URL del email para campaña {campaign_id}")
		logger.end_timer(f"scraping_email_url_campaign_{campaign_id}", "No encontrada")
		return ""

	except Exception as e:
		logger.error(f"❌ Error extrayendo URL del email de campaña {campaign_id}: {e}")
		logger.end_timer(f"scraping_email_url_campaign_{campaign_id}", f"Error: {e}")
		# En caso de error, devolver cadena vacía para no bloquear el proceso
		return ""

def generar_listas(todas_listas, id_listas: list[str]) -> str:
	logger.debug("📋 Generando string de listas", total_listas=len(todas_listas), id_listas_count=len(id_listas))

	listas_ar = []
	for lista in todas_listas:
		if lista.id in id_listas:
			listas_ar.append(lista.name or "")
			logger.debug(f"  ✅ Lista encontrada: {lista.name}", lista_id=lista.id)

	listas = ", ".join(listas_ar)
	logger.info("✅ String de listas generado", listas_encontradas=len(listas_ar), resultado=listas)
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
	lista = mapa_email_lista.get(email_clean, "Lista no encontrada")
	logger.debug("📧 Consultando lista de suscriptor", email=email_clean, lista_encontrada=lista)
	return lista

def generar_general(campania: CampaignBasicInfo, campania_complete, campaign_clics, todas_listas, page, campaign_id=None) -> list[str]:
	from .shared.logging.logger import get_logger
	logger = get_logger()
	
	logger.debug("🚀 Iniciando generación de datos generales para campaña")
	logger.debug(f"   - Nombre campaña: {campania.name if campania.name else 'Sin nombre'}")
	logger.debug(f"   - ID pasado como parámetro: {campaign_id}")
	logger.debug(f"   - Objeto campania tiene atributo 'id': {hasattr(campania, 'id')}")
	if hasattr(campania, 'id'):
		logger.debug(f"   - Valor de campania.id: {getattr(campania, 'id', 'NO_DISPONIBLE')}")
	
	nombre = campania.name or ""
	tipo = ""
	fecha = campania.date_sent
	
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
	import argparse

	# Inicializar logger
	logger = get_logger()

	# Configurar argumentos de línea de comandos
	parser = argparse.ArgumentParser(description="Extracción de datos de campañas de Acumbamail")
	parser.add_argument("--validate", type=int, metavar="CAMPAIGN_ID",
	                   help="Validar datos de scraping para una campaña específica")
	parser.add_argument("--test", action="store_true",
	                   help="Ejecutar en modo prueba (solo validar, no crear archivos)")

	args = parser.parse_args()

	try:
		log_info("🚀 Iniciando proceso de extracción de campañas")

		config = load_config()
		extraccion_oculta = bool(config.get("headless", False))
		log_info("Configuración cargada", headless=extraccion_oculta, validate_mode=args.validate is not None)

		# Modo de validación para una campaña específica
		if args.validate:
			log_info(f"🔍 Modo validación activado para campaña {args.validate}")
			return validate_campaign(args.validate, extraccion_oculta)

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

			# Espera adicional post-login para asegurar estabilidad de sesión antes de operaciones de API
			log_info("⏳ Esperando estabilización completa de sesión antes de operaciones...")
			page.wait_for_load_state("networkidle", timeout=30000)
			page.wait_for_timeout(3000)  # 3 segundos adicionales para máxima estabilidad
			log_success("✅ Sesión completamente estabilizada, iniciando operaciones")

			# Inicializar servicio híbrido con la página autenticada
			hybrid_service = HybridDataService(page)
			api = hybrid_service.api  # Obtener instancia de API para consultas adicionales
			log_info("🔧 Servicio híbrido inicializado")

			# Inicializar scraper de campañas para extraer URLs
			campaigns_scraper = CampaignsScraper(page)
			log_info("🔗 Scraper de URLs de campañas inicializado")

			errores_campanias = []
			campanias_exitosas = 0

			for i, (id, nombre_campania) in enumerate(campanias_a_buscar):
				log_info(f"📊 Procesando campaña {i+1}/{len(campanias_a_buscar)}",
						campania_id=id, nombre=nombre_campania, progreso=f"{i+1}/{len(campanias_a_buscar)}")

				# Validar sesión antes de procesar cada campaña (especialmente después de la primera)
				if i > 0:  # Validar después de la primera campaña
					try:
						from .shared.utils.legacy_utils import validate_session, is_on_login_page

						# Verificar si la sesión sigue válida
						if is_on_login_page(page):
							log_warning(f"⚠️ Sesión expirada detectada antes de procesar campaña {id}")
							log_info("🔄 Re-autenticando...")

							# Re-autenticar
							login(page, context=context)
							log_success("✅ Sesión refrescada exitosamente")

							# Re-esperar estabilización
							page.wait_for_load_state("networkidle", timeout=30000)
							page.wait_for_timeout(3000)
							log_success("✅ Sesión estabilizada después de re-autenticación")
					except ImportError:
						log_warning("⚠️ No se pudo importar funciones de validación de sesión")
					except Exception as e:
						log_error(f"❌ Error validando sesión: {e}")
						# Continuar de todas formas, el scraping individual detectará el problema

				# Obtener datos completos usando servicio híbrido con reintentos
				try:
					def get_data():
						data = hybrid_service.get_complete_campaign_data(id)
						if not data or not data.get("campaign_basic"):
							raise Exception(f"No se pudieron obtener datos para la campaña '{nombre_campania}'")
						return data

					# Intentar con reintentos para manejar problemas de conexión
					log_info(f"Obteniendo datos de campaña {id} (con reintentos si es necesario)")
					complete_data = retry_with_backoff(
						func=get_data,
						max_retries=2,
						initial_delay=2.0,
						backoff_factor=1.5,
						logger=logger
					)

					log_success("Datos de campaña obtenidos", campania_id=id,
							   tiene_datos_basicos=bool(complete_data.get("campaign_basic")),
							   tiene_scraping=bool(complete_data.get("scraping_result")))

				except Exception as e:
					error_msg = f"La campaña '{nombre_campania}' no está disponible"

					# Verificar si es un error de conexión para dar un mensaje más específico
					if is_connection_error(e):
						error_msg = f"La campaña '{nombre_campania}' no pudo ser accedida (problema de conexión o carga lenta)"
						log_error(f"{error_msg}: {e}", campania_id=id, error_type=type(e).__name__, es_error_conexion=True)
					else:
						log_error(f"{error_msg}: {e}", campania_id=id, error_type=type(e).__name__, es_error_conexion=False)

					errores_campanias.append(error_msg)
					continue  # Continuar con la siguiente campaña

				# Extraer datos para compatibilidad con formato Excel existente
				campania: CampaignBasicInfo = complete_data["campaign_basic"]
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

					# Logging detallado de datos de scraping antes de conversión
					log_info("🔍 Datos de scraping obtenidos",
							campania_id=id,
							hard_bounces_count=len(scraping_result.hard_bounces) if scraping_result.hard_bounces else 0,
							no_opens_count=len(scraping_result.no_opens) if scraping_result.no_opens else 0)

					# Log de muestra de datos si existen
					if scraping_result.no_opens:
						log_info("📋 Muestra de 'No abiertos' extraídos (primeros 3)",
								campania_id=id,
								sample=scraping_result.no_opens[:3])
					else:
						log_warning("⚠️ Lista de 'No abiertos' está vacía", campania_id=id)

					hard_bounces = convert_hard_bounces_to_rows(scraping_result.hard_bounces)
					no_abiertos = convert_no_opens_to_rows(scraping_result.no_opens)

					# Logging después de conversión
					log_info("📊 Datos convertidos para Excel",
							campania_id=id,
							hard_bounces_rows=len(hard_bounces),
							no_abiertos_rows=len(no_abiertos))

					log_success("Scraping completado",
							   hard_bounces=len(hard_bounces), no_abiertos=len(no_abiertos))
				else:
					log_warning("No se pudieron obtener datos de scraping", campania_id=id)
					log_info("🔍 Detalle de complete_data",
							campania_id=id,
							has_scraping_result=bool(complete_data.get("scraping_result")),
							complete_data_keys=list(complete_data.keys()) if complete_data else [])

				# Extraer URLs de campaña con scraping
				campaign_urls_data = []
				try:
					log_info("🔗 Iniciando extracción de URLs de campaña", campania_id=id)
					campaign_urls = campaigns_scraper.get_campaign_urls(id)
					if campaign_urls:
						# Convertir a formato de filas para Excel: [URL, Clics, Porcentaje]
						campaign_urls_data = [
							[url.url, url.clicks, url.click_percentage]
							for url in campaign_urls
						]
						log_success("URLs de campaña extraídas",
								   urls_count=len(campaign_urls), campania_id=id)
					else:
						log_info("No se encontraron URLs en la campaña", campania_id=id)
				except Exception as e:
					log_warning(f"Error extrayendo URLs de campaña: {e}",
							   campania_id=id, error_type=type(e).__name__)
					# Continuar sin URLs, no es crítico

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
						fecha_envio_param,
						campaign_urls_data  # Agregar URLs de campaña
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
		
def validate_campaign(campaign_id: int, headless: bool = False) -> bool:
	"""
	Valida los datos de scraping para una campaña específica
	"""
	try:
		log_info(f"🔍 Iniciando validación de campaña {campaign_id}")

		with sync_playwright() as p:
			log_info("🌐 Iniciando navegador para validación")
			browser = configurar_navegador(p, headless)
			context = crear_contexto_navegador(browser, headless)

			page = context.new_page()

			log_info("🔐 Iniciando proceso de autenticación")
			login(page, context=context)
			log_success("Autenticación completada exitosamente")

			# Inicializar servicio híbrido para validación
			hybrid_service = HybridDataService(page)
			log_info("🔧 Servicio híbrido inicializado para validación")

			# Ejecutar validación
			log_info(f"🔍 Ejecutando validación para campaña {campaign_id}")
			validation_report = hybrid_service.validate_scraping_data(campaign_id)

			# Mostrar resultados de validación
			print("\n" + "="*80)
			print(f"📊 REPORTE DE VALIDACIÓN - CAMPAÑA {campaign_id}")
			print("="*80)

			print(f"Timestamp: {validation_report['timestamp']}")
			print(f"Success: {'✅' if validation_report['success'] else '❌'}")

			print("\n📈 Resultados por tipo:")
			for tipo, resultados in validation_report['validation_results'].items():
				print(f"\n{tipo.title()}:")
				print(f"  • Web count: {resultados['web_count']}")
				print(f"  • Extracted count: {resultados['extracted_count']}")
				print(f"  • Match: {'✅' if resultados['match'] else '❌'}")

				if resultados['sample_extracted_data']:
					print(f"  • Sample extracted data:")
					for i, sample in enumerate(resultados['sample_extracted_data'][:3], 1):
						print(f"    {i}. {sample}")

			if validation_report['errors']:
				print(f"\n❌ Errores encontrados:")
				for error in validation_report['errors']:
					print(f"  • {error}")

			# Conclusión
			if validation_report['success']:
				print(f"\n✅ Validación exitosa - Todos los datos coinciden")
				log_success(f"Validación exitosa para campaña {campaign_id}")
				return True
			else:
				print(f"\n❌ Validación fallida - Hay discrepancias en los datos")
				log_error(f"Validación fallida para campaña {campaign_id}")
				return False

	except Exception as e:
		log_error(f"Error en validación de campaña {campaign_id}: {e}")
		print(f"\n❌ Error en validación: {e}")
		return False

if __name__ == "__main__":
	main()