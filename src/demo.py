from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page
from datetime import datetime

from .api.models.campanias import CampaignBasicInfo #, CampaignTotalInfo, CampaignClicks

from .api import API
from .autentificacion import login
from .utils import cargar_id_campanias_a_buscar, cargar_terminos_busqueda, crear_contexto_navegador, configurar_navegador, navegar_a_reportes, navegar_siguiente_pagina, obtener_total_paginas, load_config, data_path, storage_state_path, notify, get_timeouts, safe_goto, click_element
from .logger import get_logger, timer
from openpyxl import Workbook, load_workbook
import pandas as pd
import time
import os
import re

ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")
ARCHIVO_INFORMES_PREFIX = data_path("informes")

# REAL_UA = (
# 	"Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/537.36 "
# 	"(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
# )

# def buscar_campania_por_termino(page: Page, termino: list[str], buscador) -> list[str]:
# 	"""
# 	Busca una campaña específica por término y retorna sus datos
# 	"""

# 	try:
# 		timeouts = get_timeouts()
		
# 		navegar_a_reportes(page)
		
# 		# Realizar búsqueda
	
	
# 		try:
# 			buscador.fill("")
# 			buscador.fill(termino[0])
# 			page.keyboard.press("Enter")
	
	
# 		except Exception as e:
	
	
# 			raise
		
# 		# Esperar a que la página se cargue
	
# 		try:
# 			page.wait_for_load_state('networkidle', timeout=timeouts['page_load'])
	
	
# 		except Exception as e:
	
	
# 			raise
		
# 		# Localizar tabla de reportes
	
# 		try:
# 			tabla_reporte = page.locator('#newsletter-reports')
# 			# Esperar a que la tabla esté disponible
# 			tabla_reporte.locator('> li').first.wait_for(timeout=timeouts['tables'])
	
	
# 		except Exception as e:
	
	
# 			raise
		
# 		tds = tabla_reporte.locator('> li')
# 		cantidad_reportes = tds.count()
	
		
# 		divs = None
	
# 		for g in range(0, cantidad_reportes):
# 			try:
	
# 				td = tds.nth(g)
# 				div = td.locator('> div')
				
# 				# Verificar que el elemento existe antes de acceder al texto
# 				if div.first.count() == 0:
	
# 					continue
					
# 				nombre_txt = div.first.inner_text()
# 				if div.nth(3).count() == 0:
	
# 					continue
# 				listas = div.nth(3).inner_text()
				
	
				
# 				if(nombre_txt.strip() == termino[0] and listas.strip() == termino[1]):
# 					divs = td.locator('> div')
	
	
# 					break
# 			except Exception as e:
	
# 				continue
		
		
# 		if divs is None:
# 			raise Exception(f"No se encontró la campaña: {termino[0]} - {termino[1]}")
		
# 		# Extraer datos de la campaña
# 		campos = [divs.nth(i).inner_text() for i in range(7)]
	
		
# 		# Verificar que no estamos agregando una fila de encabezados como datos
# 		# Si el primer campo contiene "NOMBRE" o "Nombre", es probable que sea una fila de headers
# 		if campos and (campos[0].upper() == "NOMBRE" or campos[0] == "Nombre"):
	
# 			raise Exception(f"Se detectó una fila de encabezados en lugar de datos de campaña: {campos}")
		
# 		# Hacer clic en la campaña
	
# 		click_element(divs.locator('a').first)
		
# 		# Obtener URL del correo
# 		url_correo = page.get_by_role('link', name="Ver email")
# 		href_correo = url_correo.get_attribute('href') or ""
# 		campos.append(href_correo)
		
	
	
# 		return campos
		
# 	except Exception as e:
# 		raise

# def obtener_suscriptores_abrieron(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:
# 	suscriptores_abrieron = []
# 	paginas_totales = obtener_total_paginas(page)
# 	paginas_fallidas = 0

# 	for numero_pagina in range(1, paginas_totales + 1):

# 		try:
# 			# Espera mínima para que la tabla esté lista
# 			tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
			
# 			# Timeout ultra-agresivo: solo 1 segundo
# 			try:
# 				tabla_suscriptores.first.wait_for(timeout=1000)
# 			except:
# 				pass
			
# 			# OPTIMIZACIÓN CLAVE: Extraer todos los textos de una vez en lugar de uno por uno
# 			suscriptores = tabla_suscriptores.locator('> li')
# 			cantidad_suscriptores = suscriptores.count()
			
# 			# Extraer todos los datos de la página de una vez usando evaluate
# 			try:
# 				datos_pagina = page.evaluate("""
# 					() => {
# 						// Intentar múltiples selectores para encontrar la tabla
# 						let tabla = null;
						
# 						// Intento 1: Selector original
# 						tabla = document.querySelector('ul')?.querySelector('li[data-v-text="Correo electrónico"]')?.parentElement;
						
# 						// Intento 2: Buscar por texto "Correo electrónico"
# 						if (!tabla) {
# 							const elementos = document.querySelectorAll('li');
# 							for (const el of elementos) {
# 								if (el.textContent && el.textContent.includes('Correo electrónico')) {
# 									tabla = el.parentElement;
# 									break;
# 								}
# 							}
# 						}
						
# 						// Intento 3: Buscar UL que contenga múltiples LI con divs
# 						if (!tabla) {
# 							const uls = document.querySelectorAll('ul');
# 							for (const ul of uls) {
# 								const lis = ul.querySelectorAll('li');
# 								if (lis.length > 5) { // Más de 5 items, probablemente es la tabla
# 									const primerLi = lis[0];
# 									const divs = primerLi.querySelectorAll('div');
# 									if (divs.length >= 7) { // Al menos 7 columnas
# 										tabla = ul;
# 										break;
# 									}
# 								}
# 							}
# 						}
						
# 						if (!tabla) {
# 							console.log('No se encontró la tabla de suscriptores');
# 							return [];
# 						}
						
# 						const filas = Array.from(tabla.children).slice(1); // Skip header
# 						console.log('Filas encontradas:', filas.length);
						
# 						return filas.map(fila => {
# 							const divs = Array.from(fila.children);
# 							return divs.map(div => div.textContent?.trim() || '');
# 						}).filter(fila => fila.length >= 7);
# 					}
# 				""")
				
# 				suscriptores_en_pagina = 0
	
				
# 				for datos_fila in datos_pagina:
# 					if len(datos_fila) >= 7:
# 						correo, fecha_apertura, pais_apertura, aperturas, lista_suscriptor, estado, calidad = datos_fila[:7]
						
# 						# Verificar que no es una fila de encabezados
# 						if correo.upper() in ["CORREO", "EMAIL", "CORREO ELECTRÓNICO"]:
	
# 							continue
							
# 						suscriptores_abrieron.append([
# 							nombre_campania, lista, correo, fecha_apertura, pais_apertura, aperturas, lista_suscriptor, estado, calidad
# 						])
# 						suscriptores_en_pagina += 1
						
# 			except Exception:
# 				# Fallback al método anterior si falla la extracción batch
# 				suscriptores_en_pagina = 0
# 				for i in range(1, cantidad_suscriptores):
# 					try:
# 						datos_suscriptor = suscriptores.nth(i).locator('> div')
						
# 						# Extraer todos los inner_text de una vez
# 						textos = [datos_suscriptor.nth(j).inner_text() for j in range(7)]
# 						correo, fecha_apertura, pais_apertura, aperturas, lista_suscriptor, estado, calidad = textos
						
# 						suscriptores_abrieron.append([
# 							nombre_campania, lista, correo, fecha_apertura, pais_apertura, aperturas, lista_suscriptor, estado, calidad
# 						])
# 						suscriptores_en_pagina += 1
# 					except Exception:
# 						continue
			
	
	
			
# 		# Navegar a siguiente página si no es la última
# 			if numero_pagina < paginas_totales:
# 				if not navegar_siguiente_pagina(page, numero_pagina):
# 					paginas_fallidas += 1
# 					if paginas_fallidas >= 3:
	
# 						break
# 		except Exception as e:
	
	
# 			paginas_fallidas += 1
# 			if paginas_fallidas >= 3:
	
# 				break
# 			continue
	
	
	
	
	
	
# 	return suscriptores_abrieron

# def obtener_suscriptores_no_abrieron(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:
# 	"""Obtiene suscriptores que NO abrieron el email"""
	
	
	
# 	suscriptores_no_abrieron = []
# 	paginas_totales = obtener_total_paginas(page)
# 	paginas_fallidas = 0

# 	print(f"📄 Total de páginas detectado: {paginas_totales}")

# 	for numero_pagina in range(1, paginas_totales + 1):
	
# 		try:
# 			# Timeout ultra-agresivo para tabla
# 			tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
# 			try:
# 				tabla_suscriptores.first.wait_for(timeout=1000)  # Solo 1 segundo
# 			except:
# 				pass
			
# 			# OPTIMIZACIÓN: Extraer todos los datos usando evaluate (misma lógica que Abiertos)
# 			try:
# 				datos_pagina = page.evaluate("""
# 					() => {
# 						// Intentar múltiples selectores para encontrar la tabla
# 						let tabla = null;
						
# 						// Intento 1: Selector original
# 						tabla = document.querySelector('ul')?.querySelector('li[data-v-text="Correo electrónico"]')?.parentElement;
						
# 						// Intento 2: Buscar por texto "Correo electrónico"
# 						if (!tabla) {
# 							const elementos = document.querySelectorAll('li');
# 							for (const el of elementos) {
# 								if (el.textContent && el.textContent.includes('Correo electrónico')) {
# 									tabla = el.parentElement;
# 									break;
# 								}
# 							}
# 						}
						
# 						// Intento 3: Buscar UL que contenga múltiples LI con divs
# 						if (!tabla) {
# 							const uls = document.querySelectorAll('ul');
# 							for (const ul of uls) {
# 								const lis = ul.querySelectorAll('li');
# 								if (lis.length > 5) { // Más de 5 items, probablemente es la tabla
# 									const primerLi = lis[0];
# 									const divs = primerLi.querySelectorAll('div');
# 									if (divs.length >= 4) { // Al menos 4 columnas para No Abiertos
# 										tabla = ul;
# 										break;
# 									}
# 								}
# 							}
# 						}
						
# 						if (!tabla) {
# 							console.log('No se encontró la tabla de suscriptores No Abiertos');
# 							return [];
# 						}
						
# 						const filas = Array.from(tabla.children).slice(1); // Skip header
# 						console.log('Filas No Abiertos encontradas:', filas.length);
						
# 						return filas.map(fila => {
# 							const divs = Array.from(fila.children);
# 							return divs.map(div => div.textContent?.trim() || '');
# 						}).filter(fila => fila.length >= 4);
# 					}
# 				""")
				
# 				suscriptores_en_pagina = 0
	
				
# 				for datos_fila in datos_pagina:
# 					if len(datos_fila) >= 4:
# 						# Para No Abiertos, la estructura típica es: Correo, Lista, Estado, Calidad
# 						# Pero puede variar, así que tomamos el email del primer campo
# 						correo = datos_fila[0]
						
# 						# Verificar que no es una fila de encabezados
# 						if correo.upper() in ["CORREO", "EMAIL", "CORREO ELECTRÓNICO"]:
	
# 							continue
						
# 						# Extraer los últimos campos como lista, estado, calidad
# 						if len(datos_fila) >= 6:
# 							# Formato completo: más campos disponibles
# 							lista_suscriptor, estado, calidad = datos_fila[-3], datos_fila[-2], datos_fila[-1]
# 						else:
# 							# Formato simple: solo los básicos
# 							lista_suscriptor = datos_fila[1] if len(datos_fila) > 1 else ""
# 							estado = datos_fila[2] if len(datos_fila) > 2 else ""
# 							calidad = datos_fila[3] if len(datos_fila) > 3 else ""
						
# 						suscriptores_no_abrieron.append([
# 							nombre_campania, lista, correo, lista_suscriptor, estado, calidad
# 						])
# 						suscriptores_en_pagina += 1
						
# 			except Exception:
# 				# Fallback al método anterior si falla la extracción batch
# 				suscriptores = tabla_suscriptores.locator('> li')
# 				cantidad_suscriptores = suscriptores.count()
# 				suscriptores_en_pagina = 0
				
# 				for i in range(1, cantidad_suscriptores):
# 					try:
# 						datos_suscriptor = suscriptores.nth(i).locator('> div')
						
# 						# Extraer todos los inner_text de una vez
# 						textos = [datos_suscriptor.nth(j).inner_text() for j in range(4)]
# 						correo, lista_suscriptor, estado, calidad = textos
						
# 						suscriptores_no_abrieron.append([
# 							nombre_campania, lista, correo, lista_suscriptor, estado, calidad
# 						])
# 						suscriptores_en_pagina += 1
# 					except Exception:
# 						continue
			
	
	
			
# 			# Navegar a siguiente página si no es la última
# 			if numero_pagina < paginas_totales:
# 				if not navegar_siguiente_pagina(page, numero_pagina):
	
# 					break
					
# 		except Exception as e:
	
	
# 			paginas_fallidas += 1
# 			if paginas_fallidas >= 3:
	
# 				break
# 			continue
	
	
	
	
	
	
# 	return suscriptores_no_abrieron

# def obtener_suscriptores_hicieron_clic(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:
# 	suscriptores_abrieron = []
# 	paginas_totales = obtener_total_paginas(page)

# 	for numero_pagina in range(1, paginas_totales + 1):
# 		tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
# 		suscriptores = tabla_suscriptores.locator('> li')
# 		cantidad_suscriptores = suscriptores.count()
		
# 		for i in range(1, cantidad_suscriptores):  # empieza en 1 → segundo elemento
# 			datos_suscriptor = suscriptores.nth(i).locator('> div')
			
# 			correo = datos_suscriptor.nth(0).inner_text()
# 			fecha_apertura = datos_suscriptor.nth(1).inner_text()
# 			pais_apertura = datos_suscriptor.nth(2).inner_text()
# 			lista = datos_suscriptor.nth(3).inner_text()
# 			estado = datos_suscriptor.nth(4).inner_text()
# 			calidad = datos_suscriptor.nth(5).inner_text()
			
# 			suscriptores_abrieron.append([
# 				nombre_campania, lista, correo, fecha_apertura, pais_apertura, lista, estado, calidad
# 			])

# 		if numero_pagina < paginas_totales:
# 			if not navegar_siguiente_pagina(page, numero_pagina):
# 				break
# 	return suscriptores_abrieron

# def obtener_suscriptores_soft_bounces(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:
# 	suscriptores_abrieron = []
# 	paginas_totales = obtener_total_paginas(page)

# 	for numero_pagina in range(1, paginas_totales + 1):
# 		tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
# 		suscriptores = tabla_suscriptores.locator('> li')
# 		cantidad_suscriptores = suscriptores.count()
		
# 		for i in range(1, cantidad_suscriptores):  # empieza en 1 → segundo elemento
# 			datos_suscriptor = suscriptores.nth(i).locator('> div')
			
# 			correo = datos_suscriptor.nth(0).inner_text()
# 			lista = datos_suscriptor.nth(1).inner_text()
# 			estado = datos_suscriptor.nth(2).inner_text()
# 			calidad = datos_suscriptor.nth(3).inner_text()
			
# 			suscriptores_abrieron.append([
# 				nombre_campania, lista, correo, lista, estado, calidad
# 			])

# 		if numero_pagina < paginas_totales:
# 			if not navegar_siguiente_pagina(page, numero_pagina):
# 				break
# 	return suscriptores_abrieron

# def obtener_suscriptores_hard_bounces(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:	
# 	return obtener_suscriptores_soft_bounces(page, nombre_campania, lista)

# def extraer_metricas_campania(page: Page) -> dict:
# 	"""
# 	Extrae las métricas totales de la campaña desde el contenedor de estadísticas
# 	"""
# 	metricas = {
# 		'abiertos': 0,
# 		'no_abiertos': 0,
# 		'clics': 0,
# 		'hard_bounces': 0,
# 		'soft_bounces': 0
# 	}
	
# 	try:
# 		print("🔍 Extrayendo métricas totales de la campaña...")
		
# 		# Localizar el contenedor de estadísticas específico
# 		contenedor_stats = page.locator('div.box-shadow-1.border-radius-04.overflow-hidden.bg-color-white-1.margin-top-24')
		
# 		if contenedor_stats.count() == 0:
# 			print("❌ No se encontró el contenedor de estadísticas")
# 			return metricas
		
# 		# Buscar cada métrica por su enlace y texto
# 		elementos_li = contenedor_stats.locator('li').all()
# 		print(f"📊 Encontrados {len(elementos_li)} elementos de métricas")
		
# 		for i, elemento in enumerate(elementos_li):
# 			try:
# 				# Buscar el enlace con el texto de la métrica
# 				enlace_texto = elemento.locator('a').first
# 				if enlace_texto.count() == 0:
# 					continue
					
# 				texto_metrica = enlace_texto.inner_text().strip().lower()
				
# 				# Buscar el número (el segundo enlace con font-size-40)
# 				enlace_numero = elemento.locator('a.font-size-40.font-weight-300')
# 				if enlace_numero.count() == 0:
# 					continue
					
# 				numero_texto = enlace_numero.inner_text().strip()
				
# 				# Limpiar el número (quitar puntos de miles)
# 				numero_limpio = numero_texto.replace('.', '').replace(',', '')
				
# 				if not numero_limpio.isdigit():
# 					print(f"⚠️ Número no válido encontrado: '{numero_texto}' -> '{numero_limpio}'")
# 					continue
					
# 				numero = int(numero_limpio)
				
# 				# Asignar el número a la métrica correspondiente
# 				if 'abiertos' in texto_metrica and 'no' not in texto_metrica:
# 					metricas['abiertos'] = numero
# 					print(f"✅ Abiertos: {numero}")
# 				elif 'no abiertos' in texto_metrica:
# 					metricas['no_abiertos'] = numero
# 					print(f"✅ No abiertos: {numero}")
# 				elif 'clics' in texto_metrica:
# 					metricas['clics'] = numero
# 					print(f"✅ Clics: {numero}")
# 				elif 'hard bounces' in texto_metrica:
# 					metricas['hard_bounces'] = numero
# 					print(f"✅ Hard bounces: {numero}")
# 				elif 'soft bounces' in texto_metrica:
# 					metricas['soft_bounces'] = numero
# 					print(f"✅ Soft bounces: {numero}")
# 				else:
# 					print(f"📋 Métrica ignorada: {texto_metrica} = {numero}")
					
# 			except Exception as e:
# 				print(f"⚠️ Error procesando elemento {i}: {e}")
# 				continue
		
# 		print(f"📊 MÉTRICAS EXTRAÍDAS: {metricas}")
		
# 	except Exception as e:
# 		print(f"❌ Error extrayendo métricas: {e}")
	
# 	return metricas

# def obtener_listado_suscriptores(page: Page, nombre_campania: str, lista: str) -> list[list[list[str]]]:
# 	"""
# 	Obtiene los listado de todos los suscriptores de una campaña
# 	"""
# 	logger = get_logger()
# 	logger.start_timer("obtener_listado_suscriptores")
# 	logger.log_checkpoint("inicio_detalle_suscriptores", f"campaña: {nombre_campania}")
	
# 	try:
# 		logger.log_browser_action("Haciendo clic en Detalles suscriptores")
# 		click_element(page.get_by_role('link', name="Detalles suscriptores"))
# 		logger.log_checkpoint("click_detalles_done", "esperando carga")
		
# 		page.wait_for_load_state('networkidle')
# 		logger.log_checkpoint("pagina_cargada", "extrayendo métricas")

# 		# Extraer métricas totales ANTES de procesar los suscriptores
# 		logger.logger.info(f"\n🎯 === PROCESANDO CAMPAÑA: {nombre_campania} ===")
# 		metricas_totales = extraer_metricas_del_panel(page)
# 		logger.log_checkpoint("metricas_extraidas", f"métricas: {metricas_totales}")

# 		logger.log_browser_action("Localizando filtro de consulta")
# 		filtro = page.locator('select#query-filter')
# 		logger.log_checkpoint("filtro_localizado", "listo para procesar")

# 		logger.logger.info(f"📋 MÉTRICAS ESPERADAS: Abiertos: {metricas_totales['abiertos']:,}, No abiertos: {metricas_totales['no_abiertos']:,}, Clics: {metricas_totales['clics']:,}, Hard bounces: {metricas_totales['hard_bounces']:,}, Soft bounces: {metricas_totales['soft_bounces']:,}")

# 		abrieron = []
# 		no_abrieron = []
# 		clics = []
# 		hard_bounces = []
# 		soft_bounces = []

# 		# Procesar ABIERTOS
# 		if metricas_totales['abiertos'] > 0:
# 			try:
# 				print(f"\n🔍 Obteniendo suscriptores que ABRIERON (esperados: {metricas_totales['abiertos']:,})...")
# 				filtro.select_option(label="Abiertos")
# 				page.wait_for_load_state('networkidle')
# 				abrieron = obtener_suscriptores_abrieron(page, nombre_campania, lista) or []
# 				if len(abrieron) != metricas_totales['abiertos']:
# 					print(f"🚨 DISCREPANCIA ABIERTOS: Obtenidos {len(abrieron):,} vs Esperados {metricas_totales['abiertos']:,}")
# 			except Exception as e:
# 				print(f"❌ Error obteniendo suscriptores que abrieron: {e}")

# 		# Procesar NO ABIERTOS
# 		if metricas_totales['no_abiertos'] > 0:
# 			try:
# 				print(f"\n🔍 Obteniendo suscriptores que NO ABRIERON (esperados: {metricas_totales['no_abiertos']:,})...")
# 				filtro.select_option(label="No abiertos")
# 				page.wait_for_load_state('networkidle')
# 				no_abrieron = obtener_suscriptores_no_abrieron(page, nombre_campania, lista) or []
# 				print(f"✅ No abiertos obtenidos: {len(no_abrieron):,}")
				
# 				if len(no_abrieron) != metricas_totales['no_abiertos']:
# 					print(f"🚨 DISCREPANCIA NO ABIERTOS: Obtenidos {len(no_abrieron):,} vs Esperados {metricas_totales['no_abiertos']:,}")
# 			except Exception as e:
# 				print(f"❌ Error obteniendo suscriptores que no abrieron: {e}")

# 		# Procesar CLICS
# 		if metricas_totales['clics'] > 0:
# 			try:
# 				print(f"\n🔍 Obteniendo suscriptores que hicieron CLIC...")
# 				filtro.select_option(label="Clics")
# 				page.wait_for_load_state('networkidle')
# 				clics = obtener_suscriptores_hicieron_clic(page, nombre_campania, lista) or []
# 				print(f"✅ Clics obtenidos: {len(clics):,}")
# 			except Exception as e:
# 				print(f"❌ Error obteniendo suscriptores que hicieron clic: {e}")

# 		# Procesar HARD BOUNCES
# 		if metricas_totales['hard_bounces'] > 0:
# 			try:
# 				print(f"\n🔍 Obteniendo HARD BOUNCES...")
# 				filtro.select_option(label="Hard bounces")
# 				page.wait_for_load_state('networkidle')
# 				hard_bounces = obtener_suscriptores_hard_bounces(page, nombre_campania, lista) or []
# 				print(f"✅ Hard bounces obtenidos: {len(hard_bounces):,}")
# 			except Exception as e:
# 				print(f"❌ Error obteniendo hard bounces: {e}")

# 		# Procesar SOFT BOUNCES
# 		if metricas_totales['soft_bounces'] > 0:
# 			try:
# 				print(f"\n🔍 Obteniendo SOFT BOUNCES...")
# 				filtro.select_option(label="Soft bounces")
# 				page.wait_for_load_state('networkidle')
# 				soft_bounces = obtener_suscriptores_soft_bounces(page, nombre_campania, lista) or []
# 				print(f"✅ Soft bounces obtenidos: {len(soft_bounces):,}")
				
# 				if len(soft_bounces) != metricas_totales['soft_bounces']:
# 					print(f"🚨 DISCREPANCIA SOFT BOUNCES: Obtenidos {len(soft_bounces):,} vs Esperados {metricas_totales['soft_bounces']:,}")
# 			except Exception as e:
# 				print(f"❌ Error obteniendo soft bounces: {e}")

# 		# RESUMEN FINAL
# 		print(f"\n📊 === RESUMEN FINAL: {nombre_campania} ===")
# 		print(f"📈 Abiertos: {len(abrieron):,} / {metricas_totales['abiertos']:,}")
# 		print(f"📉 No abiertos: {len(no_abrieron):,} / {metricas_totales['no_abiertos']:,}")
# 		print(f"🖱️ Clics: {len(clics):,} / {metricas_totales['clics']:,}")
# 		print(f"💥 Hard bounces: {len(hard_bounces):,} / {metricas_totales['hard_bounces']:,}")
# 		print(f"⚠️ Soft bounces: {len(soft_bounces):,} / {metricas_totales['soft_bounces']:,}")

# 		total_obtenido = len(abrieron) + len(no_abrieron) + len(clics) + len(hard_bounces) + len(soft_bounces)
# 		total_esperado = sum(metricas_totales.values())
		
# 		if total_obtenido != total_esperado:
# 			print(f"🚨 DISCREPANCIA TOTAL: {total_obtenido:,} obtenidos vs {total_esperado:,} esperados")
# 		else:
# 			print(f"✅ TOTAL CORRECTO: {total_obtenido:,} suscriptores")

# 		# Cerrar timer y devolver resultados
# 		logger.end_timer("obtener_listado_suscriptores")
# 		return [abrieron, no_abrieron, clics, hard_bounces, soft_bounces]

# 	except Exception as e:
# 		# Manejo del try externo
# 		print(f"❌ Error general en obtener_listado_suscriptores: {e}")
# 		logger.log_error("obtener_listado_suscriptores", e)
# 		logger.end_timer("obtener_listado_suscriptores")
# 		raise

# def procesar_seguimiento_urls(page: Page, informe_detallado: list[list[str]]):
# 	"""
# 	Procesa el seguimiento de URLs y marca los clics en el informe detallado
# 	"""
# 	click_element(page.get_by_role('link', name="Seguimiento url's"))
# 	page.wait_for_load_state('networkidle')
	
# 	# Inicializar todos los registros con cadena vacía para seguimiento URL
# 	for detalle in informe_detallado:
# 		if len(detalle) < 9:
# 			detalle.append("")
	
# 	try:
# 		tabla_urls_seguimiento = page.locator('ul').filter(has=page.locator("span", has_text="Han hecho clic"))
# 		urls_seguimiento = tabla_urls_seguimiento.locator('> li')
# 		cantidad_url_seguimiento = urls_seguimiento.count()
		
# 		for z in range(1, cantidad_url_seguimiento):
# 			try:
# 				tabla_urls_seguimiento = page.locator('ul').filter(has=page.locator("span", has_text="Han hecho clic"))
# 				urls_seguimiento = tabla_urls_seguimiento.locator('> li')
				
# 				col_acciones = urls_seguimiento.nth(z).locator('> div')
# 				btn_menu = col_acciones.last.locator('a').first
# 				click_element(btn_menu)

# 				click_element(urls_seguimiento.nth(z).get_by_role('link', name="Detalles"))

# 				# vamos a recorrer cada pagina de clics de cada url de seguimiento
# 				paginas_totales = obtener_total_paginas(page)
				
# 				for numero_pagina in range(1, paginas_totales + 1):
# 					tabla_clics = page.locator('ul').filter(has=page.locator("span", has_text="Suscriptores que han hecho clic"))
# 					clics = tabla_clics.locator('> li')
# 					cantidad_clics = clics.count()
					
# 					for k in range(1, cantidad_clics):  # empieza en 1 → segundo elemento
# 						email = clics.nth(k).inner_text()
# 						for detalle in informe_detallado:
# 							if detalle[2].strip() == email.strip():
# 								# Marcar como "SI" si ya no está marcado
# 								if len(detalle) >= 10:
# 									detalle[9] = "SI"
# 								else:
# 									detalle.append("SI")
# 					# Navegar a siguiente página si no es la última
# 					if numero_pagina < paginas_totales:
# 						if not navegar_siguiente_pagina(page, numero_pagina):
# 							break
				
# 				page.go_back(wait_until='networkidle')
# 			except Exception as e:
# 				print(f"Error procesando seguimiento URL {z}: {e}")
# 				continue
# 	except Exception as e:
# 		print(f"Error general en seguimiento URLs: {e}")

def crear_archivo_excel(general: list[list[str]], informe_detallado: list[list[list[str]]], nombre_campania: str = "", fecha_envio: str = ""):
	"""
	Crea el archivo Excel con los informes recopilados
	"""

	try:
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
		
		# Filtrar filas de encabezados erróneas antes de escribir
		for fila in general:
			# Saltar filas que parecen ser encabezados (comienzan con "NOMBRE", "Nombre", etc.)
			if fila and len(fila) > 0 and (fila[0].upper() == "NOMBRE" or fila[0] == "Nombre" or 
				any(header.upper() in fila[0].upper() for header in ["TIPO", "FECHA ENV", "LISTAS", "EMAILS"])):
			
				continue
			ws.append(fila)
		
		# Crear hojas de detalles
		hojas_datos = [
			("Abiertos", abiertos, ["Proyecto", "Lista", "Correo", "Fecha apertura", "País apertura", "Aperturas", "Lista", "Estado", "Calidad"]),
			("No abiertos", no_abiertos, ["Proyecto", "Lista", "Correo", "Lista", "Estado", "Calidad"]),
			("Clics", clics, ["Proyecto", "Lista", "Correo", "Fecha primer clic", "País apertura", "Lista", "Estado", "Calidad"]),
			("Hard bounces", hard_bounces, ["Proyecto", "Lista", "Correo", "Lista", "Estado", "Calidad"]),
			("Soft bounces", soft_bounces, ["Proyecto", "Lista", "Correo", "Lista", "Estado", "Calidad"])
		]
		
		for nombre_hoja, datos, columnas in hojas_datos:
			ws = wb.create_sheet(title=nombre_hoja)
			
			# Escribir headers
			for col_idx, columna in enumerate(columnas, 1):
				ws.cell(row=1, column=col_idx, value=columna)
			
			# Escribir datos
			for fila in datos:
				ws.append(fila)

		# Guardar archivo con nuevo formato: (nombre campaña)-(fecha envio)_(fecha extraccion).xlsx
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
		
		wb.save(nombre_archivo)
		file_size = os.path.getsize(nombre_archivo)
		
		
		notify("Proceso finalizado", f"Lista de suscriptores obtenida")
		return nombre_archivo
		
	except Exception as e:
		
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

def main():
	try:
		# Config cargada en runtime y términos de búsqueda
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

				abiertos2: list[list[str]] = []

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

					abiertos2.append([proyecto, lista, correo, fecha_apertura, pais, aperturas, lista2, estado, calidad])
			
				# CLICS
				clics = []
				
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

				# SOFT BOUNCES
				soft_bounce_list = api.campaigns.get_soft_bounces(id)

				soft_bounces = []

				for bounce in soft_bounce_list:
				# // proyecto, lista, correo, lista, estado, calidad
					proyecto = campania.name or ""
					# lista = generar_listas(todas_listas, campania.lists or [])
					correo = bounce.email or ""
					lista2 = lista
					estado = "Activo"
					calidad = ""

					soft_bounces.append([proyecto, lista, correo, lista2, estado, calidad])
				
				# HARD BOUNCES
				hard_bounces = []

				url = f"https://acumbamail.com/report/campaign/{id}/"
				page.goto(url)

				link_detalle = page.get_by_role("link", name="Detalles suscriptores")
				link_detalle.click()

				page.wait_for_load_state("networkidle")

				select_filtro = page.locator("#query-filter")
				select_filtro.select_option(label="Hard bounces")

				paginas_totales = obtener_total_paginas(page)

				for numero_pagina in range(1, paginas_totales + 1):
					page.wait_for_load_state('networkidle')

					contenedor_tabla = page.locator("div").filter(has_text="Abiertos No abiertos Clics").nth(1)
					filas = contenedor_tabla.locator("> li")

					# obviar la primera fila, cabezeras
					for fila_i in range(1, filas.count()):
						campos = filas.nth(fila_i).locator("> div")
					
						email = campos.nth(0).inner_text()
						lista = campos.nth(1).inner_text()
						estado = campos.nth(2).inner_text()
						calidad = campos.nth(3).inner_text()

						hard_bounces.append([campania.name or "", lista, email, lista, estado, calidad])
					if numero_pagina < paginas_totales:
							if not navegar_siguiente_pagina(page, numero_pagina):
									break
				# NO ABIERTOS
				no_abiertos = []

				select_filtro = page.locator("#query-filter")
				select_filtro.select_option(label="No abiertos")

				page.wait_for_load_state('networkidle')

				paginas_totales = obtener_total_paginas(page)

				for numero_pagina in range(1, paginas_totales + 1):
					page.wait_for_load_state('networkidle')

					contenedor_tabla = page.locator("div").filter(has_text="Abiertos No abiertos Clics").nth(1)
					filas = contenedor_tabla.locator("> li")

					for fila_i in range(1, filas.count()):
						campos = filas.nth(fila_i).locator("> div")
					
						email = campos.nth(0).inner_text()
						lista = campos.nth(1).inner_text()
						estado = campos.nth(2).inner_text()
						calidad = campos.nth(3).inner_text()

						no_abiertos.append([campania.name or "", lista, email, lista, estado, calidad])
					if numero_pagina < paginas_totales:
						if not navegar_siguiente_pagina(page, numero_pagina):
								break

			# Crear archivo Excel con los resultados
				if general or abiertos2 or no_abiertos or clics or hard_bounces or soft_bounces:
					# Extraer nombre de campaña y fecha de envío del primer elemento procesado
					nombre_campania_param = ""
					fecha_envio_param = ""
					
					if general and len(general) > 0 and len(general[0]) >= 3:
						nombre_campania_param = general[0][0]  # Primer campo: nombre de campaña
						fecha_envio_raw = general[0][2]  # Tercer campo: fecha de envío
						
						# Convertir fecha de envío a formato YYYYMMDDHHMM
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
									fecha_envio_dt = datetime.strptime(fecha_envio_raw, fmt)
									break
								except ValueError:
									continue
							
							if fecha_envio_dt:
								fecha_envio_param = fecha_envio_dt.strftime("%Y%m%d")
							else:
								# Si no se puede parsear, usar el texto directamente limpiando caracteres problemáticos
								fecha_envio_param = re.sub(r'[<>:"/\\|?*\s]', '', fecha_envio_raw)
						except Exception as e:
							fecha_envio_param = re.sub(r'[<>:"/\\|?*\s]', '', fecha_envio_raw)
					
					archivo_creado = crear_archivo_excel(general, [abiertos2, no_abiertos, clics, hard_bounces, soft_bounces], nombre_campania_param, fecha_envio_param)
				browser.close()
				
				
	
	except Exception as e:
		print(f"❌ Error en proceso principal: {e}")
		notify("Error en proceso", str(e))
		
if __name__ == "__main__":
	main()