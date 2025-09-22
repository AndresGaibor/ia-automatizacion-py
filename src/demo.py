from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page
from datetime import datetime

from .excel_utils import agregar_datos, crear_hoja_con_datos, obtener_o_crear_hoja

from .api.models.campanias import CampaignBasicInfo

from .api import API
from .autentificacion import login
from .utils import cargar_id_campanias_a_buscar, crear_contexto_navegador, configurar_navegador, navegar_siguiente_pagina, obtener_total_paginas, load_config, data_path, notify
from .logger import get_logger
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
        [abiertos, no_abiertos, clics, hard_bounces, soft_bounces] = informe_detallado
        
        # Crear libro y hoja general
        wb = Workbook()
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

        nombre_archivo = generar_nombre_archivo_informe(nombre_campania, fecha_envio)
        wb.save(nombre_archivo)
        
        return nombre_archivo
        
    except Exception as e:
        print(f"❌ Error creando archivo Excel: {e}")
        raise

def generar_listas(todas_listas, id_listas: list[str]) -> str:
	listas_ar = []
	for lista in todas_listas:
		if lista.id in id_listas:
			listas_ar.append(lista.name or "")
	listas = ", ".join(listas_ar)
	return listas

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

def generar_abiertos(campania, openers, todas_listas) -> list[list[str]]:
	abiertos: list[list[str]] = []
	
	lista = generar_listas(todas_listas, campania.lists or [])
	
	for opener in openers:
		proyecto = campania.name or ""
		# lista = generar_listas(todas_listas, campania.lists or [])
		correo = opener.email or ""
		fecha_apertura = opener.open_datetime or ""
		pais = ""
		aperturas = ""
		lista2 = lista
		estado = "Activo"
		calidad = ""

		abiertos.append([proyecto, lista, correo, fecha_apertura, pais, aperturas, lista2, estado, calidad])
	return abiertos

def generar_clics(campania, campaign_clics, todas_listas) -> list[list[str]]:
	clics: list[list[str]] = []
	
	lista = generar_listas(todas_listas, campania.lists or [])
	
	for click in campaign_clics:
		proyecto = campania.name or ""
		# lista = generar_listas(todas_listas, campania.lists or [])
		correo = click.email or ""
		fecha_clic = click.click_datetime or ""
		pais = ""
		lista2 = lista
		estado = "Activo"
		calidad = ""

		clics.append([proyecto, lista, correo, fecha_clic, pais, lista2, estado, calidad])
	return clics

def generar_soft_bounces(campania, soft_bounce_list, todas_listas) -> list[list[str]]:
	soft_bounces: list[list[str]] = []
	
	lista = generar_listas(todas_listas, campania.lists or [])
	
	for bounce in soft_bounce_list:
		proyecto = campania.name or ""
		# lista = generar_listas(todas_listas, campania.lists or [])
		correo = bounce.email or ""
		lista2 = lista
		estado = "Activo"
		calidad = ""

		soft_bounces.append([proyecto, lista, correo, lista2, estado, calidad])
	return soft_bounces

def seleccionar_filtro(page: Page, label: str) -> bool:
	"""
	Selecciona un filtro en el selector de la página actual.
	Devuelve True si se seleccionó correctamente, False en caso contrario.
	"""
	try:
		select_filtro = page.locator("#query-filter")
		select_filtro.select_option(label=label)
		page.wait_for_load_state("networkidle")
		return True
	except Exception as e:
		get_logger().error(f"Error seleccionando filtro '{label}': {e}")
		return False

def extraer_suscriptores_tabla(page: Page, cantidad_campos) -> list[list[str]]:
	suscriptores = []
	page.wait_for_load_state("networkidle")

	contenedor_tabla = page.locator("div").filter(has_text="Abiertos No abiertos Clics").nth(1)
	filas = contenedor_tabla.locator("> li")
	filas_total = filas.count()

	for fila_i in range(1, filas_total):
		campos = filas.nth(fila_i).locator("> div")

		campos_arr = []

		for i in range(0, cantidad_campos - 1):
			campo = campos.nth(i).inner_text()
			campos_arr.append(campo)
		
		suscriptores.append(campos_arr)

	return suscriptores

def navegar_a_detalle_sucriptores(page: Page, campaign_id) -> bool:
	"""
	Navega a la sección de detalles de suscriptores de la campaña.
	Devuelve True si se navegó correctamente, False en caso contrario.
	"""
	try:
		config = load_config()
		url_base = config.get("url_base", "")
		url = f"{url_base}/report/campaign/{campaign_id}/"
		page.goto(url)

		page.get_by_role("link", name="Detalles suscriptores").click()
		page.wait_for_load_state("networkidle")
		return True
	except Exception as e:
		get_logger().error(f"Error navegando a Detalles suscriptores: {e}")
		return False

def generar_hard_bounces(page: Page, campania: CampaignBasicInfo, campaign_id: int) -> list[list[str]]:
	"""
	Scrapea Hard bounces de la campaña y devuelve filas:
	[Proyecto, Lista, Correo, Lista, Estado, Calidad]
	"""
	suscriptores: list[list[str]] = []
	try:
		navegar_a_detalle_sucriptores(page, campaign_id)

		seleccionar_filtro(page, "Hard bounces")

		paginas_totales = obtener_total_paginas(page)
		for numero_pagina in range(1, paginas_totales + 1):
			
			suscriptores = extraer_suscriptores_tabla(page, 4)

			for suscriptor in suscriptores:
				email = suscriptor[0]
				lista = suscriptor[1]
				estado = suscriptor[2]
				calidad = suscriptor[3]

				suscriptores.append([campania.name or "", lista, email, lista, estado, calidad])

			if numero_pagina < paginas_totales:
				if not navegar_siguiente_pagina(page, numero_pagina):
					break
	except Exception as e:
		get_logger().error(f"Error generando Hard bounces para campaña {campaign_id}: {e}")
	return suscriptores

def generar_no_abiertos(page: Page, campania: CampaignBasicInfo, campaign_id: int) -> list[list[str]]:
	"""
	Scrapea No abiertos en la página de detalles abierta y devuelve filas:
	[Proyecto, Lista, Correo, Lista, Estado, Calidad]
	Nota: Asume que ya estamos en la vista de 'Detalles suscriptores' de la campaña.
	"""
	suscriptores: list[list[str]] = []
	try:
		seleccionar_filtro(page, "No abiertos")

		paginas_totales = obtener_total_paginas(page)
		for numero_pagina in range(1, paginas_totales + 1):

			suscriptores = extraer_suscriptores_tabla(page, 4)

			for suscriptor in suscriptores:
				email = suscriptor[0]
				lista = suscriptor[1]
				estado = suscriptor[2]
				calidad = suscriptor[3]

				suscriptores.append([campania.name or "", lista, email, lista, estado, calidad])

			if numero_pagina < paginas_totales:
				if not navegar_siguiente_pagina(page, numero_pagina):
					break
	except Exception as e:
		get_logger().error(f"Error generando No abiertos para campaña {campaign_id}: {e}")
	return suscriptores

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
			"%d-%m-%Y %H:%M", 
			"%Y-%m-%d %H:%M",
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
			# Si no se puede parsear, usar el texto directamente limpiando caracteres problemáticos
			fecha_envio_param = re.sub(r'[<>:"/\\|?*\s]', '', fecha_str)
	except Exception as e:
		fecha_envio_param = re.sub(r'[<>:"/\\|?*\s]', '', fecha_str)

	return fecha_envio_param

def main():
	try:
		config = load_config()
		extraccion_oculta = bool(config.get("headless", False))

		ids_a_buscar = cargar_id_campanias_a_buscar(ARCHIVO_BUSQUEDA)
		
		with sync_playwright() as p:
			browser = configurar_navegador(p, extraccion_oculta)
			context = crear_contexto_navegador(browser, extraccion_oculta)
			
			page = context.new_page()
			
			login(page, context= context)

			api = API()

			for i, id in enumerate(ids_a_buscar):
				# GENERAL
				campania = api.campaigns.get_basic_info(id)
				campania_complete = api.campaigns.get_total_info(id)
				campaign_clics = api.campaigns.get_clicks(id)
				todas_listas = api.suscriptores.get_lists()

				general = [generar_general(campania, campania_complete, campaign_clics, todas_listas)]

				# ABIERTOS
				openers = api.campaigns.get_openers(id)
				abiertos2 = generar_abiertos(campania, openers, todas_listas)

				# CLICS
				clics = generar_clics(campania, campaign_clics, todas_listas)

				# SOFT BOUNCES
				soft_bounce_list = api.campaigns.get_soft_bounces(id)
				soft_bounces = generar_soft_bounces(campania, soft_bounce_list, todas_listas)

				# HARD BOUNCES (scraping) y NO ABIERTOS (scraping)
				hard_bounces = generar_hard_bounces(page, campania, id)
				no_abiertos = generar_no_abiertos(page, campania, id)

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
			browser.close()
			notify("Proceso finalizado", "Extracción de suscriptores completada")
				
				
	
	except Exception as e:
		print(f"❌ Error en proceso principal: {e}")
		notify("Error en proceso", str(e))
		
if __name__ == "__main__":
	main()