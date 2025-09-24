from playwright.sync_api import sync_playwright
from datetime import datetime
from typing import List

try:
    # Intentar imports relativos (cuando se ejecuta como módulo)
    from .excel_utils import agregar_datos, crear_hoja_con_datos, obtener_o_crear_hoja
    from .autentificacion import login
    from .utils import cargar_campanias_a_buscar, crear_contexto_navegador, configurar_navegador, load_config, data_path, notify
    from .logger import get_logger
    from .structured_logger import log_success, log_error, log_warning, log_info, log_performance, log_data_extraction
    from .hybrid_service import HybridDataService
except ImportError:
    # Imports absolutos (cuando se ejecuta como script independiente)
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from excel_utils import agregar_datos, crear_hoja_con_datos, obtener_o_crear_hoja
    from autentificacion import login
    from utils import cargar_campanias_a_buscar, crear_contexto_navegador, configurar_navegador, load_config, data_path, notify
    from logger import get_logger
    from structured_logger import log_success, log_error, log_warning, log_info, log_performance, log_data_extraction
    from hybrid_service import HybridDataService

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

def crear_archivo_excel(general: list[list[str]], informe_detallado: list[list[list[str]]], nombre_campania: str = "", fecha_envio: str = ""):
    """
    Crea el archivo Excel con los informes recopilados
    """
    try:
        log_info(f"Iniciando creación de archivo Excel", 
                campania=nombre_campania, fecha_envio=fecha_envio)
        
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
		log_info(f"Iniciando creación de mapa email-lista", total_listas=len(todas_listas))

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

		log_success(f"Mapa email-lista completado", 
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

def generar_general(campania, campania_complete, campaign_clics, todas_listas) -> list[str]:
	nombre = campania.name or ""
	tipo = ""
	fecha = campania.date
	
	id_listas = campania.lists or []
	listas = generar_listas(todas_listas, id_listas)
	emails = str(campania_complete.total_delivered)
	opens = str(campania_complete.opened or 0)
	clicks = str(len(campaign_clics))
	url_email = ""
	
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
		log_info(f"Configuración cargada", headless=extraccion_oculta)

		campanias_a_buscar = cargar_campanias_a_buscar(ARCHIVO_BUSQUEDA)
		log_info(f"Campañas a procesar", total_campanias=len(campanias_a_buscar))
		
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
					
					log_success(f"Datos de campaña obtenidos", campania_id=id, 
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
				general = [generar_general(campania, campania_complete, campaign_clics, todas_listas)]
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
					log_success(f"Scraping completado", 
							   hard_bounces=len(hard_bounces), no_abiertos=len(no_abiertos))
				else:
					log_warning(f"No se pudieron obtener datos de scraping", campania_id=id)

				# Crear archivo Excel con los resultados
				if general or abiertos2 or no_abiertos or clics or hard_bounces or soft_bounces:
					# Extraer nombre de campaña y fecha de envío del primer elemento procesado
					nombre_campania_param = ""
					fecha_envio_param = ""
					
					if general and len(general) > 0 and len(general[0]) >= 3:
						nombre_campania_param = general[0][0]  # Primer campo: nombre de campaña
						fecha_envio_raw = general[0][2]  # Tercer campo: fecha de envío
						fecha_envio_param = formatear_fecha_envio(fecha_envio_raw)

					archivo_creado = crear_archivo_excel(
						general,
						[abiertos2, no_abiertos, clics, hard_bounces, soft_bounces],
						nombre_campania_param,
						fecha_envio_param
					)
					log_success(f"Archivo Excel creado", archivo=archivo_creado, campania_id=id)
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
						error_summary = f"Todas las campañas seleccionadas fallaron: " + "; ".join(errores_campanias[:2])
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