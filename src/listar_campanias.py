from playwright.sync_api import sync_playwright, Page
from datetime import datetime
from .utils import configurar_navegador, crear_contexto_navegador, obtener_total_paginas, navegar_siguiente_pagina, load_config, data_path, storage_state_path, notify, get_timeouts, safe_goto, safe_wait_for_element
from .autentificacion import login
import pandas as pd
from openpyxl import Workbook, load_workbook
import os
import re

# Rutas
ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")

def cargar_ultimo_termino_busqueda(archivo_busqueda: str) -> list[str]:
	"""
	Carga el último término de búsqueda desde el archivo Excel
	"""
	try:
		df = pd.read_excel(archivo_busqueda, engine="openpyxl")
		terminos = ["", ""]

		# Solo si hay filas y existen las columnas esperadas, extrae la última
		if not df.empty and {'Nombre', 'Listas'}.issubset(df.columns):
			ultima_fila = df.iloc[-1]
			terminos = [str(ultima_fila.get('Nombre', '')).strip(),
						str(ultima_fila.get('Listas', '')).strip()]
		
		return terminos
	except Exception as e:
		print(f"Error al cargar términos de búsqueda: {e}")
		return ["", ""]

def inicializar_navegacion_reportes(page: Page):
	"""
	Navega a la sección de reportes y espera a que cargue
	"""
	timeouts = get_timeouts()
    
	# Evitar depender de 'networkidle' (puede no llegar en SPAs); en su lugar, esperar al contenedor de reportes
	try:
		page.click("a[href*='/reports']")
	except Exception as e:
		print(f"⚠️ No se pudo hacer clic en el enlace de reportes: {e}")

	# Esperar elemento concreto de la lista de reportes o un fallback visible
	try:
		lista_reportes = page.locator('#newsletter-reports')
		safe_wait_for_element(lista_reportes, 'tables')
		# además, comprobar que tiene al menos un ítem cargado
		lista_reportes.locator('> li').first.wait_for(timeout=timeouts['elements'])
	except Exception as e:
		print(f"⚠️ Advertencia al cargar reportes (fallback): {e}")
		# Fallback: esperar un título/heading relacionado si existe para no colgarse
		try:
			heading = page.locator('h1, h2, h3, h4').filter(has_text=re.compile(r"(?i)(reporte|report)"))
			heading.first.wait_for(timeout=timeouts['elements'])
		except Exception:
			pass

def extraer_datos_campania(td_element, indice: int) -> list[str]:
	"""
	Extrae los datos de una campaña específica del elemento TD
	"""
	try:
		divs = td_element.locator('> div')
		
		nombre = divs.nth(0)
		nombre_txt = nombre.nth(0).inner_text()
		tipo = divs.nth(1).inner_text()
		fecha_envio = divs.nth(2).inner_text()
		listas = divs.nth(3).inner_text()
		emails = divs.nth(4).inner_text()
		abiertos = divs.nth(5).inner_text()
		clics = divs.nth(6).inner_text()
		
		# Verificar si es una fila de encabezados
		if (nombre_txt.upper() in ["NOMBRE", "NAME"] or 
		    tipo.upper() in ["TIPO", "TYPE"] or
		    fecha_envio.upper() in ["FECHA ENVIO", "FECHA ENV", "DATE"] or
		    listas.upper() in ["LISTAS", "LISTS"] or
		    emails.upper() in ["EMAILS", "EMAIL"] or
		    abiertos.upper() in ["ABIERTOS", "OPENS", "OPENED"] or
		    clics.upper() in ["CLICS", "CLICKS"]):
			print(f"⚠️ Saltando fila de encabezados: {nombre_txt}, {tipo}, {fecha_envio}")
			return []  # Retornar lista vacía para indicar que se debe saltar
		
		return ['', nombre_txt, tipo, fecha_envio, listas, emails, abiertos, clics]
	except Exception:
		return ['', '', '', '', '', '', '', '']

def buscar_campanias_en_pagina(page: Page, terminos: list[str], numero_pagina: int) -> tuple[list[list[str]], bool]:
	"""
	Busca campañas en la página actual y retorna los datos y si encontró el término buscado
	"""
	informe_detalle = []
	encontrado = False
	buscar_todo = not terminos[0] or not terminos[1]  # Si no hay términos, buscar todo
	timeouts = get_timeouts()
	
	# Si la página fue cerrada (por el usuario o por error), salir temprano
	if getattr(page, 'is_closed', None) and page.is_closed():
		return [], False

	try:
		tabla_reporte = page.locator('#newsletter-reports')
		# Esperar a que al menos un elemento esté presente sin depender de networkidle
		tabla_reporte.locator('> li').first.wait_for(timeout=timeouts['tables'])

		tds = tabla_reporte.locator('> li')
		total = tds.count()
		# Detectar si el primer li es cabecera (heurística: tiene menos de 7 divs esperados)
		start_index = 0
		try:
			primer_divs = tds.nth(0).locator('> div').count()
			if primer_divs < 7:
				start_index = 1
		except Exception:
			pass
		page_items = max(total - start_index, 0)
		print(f"Encontrados {page_items} elementos de campaña en la página {numero_pagina}")
		
		for o in range(start_index, total):
			datos_campania = extraer_datos_campania(tds.nth(o), o)
			
			# Si la función retorna lista vacía, significa que es una fila de encabezados, saltar
			if not datos_campania:
				continue
			
			if datos_campania[1]:  # Si tiene nombre
				nombre_txt = datos_campania[1]
				listas = datos_campania[4]
				fecha_envio = datos_campania[3]
				
				# Si estamos buscando todo, agregar todas las campañas
				if buscar_todo:
					informe_detalle = [datos_campania] + informe_detalle
				else:
					# Verificar si es la campaña buscada específica
					if nombre_txt.strip() == terminos[0] and listas.strip() == terminos[1]:
						encontrado = True
						break
					
					# Agregar al inicio para mantener orden cronológico inverso
					informe_detalle = [datos_campania] + informe_detalle
		
	except Exception as e:
		# Mensaje más claro si la página/contexto fue cerrada
		try:
			cerrada = (getattr(page, 'is_closed', None) and page.is_closed())
		except Exception:
			cerrada = False
		if cerrada:
			print(f"Error procesando página {numero_pagina}: la página fue cerrada")
		else:
			print(f"Error procesando página {numero_pagina}: {e}")
	
	return informe_detalle, encontrado

def guardar_datos_en_excel(informe_detalle: list[list[str]], archivo_busqueda: str):
	"""
	Guarda los datos en el archivo Excel
	"""
	try:
		try:
			wb = load_workbook(archivo_busqueda)
			ws = wb.active
		except FileNotFoundError:
			wb = Workbook()
			ws = wb.active
			if ws is None:
				ws = wb.create_sheet(title="Campanias")
			ws.append(["Buscar", "Nombre", "Tipo", "Fecha envio", "Listas", "Emails", "Abiertos", "Clics"])

		# Agregar datos al final
		registros_agregados = 0
		for fila in informe_detalle:
			if ws is not None and any(fila) and len(fila) >= 8:  # Solo agregar filas con datos válidos
				# Verificación adicional: asegurar que no es una fila de headers
				nombre = fila[1] if len(fila) > 1 else ""
				tipo = fila[2] if len(fila) > 2 else ""
				
				if (nombre.upper() not in ["NOMBRE", "NAME"] and 
				    tipo.upper() not in ["TIPO", "TYPE"]):
					ws.append(fila)
					registros_agregados += 1
				else:
					print(f"⚠️ Fila de encabezados filtrada en guardado: {nombre}, {tipo}")
		
		wb.save(archivo_busqueda)
		
	except Exception as e:
		print(f"Error guardando archivo Excel: {e}")

def procesar_busqueda_campanias(page: Page, terminos: list[str]) -> list[list[str]]:
	"""
	Función principal que coordina la búsqueda de campañas
	"""
	informe_detalle = []
	buscar_todo = not terminos[0] or not terminos[1]  # Si no hay términos, buscar todo
	
	# Inicializar navegación a reportes
	inicializar_navegacion_reportes(page)
	
	# Obtener total de páginas
	paginas_totales = obtener_total_paginas(page)
	print(f"Total de páginas de reportes: {paginas_totales}")
	encontrado = False
	campanias_totales = 0
	
	# Buscar en todas las páginas
	for numero_pagina in range(1, paginas_totales + 1):
	# for numero_pagina in range(1, 2 + 1):
		print(f"Procesando página {numero_pagina} de {paginas_totales}...")
		datos_pagina, encontrado = buscar_campanias_en_pagina(page, terminos, numero_pagina)
		
		# Mantener orden cronológico: nuevos datos al inicio
		informe_detalle = datos_pagina + informe_detalle
		campanias_totales += len(datos_pagina)
		print(f"Página {numero_pagina}: añadidas {len(datos_pagina)} campañas (acumulado: {campanias_totales})")
		
		# Si estamos buscando una campaña específica y la encontramos, parar
		if not buscar_todo and encontrado:
			print(f"Búsqueda detenida: se encontró la última campaña registrada ('{terminos[0]}')")
			break
		
		# Navegar a siguiente página si no es la última
		if numero_pagina < paginas_totales:
			if not navegar_siguiente_pagina(page, numero_pagina):
				break
	
	if buscar_todo:
		print(f"Total de campañas recopiladas: {campanias_totales}")
	else:
		print(f"Total de campañas añadidas: {campanias_totales}")
	
	return informe_detalle

def main():
	"""
	Función principal del programa de listado de campañas
	"""
	# Cargar config fresca y términos de búsqueda
	config = load_config()
	url = config.get("url", "")
	url_base = config.get("url_base", "")

	terminos = cargar_ultimo_termino_busqueda(ARCHIVO_BUSQUEDA)
	
	# Si no hay términos válidos, buscar todas las campañas
	if not terminos[0] or not terminos[1]:
		terminos = ["", ""]  # Términos vacíos para buscar todo
	
	try:
		with sync_playwright() as p:
			browser = configurar_navegador(p, extraccion_oculta=False)
			context = crear_contexto_navegador(browser)
			
			page = context.new_page()
			
			safe_goto(page, url_base, "domcontentloaded")
			safe_goto(page, url, "domcontentloaded")
			
			# Realizar login
			login(page)
			context.storage_state(path=storage_state_path())

			# Procesar búsqueda de campañas
			informe_detalle = procesar_busqueda_campanias(page, terminos)

			# Guardar resultados
			if informe_detalle:
				guardar_datos_en_excel(informe_detalle, ARCHIVO_BUSQUEDA)
			
			browser.close()
			notify("Proceso finalizado", f"Lista de campañas obtenida")
			
	except Exception as e:
		print(f"Error crítico en el programa: {e}")
		raise

if __name__ == "__main__":
	main()