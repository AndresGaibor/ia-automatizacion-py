from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page
from datetime import datetime
from .autentificacion import login
from .utils import cargar_terminos_busqueda, crear_contexto_navegador, configurar_navegador, navegar_a_reportes, navegar_siguiente_pagina, obtener_total_paginas, load_config, data_path, storage_state_path, notify
from openpyxl import Workbook, load_workbook
import pandas as pd
import time
import os

ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")
ARCHIVO_INFORMES_PREFIX = data_path("informes")

REAL_UA = (
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/537.36 "
	"(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

def buscar_campania_por_termino(page: Page, termino: list[str], buscador) -> list[str]:
	"""
	Busca una campaña específica por término y retorna sus datos
	"""
	navegar_a_reportes(page)
	
	buscador.fill("")
	buscador.fill(termino[0])
	page.keyboard.press("Enter")
	
	page.wait_for_load_state('networkidle')
	
	tabla_reporte = page.locator('#newsletter-reports')
	
	# Esperar a que la tabla esté disponible
	tabla_reporte.locator('> li').first.wait_for(timeout=60000)
	
	tds = tabla_reporte.locator('> li')
	cantidad_reportes = tds.count()
	
	divs = None
	for g in range(0, cantidad_reportes):
		try:
			td = tds.nth(g)
			div = td.locator('> div')
			
			# Verificar que el elemento existe antes de acceder al texto
			if div.first.count() == 0:
				continue
				
			nombre_txt = div.first.inner_text()
			if div.nth(3).count() == 0:
				continue
			listas = div.nth(3).inner_text()
			
			if(nombre_txt.strip() == termino[0] and listas.strip() == termino[1]):
				divs = td.locator('> div')
				break
		except Exception as e:
			print(f"Error procesando elemento {g}: {e}")
			continue
	
	if divs is None:
		raise Exception(f"No se encontró la campaña: {termino[0]} - {termino[1]}")
	
	# Extraer datos de la campaña
	# nombre_txt = divs.first.inner_text()
	# tipo = divs.nth(1).inner_text()
	# fecha_envio = divs.nth(2).inner_text()
	# listas = divs.nth(3).inner_text()
	# emails = divs.nth(4).inner_text()
	# abiertos = divs.nth(5).inner_text()
	# clics = divs.nth(6).inner_text()
	
	campos = [divs.nth(i).inner_text() for i in range(7)]
	
	# Hacer clic en la campaña
	divs.locator('a').first.click()
	
	# Obtener URL del correo
	url_correo = page.get_by_role('link', name="Ver email")
	href_correo = url_correo.get_attribute('href') or ""
	campos.append(href_correo)
	return campos

def obtener_suscriptores_abrieron(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:
	suscriptores_abrieron = []
	paginas_totales = obtener_total_paginas(page)

	for numero_pagina in range(1, paginas_totales + 1):
		tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
		suscriptores = tabla_suscriptores.locator('> li')
		cantidad_suscriptores = suscriptores.count()
		
		for i in range(1, cantidad_suscriptores):  # empieza en 1 → segundo elemento
			datos_suscriptor = suscriptores.nth(i).locator('> div')
			
			correo = datos_suscriptor.nth(0).inner_text()
			fecha_apertura = datos_suscriptor.nth(1).inner_text()
			pais_apertura = datos_suscriptor.nth(2).inner_text()
			aperturas = datos_suscriptor.nth(3).inner_text()
			lista = datos_suscriptor.nth(4).inner_text()
			estado = datos_suscriptor.nth(5).inner_text()
			calidad = datos_suscriptor.nth(6).inner_text()
			
			suscriptores_abrieron.append([
				nombre_campania, lista, correo, fecha_apertura, pais_apertura, aperturas, lista, estado, calidad
			])

		if numero_pagina < paginas_totales:
			if not navegar_siguiente_pagina(page, numero_pagina):
				break
	return suscriptores_abrieron

def obtener_suscriptores_no_abrieron(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:
	suscriptores_abrieron = []
	paginas_totales = obtener_total_paginas(page)

	for numero_pagina in range(1, paginas_totales + 1):
		tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
		suscriptores = tabla_suscriptores.locator('> li')
		cantidad_suscriptores = suscriptores.count()
		
		for i in range(1, cantidad_suscriptores):  # empieza en 1 → segundo elemento
			datos_suscriptor = suscriptores.nth(i).locator('> div')
			
			correo = datos_suscriptor.nth(0).inner_text()
			lista = datos_suscriptor.nth(1).inner_text()
			estado = datos_suscriptor.nth(2).inner_text()
			calidad = datos_suscriptor.nth(3).inner_text()
			
			suscriptores_abrieron.append([
				nombre_campania, lista, correo, lista, estado, calidad
			])

		if numero_pagina < paginas_totales:
			if not navegar_siguiente_pagina(page, numero_pagina):
				break
	return suscriptores_abrieron

def obtener_suscriptores_hicieron_clic(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:
	suscriptores_abrieron = []
	paginas_totales = obtener_total_paginas(page)

	for numero_pagina in range(1, paginas_totales + 1):
		tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
		suscriptores = tabla_suscriptores.locator('> li')
		cantidad_suscriptores = suscriptores.count()
		
		for i in range(1, cantidad_suscriptores):  # empieza en 1 → segundo elemento
			datos_suscriptor = suscriptores.nth(i).locator('> div')
			
			correo = datos_suscriptor.nth(0).inner_text()
			fecha_apertura = datos_suscriptor.nth(1).inner_text()
			pais_apertura = datos_suscriptor.nth(2).inner_text()
			lista = datos_suscriptor.nth(3).inner_text()
			estado = datos_suscriptor.nth(4).inner_text()
			calidad = datos_suscriptor.nth(5).inner_text()
			
			suscriptores_abrieron.append([
				nombre_campania, lista, correo, fecha_apertura, pais_apertura, lista, estado, calidad
			])

		if numero_pagina < paginas_totales:
			if not navegar_siguiente_pagina(page, numero_pagina):
				break
	return suscriptores_abrieron

def obtener_suscriptores_soft_bounces(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:
	suscriptores_abrieron = []
	paginas_totales = obtener_total_paginas(page)

	for numero_pagina in range(1, paginas_totales + 1):
		tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
		suscriptores = tabla_suscriptores.locator('> li')
		cantidad_suscriptores = suscriptores.count()
		
		for i in range(1, cantidad_suscriptores):  # empieza en 1 → segundo elemento
			datos_suscriptor = suscriptores.nth(i).locator('> div')
			
			correo = datos_suscriptor.nth(0).inner_text()
			lista = datos_suscriptor.nth(1).inner_text()
			estado = datos_suscriptor.nth(2).inner_text()
			calidad = datos_suscriptor.nth(3).inner_text()
			
			suscriptores_abrieron.append([
				nombre_campania, lista, correo, lista, estado, calidad
			])

		if numero_pagina < paginas_totales:
			if not navegar_siguiente_pagina(page, numero_pagina):
				break
	return suscriptores_abrieron

def obtener_suscriptores_hard_bounces(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:	
	return obtener_suscriptores_soft_bounces(page, nombre_campania, lista)

def obtener_listado_suscriptores(page: Page, nombre_campania: str, lista: str) -> list[list[list[str]]]:
	"""
	Obtiene los listado de todos los suscriptores de una campaña
	"""
	
	page.get_by_role('link', name="Detalles suscriptores").click()

	filtro = page.locator('select#query-filter')

	try:
		abrieron = obtener_suscriptores_abrieron(page, nombre_campania, lista) or []
	except Exception as e:
		print(f"Error obteniendo suscriptores que abrieron: {e}")
		abrieron = []

	try:
		filtro.select_option(label="No abiertos")
		no_abrieron = obtener_suscriptores_no_abrieron(page, nombre_campania, lista) or []
	except Exception as e:
		print(f"Error obteniendo suscriptores que no abrieron: {e}")
		no_abrieron = []

	try:
		filtro.select_option(label="Clics")
		clics = obtener_suscriptores_hicieron_clic(page, nombre_campania, lista) or []
	except Exception as e:
		print(f"Error obteniendo suscriptores que hicieron clic: {e}")
		clics = []

	try:
		filtro.select_option(label="Hard bounces")
		hard_bounces = obtener_suscriptores_hard_bounces(page, nombre_campania, lista) or []
	except Exception as e:
		print(f"Error obteniendo hard bounces: {e}")
		hard_bounces = []

	try:
		filtro.select_option(label="Soft bounces")
		soft_bounces = obtener_suscriptores_soft_bounces(page, nombre_campania, lista) or []
	except Exception as e:
		print(f"Error obteniendo soft bounces: {e}")
		soft_bounces = []
	return [abrieron, no_abrieron, clics, hard_bounces, soft_bounces]

def procesar_seguimiento_urls(page: Page, informe_detallado: list[list[str]]):
	"""
	Procesa el seguimiento de URLs y marca los clics en el informe detallado
	"""
	page.get_by_role('link', name="Seguimiento url's").click()
	page.wait_for_load_state('networkidle')
	
	# Inicializar todos los registros con cadena vacía para seguimiento URL
	for detalle in informe_detallado:
		if len(detalle) < 9:
			detalle.append("")
	
	try:
		tabla_urls_seguimiento = page.locator('ul').filter(has=page.locator("span", has_text="Han hecho clic"))
		urls_seguimiento = tabla_urls_seguimiento.locator('> li')
		cantidad_url_seguimiento = urls_seguimiento.count()
		
		for z in range(1, cantidad_url_seguimiento):
			try:
				tabla_urls_seguimiento = page.locator('ul').filter(has=page.locator("span", has_text="Han hecho clic"))
				urls_seguimiento = tabla_urls_seguimiento.locator('> li')
				
				col_acciones = urls_seguimiento.nth(z).locator('> div')
				btn_menu = col_acciones.last.locator('a').first
				btn_menu.click()

				urls_seguimiento.nth(z).get_by_role('link', name="Detalles").click()

				# vamos a recorrer cada pagina de clics de cada url de seguimiento
				paginas_totales = obtener_total_paginas(page)
				
				for numero_pagina in range(1, paginas_totales + 1):
					tabla_clics = page.locator('ul').filter(has=page.locator("span", has_text="Suscriptores que han hecho clic"))
					clics = tabla_clics.locator('> li')
					cantidad_clics = clics.count()
					
					for k in range(1, cantidad_clics):  # empieza en 1 → segundo elemento
						email = clics.nth(k).inner_text()
						for detalle in informe_detallado:
							if detalle[2].strip() == email.strip():
								# Marcar como "SI" si ya no está marcado
								if len(detalle) >= 10:
									detalle[9] = "SI"
								else:
									detalle.append("SI")
					# Navegar a siguiente página si no es la última
					if numero_pagina < paginas_totales:
						if not navegar_siguiente_pagina(page, numero_pagina):
							break
				
				page.go_back(wait_until='networkidle')
			except Exception as e:
				print(f"Error procesando seguimiento URL {z}: {e}")
				continue
	except Exception as e:
		print(f"Error general en seguimiento URLs: {e}")

def crear_archivo_excel(general: list[list[str]], informe_detallado: list[list[list[str]]]):
	"""
	Crea el archivo Excel con los informes recopilados
	"""
	[abiertos, no_abiertos, clics, hard_bounces, soft_bounces] = informe_detallado
	# Crear un libro y una hoja
	wb = Workbook()
	ws = wb.active
	if ws is not None:
		ws.title = "General"
	else:
		ws = wb.create_sheet(title="General")
	
	# Escribir datos de la primera hoja
	ws['A1'] = "Nombre"
	ws['B1'] = "Tipo"
	ws['C1'] = "Fecha envio"
	ws['D1'] = "Listas"
	ws['E1'] = "Emails"
	ws['F1'] = "Abiertos"
	ws['G1'] = "Clics"
	ws['H1'] = "URL de Correo"
	
	for fila in general:
		ws.append(fila)
	
	# Crear segunda hoja
	ws = wb.create_sheet(title="Abiertos")
	
	ws['A1'] = "Proyecto"
	ws['B1'] = "Lista"
	ws['C1'] = "Correo"
	ws['D1'] = "Fecha apertura"
	ws['E1'] = "País apertura"
	ws['F1'] = "Aperturas"
	ws['G1'] = "Lista"
	ws['H1'] = "Estado"
	ws['I1'] = "Calidad"

	for fila in abiertos:
		ws.append(fila)

	ws = wb.create_sheet(title="No abiertos")
	
	ws['A1'] = "Proyecto"
	ws['B1'] = "Lista"
	ws['C1'] = "Correo"
	ws['D1'] = "Lista"
	ws['E1'] = "Estado"
	ws['F1'] = "Calidad"
	
	for fila in no_abiertos:
		ws.append(fila)
	
	ws = wb.create_sheet(title="Clics")
	
	ws['A1'] = "Proyecto"
	ws['B1'] = "Lista"
	ws['C1'] = "Correo"
	ws['D1'] = "Fecha primer clic"
	ws['E1'] = "País apertura"
	ws['F1'] = "Lista"
	ws['G1'] = "Estado"
	ws['H1'] = "Calidad"
	
	for fila in clics:
		ws.append(fila)
	
	ws = wb.create_sheet(title="Hard bounces")
	
	ws['A1'] = "Proyecto"
	ws['B1'] = "Lista"
	ws['C1'] = "Correo"
	ws['D1'] = "Lista"
	ws['E1'] = "Estado"
	ws['F1'] = "Calidad"
	
	for fila in hard_bounces:
		ws.append(fila)

	ws = wb.create_sheet(title="Soft bounces")

	ws['A1'] = "Proyecto"
	ws['B1'] = "Lista"
	ws['C1'] = "Correo"
	ws['D1'] = "Lista"
	ws['E1'] = "Estado"
	ws['F1'] = "Calidad"
	
	for fila in soft_bounces:
		ws.append(fila)

	# Guardar archivo
	ahora = datetime.now()
	fecha_texto = ahora.strftime("%Y%m%d%H%M")
	nombre_archivo = f"{ARCHIVO_INFORMES_PREFIX}_{fecha_texto}.xlsx"
	wb.save(nombre_archivo)
	notify("Proceso finalizado", f"Lista de suscriptores obtenida")
	return nombre_archivo


def main():
	# Config cargada en runtime y términos de búsqueda
	config = load_config()
	url = config.get("url", "")
	url_base = config.get("url_base", "")
	extraccion_oculta = bool(config.get("headless", False))

	terminos = cargar_terminos_busqueda(ARCHIVO_BUSQUEDA)
	
	if not terminos:
		print("No se encontraron términos de búsqueda marcados con 'x' o 'X'")
		return
	
	with sync_playwright() as p:
		browser = configurar_navegador(p, extraccion_oculta)
		context = crear_contexto_navegador(browser, extraccion_oculta)
		
		page = context.new_page()
		
		page.goto(url_base, wait_until="domcontentloaded", timeout=30000)
		page.goto(url, wait_until="domcontentloaded", timeout=60000)
		
		login(page)
		context.storage_state(path=storage_state_path())

		general: list[list[str]] = []
		abiertos: list[list[str]] = []
		no_abiertos = []
		clics = []
		hard_bounces = []
		soft_bounces = []
		
		buscador = page.get_by_placeholder("Buscar informe")
		
		for i, termino in enumerate(terminos):
			print(f"Procesando término {i+1}/{len(terminos)}: {termino[0]} - {termino[1]}")
			
			try:
				# Buscar y obtener datos de la campaña
				datos_campania = buscar_campania_por_termino(page, termino, buscador)
				general.append(datos_campania)

				# Obtener detalles de suscriptores
				listado_suscriptores = obtener_listado_suscriptores(
					page, 
					nombre_campania= datos_campania[0], 
					lista= datos_campania[3]
					)
				
				abiertos.extend(listado_suscriptores[0])
				no_abiertos.extend(listado_suscriptores[1])
				clics.extend(listado_suscriptores[2])
				hard_bounces.extend(listado_suscriptores[3])
				soft_bounces.extend(listado_suscriptores[4])
				
				# Procesar seguimiento de URLs
				# procesar_seguimiento_urls(page, detalles_suscriptores)
				
				# Volver a la página de reportes
				print("Haciendo clic para volver a la paginas de reportes")
				page.get_by_role('link', name='Emails').click()
			
			except Exception as e:
				print(f"Error procesando término '{termino[0]} - {termino[1]}': {e}")
				continue

		# Crear archivo Excel con los resultados
		if general or abiertos or no_abiertos or clics or hard_bounces or soft_bounces:
			crear_archivo_excel(general, [abiertos, no_abiertos, clics, hard_bounces, soft_bounces])
		else:
			print("No se procesaron datos, no se creó archivo Excel")
		
		browser.close()
if __name__ == "__main__":
	main()