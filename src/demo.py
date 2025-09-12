from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page
from datetime import datetime
from .autentificacion import login
from .utils import cargar_terminos_busqueda, crear_contexto_navegador, configurar_navegador, navegar_a_reportes, navegar_siguiente_pagina, obtener_total_paginas, load_config, data_path, storage_state_path, notify, get_timeouts, safe_goto, click_element
from .logger import get_logger, timer
from openpyxl import Workbook, load_workbook
import pandas as pd
import time
import os
import re

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
	logger = get_logger()
	logger.start_timer("buscar_campania")
	logger.log_browser_action("Buscando campaña", f"término: {termino[0]} - {termino[1]}")
	
	try:
		timeouts = get_timeouts()
		
		navegar_a_reportes(page)
		
		# Realizar búsqueda
		logger.log_browser_action("Realizando búsqueda", f"término: {termino[0]}")
		logger.start_timer("realizar_busqueda")
		try:
			buscador.fill("")
			buscador.fill(termino[0])
			page.keyboard.press("Enter")
			logger.end_timer("realizar_busqueda")
			logger.log_success("realizar_busqueda", "Búsqueda enviada")
		except Exception as e:
			logger.log_error("realizar_busqueda", e, f"término: {termino[0]}")
			logger.end_timer("realizar_busqueda")
			raise
		
		# Esperar a que la página se cargue
		logger.start_timer("esperar_resultados")
		try:
			page.wait_for_load_state('networkidle', timeout=timeouts['page_load'])
			logger.end_timer("esperar_resultados")
			logger.log_success("esperar_resultados", "Página cargada")
		except Exception as e:
			logger.log_error("esperar_resultados", e, "Timeout esperando resultados")
			logger.end_timer("esperar_resultados")
			raise
		
		# Localizar tabla de reportes
		logger.start_timer("localizar_tabla")
		try:
			tabla_reporte = page.locator('#newsletter-reports')
			# Esperar a que la tabla esté disponible
			tabla_reporte.locator('> li').first.wait_for(timeout=timeouts['tables'])
			logger.end_timer("localizar_tabla")
			logger.log_success("localizar_tabla", "Tabla de reportes localizada")
		except Exception as e:
			logger.log_error("localizar_tabla", e, "No se pudo localizar la tabla de reportes")
			logger.end_timer("localizar_tabla")
			raise
		
		tds = tabla_reporte.locator('> li')
		cantidad_reportes = tds.count()
		logger.log_data_extraction("reportes", cantidad_reportes, "tabla de reportes")
		
		divs = None
		logger.start_timer("buscar_en_resultados")
		for g in range(0, cantidad_reportes):
			try:
				logger.log_browser_action("Procesando resultado", f"{g+1}/{cantidad_reportes}")
				td = tds.nth(g)
				div = td.locator('> div')
				
				# Verificar que el elemento existe antes de acceder al texto
				if div.first.count() == 0:
					logger.log_warning("buscar_campania", f"Elemento {g} vacío, saltando")
					continue
					
				nombre_txt = div.first.inner_text()
				if div.nth(3).count() == 0:
					logger.log_warning("buscar_campania", f"Elemento {g} sin listas, saltando")
					continue
				listas = div.nth(3).inner_text()
				
				logger.log_browser_action("Comparando", f"'{nombre_txt.strip()}' vs '{termino[0]}' y '{listas.strip()}' vs '{termino[1]}'")
				
				if(nombre_txt.strip() == termino[0] and listas.strip() == termino[1]):
					divs = td.locator('> div')
					logger.end_timer("buscar_en_resultados")
					logger.log_success("buscar_campania", f"Campaña encontrada: {nombre_txt}")
					break
			except Exception as e:
				logger.log_warning("buscar_campania", f"Error procesando elemento {g}: {e}")
				continue
		
		if divs is None:
			logger.end_timer("buscar_en_resultados")
		else:
			logger.log_success("buscar_en_resultados", "Búsqueda completada")
		
		if divs is None:
			logger.log_error("buscar_campania", Exception("Campaña no encontrada"), f"{termino[0]} - {termino[1]}")
			raise Exception(f"No se encontró la campaña: {termino[0]} - {termino[1]}")
		
		# Extraer datos de la campaña
		campos = [divs.nth(i).inner_text() for i in range(7)]
		logger.log_data_extraction("campos_campania", len(campos), "divs de campaña")
		
		# Verificar que no estamos agregando una fila de encabezados como datos
		# Si el primer campo contiene "NOMBRE" o "Nombre", es probable que sea una fila de headers
		if campos and (campos[0].upper() == "NOMBRE" or campos[0] == "Nombre"):
			logger.log_warning("buscar_campania", f"Detectada fila de encabezados, saltando: {campos}")
			raise Exception(f"Se detectó una fila de encabezados en lugar de datos de campaña: {campos}")
		
		# Hacer clic en la campaña
		logger.log_browser_action("Haciendo clic en campaña")
		click_element(divs.locator('a').first)
		
		# Obtener URL del correo
		url_correo = page.get_by_role('link', name="Ver email")
		href_correo = url_correo.get_attribute('href') or ""
		campos.append(href_correo)
		
		logger.end_timer("buscar_campania")
		logger.log_success("buscar_campania", f"Datos extraídos: {len(campos)} campos")
		return campos
		
	except Exception as e:
		logger.log_error("buscar_campania", e, f"término: {termino[0]} - {termino[1]}")
		logger.end_timer("buscar_campania")
		raise

def obtener_suscriptores_abrieron(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:
	logger = get_logger()
	logger.start_timer("obtener_suscriptores_abrieron")
	logger.log_browser_action("Obteniendo suscriptores que abrieron", f"campaña: {nombre_campania}")
	
	suscriptores_abrieron = []
	paginas_totales = obtener_total_paginas(page)
	paginas_fallidas = 0

	logger.logger.info(f"📄 Total de páginas detectado: {paginas_totales}")

	for numero_pagina in range(1, paginas_totales + 1):
		logger.start_timer(f"procesar_pagina_abiertos_{numero_pagina}")
		try:
			# Espera mínima para que la tabla esté lista
			tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
			
			# Timeout ultra-agresivo: solo 1 segundo
			try:
				tabla_suscriptores.first.wait_for(timeout=1000)
			except:
				pass
			
			# OPTIMIZACIÓN CLAVE: Extraer todos los textos de una vez en lugar de uno por uno
			suscriptores = tabla_suscriptores.locator('> li')
			cantidad_suscriptores = suscriptores.count()
			
			# Extraer todos los datos de la página de una vez usando evaluate
			try:
				datos_pagina = page.evaluate("""
					() => {
						// Intentar múltiples selectores para encontrar la tabla
						let tabla = null;
						
						// Intento 1: Selector original
						tabla = document.querySelector('ul')?.querySelector('li[data-v-text="Correo electrónico"]')?.parentElement;
						
						// Intento 2: Buscar por texto "Correo electrónico"
						if (!tabla) {
							const elementos = document.querySelectorAll('li');
							for (const el of elementos) {
								if (el.textContent && el.textContent.includes('Correo electrónico')) {
									tabla = el.parentElement;
									break;
								}
							}
						}
						
						// Intento 3: Buscar UL que contenga múltiples LI con divs
						if (!tabla) {
							const uls = document.querySelectorAll('ul');
							for (const ul of uls) {
								const lis = ul.querySelectorAll('li');
								if (lis.length > 5) { // Más de 5 items, probablemente es la tabla
									const primerLi = lis[0];
									const divs = primerLi.querySelectorAll('div');
									if (divs.length >= 7) { // Al menos 7 columnas
										tabla = ul;
										break;
									}
								}
							}
						}
						
						if (!tabla) {
							console.log('No se encontró la tabla de suscriptores');
							return [];
						}
						
						const filas = Array.from(tabla.children).slice(1); // Skip header
						console.log('Filas encontradas:', filas.length);
						
						return filas.map(fila => {
							const divs = Array.from(fila.children);
							return divs.map(div => div.textContent?.trim() || '');
						}).filter(fila => fila.length >= 7);
					}
				""")
				
				suscriptores_en_pagina = 0
				logger.logger.info(f"📊 JavaScript extrajo {len(datos_pagina)} filas de datos")
				
				for datos_fila in datos_pagina:
					if len(datos_fila) >= 7:
						correo, fecha_apertura, pais_apertura, aperturas, lista_suscriptor, estado, calidad = datos_fila[:7]
						
						# Verificar que no es una fila de encabezados
						if correo.upper() in ["CORREO", "EMAIL", "CORREO ELECTRÓNICO"]:
							logger.logger.info(f"⚠️ Saltando fila de encabezados: {correo}")
							continue
							
						suscriptores_abrieron.append([
							nombre_campania, lista, correo, fecha_apertura, pais_apertura, aperturas, lista_suscriptor, estado, calidad
						])
						suscriptores_en_pagina += 1
						
			except Exception:
				# Fallback al método anterior si falla la extracción batch
				suscriptores_en_pagina = 0
				for i in range(1, cantidad_suscriptores):
					try:
						datos_suscriptor = suscriptores.nth(i).locator('> div')
						
						# Extraer todos los inner_text de una vez
						textos = [datos_suscriptor.nth(j).inner_text() for j in range(7)]
						correo, fecha_apertura, pais_apertura, aperturas, lista_suscriptor, estado, calidad = textos
						
						suscriptores_abrieron.append([
							nombre_campania, lista, correo, fecha_apertura, pais_apertura, aperturas, lista_suscriptor, estado, calidad
						])
						suscriptores_en_pagina += 1
					except Exception:
						continue
			
			logger.end_timer(f"procesar_pagina_abiertos_{numero_pagina}")
			logger.log_data_extraction("suscriptores_abiertos", suscriptores_en_pagina, f"página {numero_pagina}")
			
			# Mostrar progreso cada 100 suscriptores
			if len(suscriptores_abrieron) % 100 == 0 and len(suscriptores_abrieron) > 0:
				logger.log_progress(len(suscriptores_abrieron), 0, "suscriptores abiertos obtenidos")

			# Navegar a siguiente página si no es la última
			if numero_pagina < paginas_totales:
				if not navegar_siguiente_pagina(page, numero_pagina):
					paginas_fallidas += 1
					if paginas_fallidas >= 3:
						logger.log_error("obtener_suscriptores_abrieron", Exception("Demasiadas páginas fallidas"), f"fallos: {paginas_fallidas}")
						break
		except Exception as e:
			logger.log_error("obtener_suscriptores_abrieron", e, f"página {numero_pagina}")
			logger.end_timer(f"procesar_pagina_abiertos_{numero_pagina}")
			paginas_fallidas += 1
			if paginas_fallidas >= 3:
				logger.log_error("obtener_suscriptores_abrieron", Exception("Demasiadas páginas fallidas"), f"fallos: {paginas_fallidas}")
				break
			continue
	
	logger.end_timer("obtener_suscriptores_abrieron")
	logger.log_success("obtener_suscriptores_abrieron", f"Total obtenidos: {len(suscriptores_abrieron)}")
	if paginas_fallidas > 0:
		logger.log_warning("obtener_suscriptores_abrieron", f"Se produjeron {paginas_fallidas} fallos de páginas")
	
	return suscriptores_abrieron

def obtener_suscriptores_no_abrieron(page: Page, nombre_campania: str, lista: str) -> list[list[str]]:
	"""Obtiene suscriptores que NO abrieron el email"""
	logger = get_logger()
	logger.start_timer("obtener_suscriptores_no_abrieron")
	
	suscriptores_no_abrieron = []
	paginas_totales = obtener_total_paginas(page)
	paginas_fallidas = 0

	print(f"📄 Total de páginas detectado: {paginas_totales}")

	for numero_pagina in range(1, paginas_totales + 1):
		logger.start_timer(f"procesar_pagina_no_abiertos_{numero_pagina}")
		try:
			# Timeout ultra-agresivo para tabla
			tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
			try:
				tabla_suscriptores.first.wait_for(timeout=1000)  # Solo 1 segundo
			except:
				pass
			
			# OPTIMIZACIÓN: Extraer todos los datos usando evaluate (misma lógica que Abiertos)
			try:
				datos_pagina = page.evaluate("""
					() => {
						// Intentar múltiples selectores para encontrar la tabla
						let tabla = null;
						
						// Intento 1: Selector original
						tabla = document.querySelector('ul')?.querySelector('li[data-v-text="Correo electrónico"]')?.parentElement;
						
						// Intento 2: Buscar por texto "Correo electrónico"
						if (!tabla) {
							const elementos = document.querySelectorAll('li');
							for (const el of elementos) {
								if (el.textContent && el.textContent.includes('Correo electrónico')) {
									tabla = el.parentElement;
									break;
								}
							}
						}
						
						// Intento 3: Buscar UL que contenga múltiples LI con divs
						if (!tabla) {
							const uls = document.querySelectorAll('ul');
							for (const ul of uls) {
								const lis = ul.querySelectorAll('li');
								if (lis.length > 5) { // Más de 5 items, probablemente es la tabla
									const primerLi = lis[0];
									const divs = primerLi.querySelectorAll('div');
									if (divs.length >= 4) { // Al menos 4 columnas para No Abiertos
										tabla = ul;
										break;
									}
								}
							}
						}
						
						if (!tabla) {
							console.log('No se encontró la tabla de suscriptores No Abiertos');
							return [];
						}
						
						const filas = Array.from(tabla.children).slice(1); // Skip header
						console.log('Filas No Abiertos encontradas:', filas.length);
						
						return filas.map(fila => {
							const divs = Array.from(fila.children);
							return divs.map(div => div.textContent?.trim() || '');
						}).filter(fila => fila.length >= 4);
					}
				""")
				
				suscriptores_en_pagina = 0
				logger.logger.info(f"📊 JavaScript extrajo {len(datos_pagina)} filas de No Abiertos")
				
				for datos_fila in datos_pagina:
					if len(datos_fila) >= 4:
						# Para No Abiertos, la estructura típica es: Correo, Lista, Estado, Calidad
						# Pero puede variar, así que tomamos el email del primer campo
						correo = datos_fila[0]
						
						# Verificar que no es una fila de encabezados
						if correo.upper() in ["CORREO", "EMAIL", "CORREO ELECTRÓNICO"]:
							logger.logger.info(f"⚠️ Saltando fila de encabezados No Abiertos: {correo}")
							continue
						
						# Extraer los últimos campos como lista, estado, calidad
						if len(datos_fila) >= 6:
							# Formato completo: más campos disponibles
							lista_suscriptor, estado, calidad = datos_fila[-3], datos_fila[-2], datos_fila[-1]
						else:
							# Formato simple: solo los básicos
							lista_suscriptor = datos_fila[1] if len(datos_fila) > 1 else ""
							estado = datos_fila[2] if len(datos_fila) > 2 else ""
							calidad = datos_fila[3] if len(datos_fila) > 3 else ""
						
						suscriptores_no_abrieron.append([
							nombre_campania, lista, correo, lista_suscriptor, estado, calidad
						])
						suscriptores_en_pagina += 1
						
			except Exception:
				# Fallback al método anterior si falla la extracción batch
				suscriptores = tabla_suscriptores.locator('> li')
				cantidad_suscriptores = suscriptores.count()
				suscriptores_en_pagina = 0
				
				for i in range(1, cantidad_suscriptores):
					try:
						datos_suscriptor = suscriptores.nth(i).locator('> div')
						
						# Extraer todos los inner_text de una vez
						textos = [datos_suscriptor.nth(j).inner_text() for j in range(4)]
						correo, lista_suscriptor, estado, calidad = textos
						
						suscriptores_no_abrieron.append([
							nombre_campania, lista, correo, lista_suscriptor, estado, calidad
						])
						suscriptores_en_pagina += 1
					except Exception:
						continue
			
			logger.log_progress(numero_pagina, paginas_totales, f"Página {numero_pagina}: {suscriptores_en_pagina} no abiertos")
			logger.end_timer(f"procesar_pagina_no_abiertos_{numero_pagina}")
			
			# Navegar a siguiente página si no es la última
			if numero_pagina < paginas_totales:
				if not navegar_siguiente_pagina(page, numero_pagina):
					logger.log_warning("obtener_suscriptores_no_abrieron", f"No se pudo navegar a la página {numero_pagina + 1}")
					break
					
		except Exception as e:
			logger.log_error("obtener_suscriptores_no_abrieron", e, f"página {numero_pagina}")
			logger.end_timer(f"procesar_pagina_no_abiertos_{numero_pagina}")
			paginas_fallidas += 1
			if paginas_fallidas >= 3:
				logger.log_error("obtener_suscriptores_no_abrieron", Exception("Demasiadas páginas fallidas"), f"fallos: {paginas_fallidas}")
				break
			continue
	
	logger.end_timer("obtener_suscriptores_no_abrieron")
	logger.log_success("obtener_suscriptores_no_abrieron", f"Total obtenidos: {len(suscriptores_no_abrieron)}")
	if paginas_fallidas > 0:
		logger.log_warning("obtener_suscriptores_no_abrieron", f"Se produjeron {paginas_fallidas} fallos de páginas")
	
	return suscriptores_no_abrieron

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

def extraer_metricas_campania(page: Page) -> dict:
	"""
	Extrae las métricas totales de la campaña desde el contenedor de estadísticas
	"""
	metricas = {
		'abiertos': 0,
		'no_abiertos': 0,
		'clics': 0,
		'hard_bounces': 0,
		'soft_bounces': 0
	}
	
	try:
		print("🔍 Extrayendo métricas totales de la campaña...")
		
		# Localizar el contenedor de estadísticas específico
		contenedor_stats = page.locator('div.box-shadow-1.border-radius-04.overflow-hidden.bg-color-white-1.margin-top-24')
		
		if contenedor_stats.count() == 0:
			print("❌ No se encontró el contenedor de estadísticas")
			return metricas
		
		# Buscar cada métrica por su enlace y texto
		elementos_li = contenedor_stats.locator('li').all()
		print(f"📊 Encontrados {len(elementos_li)} elementos de métricas")
		
		for i, elemento in enumerate(elementos_li):
			try:
				# Buscar el enlace con el texto de la métrica
				enlace_texto = elemento.locator('a').first
				if enlace_texto.count() == 0:
					continue
					
				texto_metrica = enlace_texto.inner_text().strip().lower()
				
				# Buscar el número (el segundo enlace con font-size-40)
				enlace_numero = elemento.locator('a.font-size-40.font-weight-300')
				if enlace_numero.count() == 0:
					continue
					
				numero_texto = enlace_numero.inner_text().strip()
				
				# Limpiar el número (quitar puntos de miles)
				numero_limpio = numero_texto.replace('.', '').replace(',', '')
				
				if not numero_limpio.isdigit():
					print(f"⚠️ Número no válido encontrado: '{numero_texto}' -> '{numero_limpio}'")
					continue
					
				numero = int(numero_limpio)
				
				# Asignar el número a la métrica correspondiente
				if 'abiertos' in texto_metrica and 'no' not in texto_metrica:
					metricas['abiertos'] = numero
					print(f"✅ Abiertos: {numero}")
				elif 'no abiertos' in texto_metrica:
					metricas['no_abiertos'] = numero
					print(f"✅ No abiertos: {numero}")
				elif 'clics' in texto_metrica:
					metricas['clics'] = numero
					print(f"✅ Clics: {numero}")
				elif 'hard bounces' in texto_metrica:
					metricas['hard_bounces'] = numero
					print(f"✅ Hard bounces: {numero}")
				elif 'soft bounces' in texto_metrica:
					metricas['soft_bounces'] = numero
					print(f"✅ Soft bounces: {numero}")
				else:
					print(f"📋 Métrica ignorada: {texto_metrica} = {numero}")
					
			except Exception as e:
				print(f"⚠️ Error procesando elemento {i}: {e}")
				continue
		
		print(f"📊 MÉTRICAS EXTRAÍDAS: {metricas}")
		
	except Exception as e:
		print(f"❌ Error extrayendo métricas: {e}")
	
	return metricas

def obtener_listado_suscriptores(page: Page, nombre_campania: str, lista: str) -> list[list[list[str]]]:
	"""
	Obtiene los listado de todos los suscriptores de una campaña
	"""
	logger = get_logger()
	logger.start_timer("obtener_listado_suscriptores")
	logger.log_checkpoint("inicio_detalle_suscriptores", f"campaña: {nombre_campania}")
	
	try:
		logger.log_browser_action("Haciendo clic en Detalles suscriptores")
		click_element(page.get_by_role('link', name="Detalles suscriptores"))
		logger.log_checkpoint("click_detalles_done", "esperando carga")
		
		page.wait_for_load_state('networkidle')
		logger.log_checkpoint("pagina_cargada", "extrayendo métricas")

		# Extraer métricas totales ANTES de procesar los suscriptores
		logger.logger.info(f"\n🎯 === PROCESANDO CAMPAÑA: {nombre_campania} ===")
		metricas_totales = extraer_metricas_del_panel(page)
		logger.log_checkpoint("metricas_extraidas", f"métricas: {metricas_totales}")

		logger.log_browser_action("Localizando filtro de consulta")
		filtro = page.locator('select#query-filter')
		logger.log_checkpoint("filtro_localizado", "listo para procesar")

		logger.logger.info(f"📋 MÉTRICAS ESPERADAS: Abiertos: {metricas_totales['abiertos']:,}, No abiertos: {metricas_totales['no_abiertos']:,}, Clics: {metricas_totales['clics']:,}, Hard bounces: {metricas_totales['hard_bounces']:,}, Soft bounces: {metricas_totales['soft_bounces']:,}")

		abrieron = []
		no_abrieron = []
		clics = []
		hard_bounces = []
		soft_bounces = []

		# Procesar ABIERTOS
		if metricas_totales['abiertos'] > 0:
			try:
				print(f"\n🔍 Obteniendo suscriptores que ABRIERON (esperados: {metricas_totales['abiertos']:,})...")
				filtro.select_option(label="Abiertos")
				page.wait_for_load_state('networkidle')
				abrieron = obtener_suscriptores_abrieron(page, nombre_campania, lista) or []
				if len(abrieron) != metricas_totales['abiertos']:
					print(f"🚨 DISCREPANCIA ABIERTOS: Obtenidos {len(abrieron):,} vs Esperados {metricas_totales['abiertos']:,}")
			except Exception as e:
				print(f"❌ Error obteniendo suscriptores que abrieron: {e}")

		# Procesar NO ABIERTOS
		if metricas_totales['no_abiertos'] > 0:
			try:
				print(f"\n🔍 Obteniendo suscriptores que NO ABRIERON (esperados: {metricas_totales['no_abiertos']:,})...")
				filtro.select_option(label="No abiertos")
				page.wait_for_load_state('networkidle')
				no_abrieron = obtener_suscriptores_no_abrieron(page, nombre_campania, lista) or []
				print(f"✅ No abiertos obtenidos: {len(no_abrieron):,}")
				
				if len(no_abrieron) != metricas_totales['no_abiertos']:
					print(f"🚨 DISCREPANCIA NO ABIERTOS: Obtenidos {len(no_abrieron):,} vs Esperados {metricas_totales['no_abiertos']:,}")
			except Exception as e:
				print(f"❌ Error obteniendo suscriptores que no abrieron: {e}")

		# Procesar CLICS
		if metricas_totales['clics'] > 0:
			try:
				print(f"\n🔍 Obteniendo suscriptores que hicieron CLIC...")
				filtro.select_option(label="Clics")
				page.wait_for_load_state('networkidle')
				clics = obtener_suscriptores_hicieron_clic(page, nombre_campania, lista) or []
				print(f"✅ Clics obtenidos: {len(clics):,}")
			except Exception as e:
				print(f"❌ Error obteniendo suscriptores que hicieron clic: {e}")

		# Procesar HARD BOUNCES
		if metricas_totales['hard_bounces'] > 0:
			try:
				print(f"\n🔍 Obteniendo HARD BOUNCES...")
				filtro.select_option(label="Hard bounces")
				page.wait_for_load_state('networkidle')
				hard_bounces = obtener_suscriptores_hard_bounces(page, nombre_campania, lista) or []
				print(f"✅ Hard bounces obtenidos: {len(hard_bounces):,}")
			except Exception as e:
				print(f"❌ Error obteniendo hard bounces: {e}")

		# Procesar SOFT BOUNCES
		if metricas_totales['soft_bounces'] > 0:
			try:
				print(f"\n🔍 Obteniendo SOFT BOUNCES...")
				filtro.select_option(label="Soft bounces")
				page.wait_for_load_state('networkidle')
				soft_bounces = obtener_suscriptores_soft_bounces(page, nombre_campania, lista) or []
				print(f"✅ Soft bounces obtenidos: {len(soft_bounces):,}")
				
				if len(soft_bounces) != metricas_totales['soft_bounces']:
					print(f"🚨 DISCREPANCIA SOFT BOUNCES: Obtenidos {len(soft_bounces):,} vs Esperados {metricas_totales['soft_bounces']:,}")
			except Exception as e:
				print(f"❌ Error obteniendo soft bounces: {e}")

		# RESUMEN FINAL
		print(f"\n📊 === RESUMEN FINAL: {nombre_campania} ===")
		print(f"📈 Abiertos: {len(abrieron):,} / {metricas_totales['abiertos']:,}")
		print(f"📉 No abiertos: {len(no_abrieron):,} / {metricas_totales['no_abiertos']:,}")
		print(f"🖱️ Clics: {len(clics):,} / {metricas_totales['clics']:,}")
		print(f"💥 Hard bounces: {len(hard_bounces):,} / {metricas_totales['hard_bounces']:,}")
		print(f"⚠️ Soft bounces: {len(soft_bounces):,} / {metricas_totales['soft_bounces']:,}")

		total_obtenido = len(abrieron) + len(no_abrieron) + len(clics) + len(hard_bounces) + len(soft_bounces)
		total_esperado = sum(metricas_totales.values())
		
		if total_obtenido != total_esperado:
			print(f"🚨 DISCREPANCIA TOTAL: {total_obtenido:,} obtenidos vs {total_esperado:,} esperados")
		else:
			print(f"✅ TOTAL CORRECTO: {total_obtenido:,} suscriptores")

		# Cerrar timer y devolver resultados
		logger.end_timer("obtener_listado_suscriptores")
		return [abrieron, no_abrieron, clics, hard_bounces, soft_bounces]

	except Exception as e:
		# Manejo del try externo
		print(f"❌ Error general en obtener_listado_suscriptores: {e}")
		logger.log_error("obtener_listado_suscriptores", e)
		logger.end_timer("obtener_listado_suscriptores")
		raise

def procesar_seguimiento_urls(page: Page, informe_detallado: list[list[str]]):
	"""
	Procesa el seguimiento de URLs y marca los clics en el informe detallado
	"""
	click_element(page.get_by_role('link', name="Seguimiento url's"))
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
				click_element(btn_menu)

				click_element(urls_seguimiento.nth(z).get_by_role('link', name="Detalles"))

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
	logger = get_logger()
	logger.start_timer("crear_archivo_excel")
	logger.log_file_operation("Creando archivo Excel", "nuevo archivo")
	
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
		logger.log_data_extraction("datos_generales", len(general), "hoja General")
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
				logger.log_warning("crear_archivo_excel", f"Saltando fila de encabezados errónea: {fila}")
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
			logger.log_data_extraction(f"datos_{nombre_hoja.lower()}", len(datos), f"hoja {nombre_hoja}")
			
			# Escribir headers
			for col_idx, columna in enumerate(columnas, 1):
				ws.cell(row=1, column=col_idx, value=columna)
			
			# Escribir datos
			for fila in datos:
				ws.append(fila)

		# Guardar archivo
		ahora = datetime.now()
		fecha_texto = ahora.strftime("%Y%m%d%H%M")
		nombre_archivo = f"{ARCHIVO_INFORMES_PREFIX}_{fecha_texto}.xlsx"
		
		wb.save(nombre_archivo)
		file_size = os.path.getsize(nombre_archivo)
		
		logger.end_timer("crear_archivo_excel")
		logger.log_file_operation("Guardado", nombre_archivo, file_size)
		logger.log_success("crear_archivo_excel", f"Archivo Excel creado: {nombre_archivo}")
		
		notify("Proceso finalizado", f"Lista de suscriptores obtenida")
		return nombre_archivo
		
	except Exception as e:
		logger.log_error("crear_archivo_excel", e)
		logger.end_timer("crear_archivo_excel")
		raise

def main():
	logger = get_logger()
	logger.start_timer("main_process")
	logger.log_success("main_process", "Iniciando proceso principal de automatización")
	
	try:
		# Config cargada en runtime y términos de búsqueda
		config = load_config()
		url = config.get("url", "")
		url_base = config.get("url_base", "")
		extraccion_oculta = bool(config.get("headless", False))

		logger.log_browser_action("Configuración cargada", f"headless={extraccion_oculta}")
		
		terminos = cargar_terminos_busqueda(ARCHIVO_BUSQUEDA)
		
		if not terminos:
			logger.log_error("main_process", Exception("No se encontraron términos"), "archivo de búsqueda vacío")
			return
		
		logger.log_success("main_process", f"Cargados {len(terminos)} términos de búsqueda")
		
		with sync_playwright() as p:
			browser = configurar_navegador(p, extraccion_oculta)
			context = crear_contexto_navegador(browser, extraccion_oculta)
			
			page = context.new_page()
			
			safe_goto(page, url_base, "domcontentloaded")
			safe_goto(page, url, "domcontentloaded")
			
			login(page)
			context.storage_state(path=storage_state_path())

			# LOGGING DETALLADO POST-LOGIN
			logger.log_checkpoint("post_login", "Login completado, iniciando navegación")
			
			# Verificar URL actual
			current_url = page.url
			logger.log_checkpoint("url_actual", f"URL: {current_url}")
			
			# Verificar si la página está cargada
			logger.log_checkpoint("verificando_carga", "esperando domcontentloaded")
			page.wait_for_load_state('domcontentloaded', timeout=10000)
			logger.log_checkpoint("dom_loaded", "DOM cargado")
			
			# Verificar si hay elementos visibles
			logger.log_checkpoint("verificando_elementos", "contando elementos visibles")
			try:
				body_text = page.locator('body').inner_text()
				logger.log_checkpoint("body_text_length", f"Texto del body: {len(body_text)} caracteres")
				if body_text:
					logger.log_checkpoint("body_sample", f"Primeros 200 chars: {body_text[:200]}")
			except Exception as e:
				logger.log_error("verificar_body", e, "No se pudo leer el body")

			# Buscar enlaces de navegación disponibles
			logger.log_checkpoint("buscando_enlaces", "localizando enlaces de navegación")
			try:
				enlaces = page.locator('a').all()
				logger.log_checkpoint("enlaces_encontrados", f"Total enlaces: {len(enlaces)}")
				
				# Buscar específicamente el enlace de reports
				reports_link = page.locator("a[href*='/reports']")
				if reports_link.count() > 0:
					logger.log_checkpoint("reports_link_found", "Enlace de reports encontrado")
					# Asegurar navegación a la sección de reports para que exista el buscador
					click_element(reports_link.first)
					page.wait_for_load_state('domcontentloaded')
					logger.log_checkpoint("reports_navegado", f"URL: {page.url}")
				else:
					logger.log_warning("reports_link_missing", "No se encontró enlace de reports")
					
					# Listar algunos enlaces para debug
					for i, enlace in enumerate(enlaces[:5]):  # Solo primeros 5
						try:
							href = enlace.get_attribute('href') or ""
							text = enlace.inner_text()[:50]  # Primeros 50 chars
							logger.log_checkpoint(f"enlace_{i}", f"href={href}, text={text}")
						except:
							continue
							
			except Exception as e:
				logger.log_error("buscar_enlaces", e, "Error buscando enlaces")

			general: list[list[str]] = []
			abiertos: list[list[str]] = []
			no_abiertos = []
			clics = []
			hard_bounces = []
			soft_bounces = []
			
			# BUSCAR ELEMENTO BUSCADOR CON LOGGING MUY DETALLADO
			logger.start_timer("buscar_elemento_buscador")
			logger.log_checkpoint("inicio_buscar_buscador", "placeholder: 'Buscar informe'")
			logger.log_browser_action("Buscando elemento buscador", "placeholder: 'Buscar informe'")
			
			try:
				# Asegurarnos de estar en la página de reportes antes de buscar el input
				try:
					navegar_a_reportes(page)
				except Exception as e:
					logger.log_warning("navegar_a_reportes_fallback", f"No se pudo asegurar navegación previa a reportes: {e}")

				# Estrategia multi-selector para ubicar el buscador
				timeouts = get_timeouts()
				candidatos = [
					page.locator("input[name='search_word']"),  # Selector principal basado en diagnóstico
					page.get_by_placeholder("Buscar informe"),  # Selector secundario
					page.locator("input[placeholder='Buscar informe']"),  # Selector exacto
					page.get_by_placeholder("Buscar informes"),
					page.locator("input[placeholder*='Buscar' i]"),
					page.locator("input[type='search']"),
					page.locator('#newsletter-reports').locator("input[placeholder], input[type='search'], input[type='text']"),
				]

				buscador = None
				for idx, cand in enumerate(candidatos):
					try:
						if cand.count() > 0:
							cand.first.wait_for(timeout=timeouts['elements'])
							buscador = cand.first
							logger.log_checkpoint("buscador_encontrado", f"estrategia {idx+1}")
							break
					except Exception:
						continue

				if buscador is None:
					logger.log_warning("buscador_no_existe", "No se encontró el input de búsqueda tras múltiples estrategias")
					# Debug adicional de inputs
					inputs = page.locator('input')
					num_inputs = inputs.count()
					logger.log_checkpoint("debug_inputs", f"Total inputs encontrados: {num_inputs}")
					for i in range(min(num_inputs, 10)):
						try:
							input_elem = inputs.nth(i)
							placeholder = input_elem.get_attribute('placeholder') or ""
							input_type = input_elem.get_attribute('type') or ""
							name_attr = input_elem.get_attribute('name') or ""
							logger.log_checkpoint(f"input_{i}", f"placeholder='{placeholder}', type='{input_type}', name='{name_attr}'")
						except Exception:
							continue
					# Capturar screenshot para diagnóstico
					try:
						screenshot_path = data_path(f"no_search_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
						page.screenshot(path=screenshot_path)
						logger.log_file_operation("Screenshot capturado", screenshot_path)
					except Exception:
						pass
					raise Exception("Elemento buscador no encontrado")

				# Verificar que el elemento es interactuable
				logger.log_checkpoint("esperando_interactuable", "usando timeout configurado")
				buscador.wait_for(timeout=timeouts['elements'])
				
				logger.end_timer("buscar_elemento_buscador")
				logger.log_success("buscar_elemento_buscador", "Elemento buscador encontrado y listo")
				
			except Exception as e:
				logger.log_error("buscar_elemento_buscador", e, f"URL actual: {page.url}")
				logger.end_timer("buscar_elemento_buscador")
				
				# Tomar screenshot para debug si es posible
				try:
					screenshot_path = data_path(f"error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
					page.screenshot(path=screenshot_path)
					logger.log_file_operation("Screenshot capturado", screenshot_path)
				except:
					pass
				
				raise
			
			for i, termino in enumerate(terminos):
				logger.start_timer(f"procesar_termino_{i+1}")
				logger.log_progress(i+1, len(terminos), f"Procesando término: {termino[0]} - {termino[1]}")
				
				try:
					# Buscar y obtener datos de la campaña
					logger.log_checkpoint("inicio_busqueda_campania", f"término {i+1}: {termino[0]}")
					datos_campania = buscar_campania_por_termino(page, termino, buscador)
					logger.log_checkpoint("campania_encontrada", f"datos: {len(datos_campania)} campos")
					general.append(datos_campania)

					# Obtener detalles de suscriptores
					logger.log_checkpoint("inicio_extraccion_suscriptores", f"campaña: {datos_campania[0]}")
					logger.log_heartbeat("extrayendo_suscriptores", "iniciando proceso largo")
					listado_suscriptores = obtener_listado_suscriptores(
						page, 
						nombre_campania= datos_campania[0], 
						lista= datos_campania[3]
						)
					
					logger.log_checkpoint("suscriptores_extraidos", f"total listas: {len(listado_suscriptores)}")
					abiertos.extend(listado_suscriptores[0])
					no_abiertos.extend(listado_suscriptores[1])
					clics.extend(listado_suscriptores[2])
					hard_bounces.extend(listado_suscriptores[3])
					soft_bounces.extend(listado_suscriptores[4])
					
					logger.log_checkpoint("datos_agregados", f"total acumulado: abiertos={len(abiertos)}, no_abiertos={len(no_abiertos)}")
					
					# Procesar seguimiento de URLs
					# procesar_seguimiento_urls(page, detalles_suscriptores)
					
					# Volver a la página de reportes
					logger.log_checkpoint("volviendo_reportes", "haciendo clic en Emails")
					logger.log_browser_action("Volviendo a reportes")
					click_element(page.get_by_role('link', name='Emails'))
					logger.log_checkpoint("click_emails_done", "navegación completada")
					
					logger.end_timer(f"procesar_termino_{i+1}")
					logger.log_success(f"procesar_termino_{i+1}", "Término procesado exitosamente")
				
				except Exception as e:
					logger.log_error(f"procesar_termino_{i+1}", e, f"término: {termino[0]} - {termino[1]}")
					logger.end_timer(f"procesar_termino_{i+1}")
					continue

			# Crear archivo Excel con los resultados
			logger.start_timer("crear_excel")
			if general or abiertos or no_abiertos or clics or hard_bounces or soft_bounces:
				archivo_creado = crear_archivo_excel(general, [abiertos, no_abiertos, clics, hard_bounces, soft_bounces])
				logger.end_timer("crear_excel")
				logger.log_success("crear_excel", f"Archivo creado: {archivo_creado}")
			else:
				logger.log_warning("crear_excel", "No se procesaron datos, no se creó archivo Excel")
				logger.end_timer("crear_excel")
			
			browser.close()
			logger.end_timer("main_process")
			logger.log_success("main_process", "Proceso principal completado")
			
			# Mostrar reporte de rendimiento
			logger.print_performance_report()
			
	except Exception as e:
		logger.log_error("main_process", e)
		logger.end_timer("main_process")
		raise
def extraer_metricas_del_panel(page: Page) -> dict:
	"""
	Extrae las métricas reales desde el panel de estadísticas
	"""
	metricas = {'abiertos': 0, 'no_abiertos': 0, 'clics': 0, 'hard_bounces': 0, 'soft_bounces': 0}
	
	try:
		# Buscar el contenedor específico
		contenedor = page.locator('div.box-shadow-1.border-radius-04.overflow-hidden.bg-color-white-1.margin-top-24')
		if contenedor.count() == 0:
			print("❌ No se encontró el contenedor de métricas")
			return metricas
		
		# Extraer cada métrica
		elementos = contenedor.locator('li').all()
		
		for i, elemento in enumerate(elementos):
			try:
				# Buscar el texto del enlace
				texto_link = elemento.locator('a').first
				if texto_link.count() == 0:
					continue
				texto = texto_link.inner_text().lower().strip()
				
				# Buscar el número
				numero_link = elemento.locator('a.font-size-40')
				if numero_link.count() == 0:
					continue
				numero_str = numero_link.inner_text().replace('.', '').replace(',', '')
				
				if not numero_str.isdigit():
					continue
				numero = int(numero_str)
				
				# Asignar según el texto
				if 'abiertos' in texto and 'no' not in texto:
					metricas['abiertos'] = numero
				elif 'no abiertos' in texto:
					metricas['no_abiertos'] = numero
				elif 'clics' in texto:
					metricas['clics'] = numero
				elif 'hard bounces' in texto:
					metricas['hard_bounces'] = numero
				elif 'soft bounces' in texto:
					metricas['soft_bounces'] = numero
					
			except Exception as e:
				continue
				
	except Exception as e:
		print(f"❌ Error extrayendo métricas: {e}")
	
	return metricas


if __name__ == "__main__":
	main()