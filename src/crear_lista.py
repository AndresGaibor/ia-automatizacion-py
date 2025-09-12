from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page
from .utils import cargar_terminos_busqueda, crear_contexto_navegador, configurar_navegador, navegar_a_reportes, navegar_siguiente_pagina, obtener_total_paginas, load_config, data_path, storage_state_path, notify, get_timeouts, safe_goto
from .autentificacion import login
from .tipo_campo import field_type_label
import pandas as pd
import os
import threading
import tkinter as tk
from tkinter import messagebox
import tempfile
import uuid
import time
from .logger import get_logger

archivo_busqueda = data_path("Lista_envio.xlsx")

def listar_hojas(archivo: str) -> list[str]:
	"""Devuelve la lista de hojas del archivo Excel."""
	with pd.ExcelFile(archivo, engine="openpyxl") as xls:
		return [str(n) for n in xls.sheet_names]

def _seleccionar_hoja_cli(archivo: str, multiple=False) -> str | list[str]:
	"""Selector por consola (fallback)."""
	hojas = listar_hojas(archivo)
	if not hojas:
		raise ValueError("El archivo no contiene hojas.")
	if len(hojas) == 1:
		print(f"Usando única hoja: {hojas[0]}")
		return [hojas[0]] if multiple else hojas[0]
	
	print("\nHojas disponibles en el Excel:")
	for i, h in enumerate(hojas, 1):
		print(f"  {i}) {h}")
	
	if multiple:
		print("\nPuedes seleccionar múltiples hojas usando:")
		print("  - Números separados por comas: 1,3,5")
		print("  - Rangos: 1-3 (hojas 1, 2 y 3)")
		print("  - Combinación: 1,3-5,7")
		prompt = f"Selecciona las hojas (1-{len(hojas)}) [1]: "
	else:
		prompt = f"Selecciona la hoja (1-{len(hojas)}) [1]: "
	
	while True:
		op = input(prompt).strip()
		if op == "":
			return [hojas[0]] if multiple else hojas[0]
		
		if not multiple:
			# Modo simple (original)
			if op.isdigit():
				idx = int(op)
				if 1 <= idx <= len(hojas):
					return hojas[idx - 1]
			print("Opción inválida. Intenta nuevamente.")
			continue
		
		# Modo múltiple
		try:
			indices_seleccionados = set()
			partes = op.split(',')
			
			for parte in partes:
				parte = parte.strip()
				if '-' in parte:
					# Rango: 2-5
					inicio, fin = parte.split('-', 1)
					inicio = int(inicio.strip())
					fin = int(fin.strip())
					if 1 <= inicio <= len(hojas) and 1 <= fin <= len(hojas):
						for i in range(min(inicio, fin), max(inicio, fin) + 1):
							indices_seleccionados.add(i)
					else:
						raise ValueError(f"Rango inválido: {parte}")
				else:
					# Número individual
					idx = int(parte)
					if 1 <= idx <= len(hojas):
						indices_seleccionados.add(idx)
					else:
						raise ValueError(f"Número inválido: {idx}")
			
			if indices_seleccionados:
				hojas_seleccionadas = [hojas[i-1] for i in sorted(indices_seleccionados)]
				print(f"Hojas seleccionadas: {', '.join(hojas_seleccionadas)}")
				return hojas_seleccionadas
			else:
				print("No se seleccionó ninguna hoja válida.")
		except (ValueError, IndexError) as e:
			print(f"Entrada inválida: {e}. Intenta nuevamente.")
		except Exception:
			print("Formato inválido. Intenta nuevamente.")

def _can_use_tk() -> bool:
	"""Tk solo en hilo principal."""
	return threading.current_thread() is threading.main_thread()

def seleccionar_hoja_tk(archivo: str, master=None, multiple=False):
	"""Ventana modal para elegir hoja(s). Devuelve nombre o lista de nombres o None."""
	try:
		hojas = listar_hojas(archivo)
	except Exception as e:
		if isinstance(master, tk.Misc):
			messagebox.showerror("Error", f"No se pudieron listar hojas:\n{e}", parent=master)
		else:
			messagebox.showerror("Error", f"No se pudieron listar hojas:\n{e}")
		return None
	if not hojas:
		if isinstance(master, tk.Misc):
			messagebox.showwarning("Excel", "El archivo no contiene hojas.", parent=master)
		else:
			messagebox.showwarning("Excel", "El archivo no contiene hojas.")
		return None

	owns_root = False
	if master is None:
		if not _can_use_tk():
			return None
		master = tk.Tk()
		master.withdraw()
		owns_root = True

	# El dict 'result' puede contener None, un str (hoja única) o list[str] (múltiples hojas)
	result: dict[str, str | list[str] | None] = {"val": None}

	win = tk.Toplevel(master)
	title = "Seleccionar hojas" if multiple else "Seleccionar hoja"
	win.title(title)
	win.resizable(False, False)
	win.grab_set()
	win.transient(master)
	# Ventana más amplia para nombres largos
	try:
		win.geometry("820x520")
	except Exception:
		pass

	# Instrucciones diferentes según el modo
	if multiple:
		instrucciones = "Selecciona las hojas a usar (mantén Ctrl/Cmd para seleccionar múltiples):"
	else:
		instrucciones = "Selecciona la hoja a usar:"
	
	tk.Label(win, text=instrucciones).pack(padx=12, pady=(12, 6), anchor="w")

	# Contenedor con scrollbars para ver nombres largos
	frame_lb = tk.Frame(win)
	frame_lb.pack(padx=12, fill="both", expand=True)
	frame_lb.rowconfigure(0, weight=1)
	frame_lb.columnconfigure(0, weight=1)

	# Configurar selectmode según si es múltiple o no
	selectmode = tk.EXTENDED if multiple else tk.SINGLE
	lb = tk.Listbox(frame_lb, height=min(14, len(hojas)), exportselection=False, selectmode=selectmode)
	vsb = tk.Scrollbar(frame_lb, orient="vertical", command=lb.yview)
	hsb = tk.Scrollbar(frame_lb, orient="horizontal", command=lb.xview)
	lb.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

	for h in hojas:
		lb.insert(tk.END, h)
	lb.selection_set(0)

	lb.grid(row=0, column=0, sticky="nsew")
	vsb.grid(row=0, column=1, sticky="ns")
	hsb.grid(row=1, column=0, sticky="ew")

	btns = tk.Frame(win)
	btns.pack(padx=12, pady=12, fill="x")

	def aceptar():
		try:
			indices = lb.curselection()
			if multiple:
				if not indices:
					result["val"] = None
				else:
					result["val"] = [hojas[idx] for idx in indices]
			else:
				if not indices:
					result["val"] = None
				else:
					result["val"] = hojas[indices[0]]
		except Exception:
			result["val"] = None
		win.destroy()

	def cancelar():
		result["val"] = None
		win.destroy()

	tk.Button(btns, text="Cancelar", command=cancelar).pack(side="right")
	tk.Button(btns, text="Aceptar", command=aceptar).pack(side="right", padx=6)

	win.bind("<Return>", lambda e: aceptar())
	win.bind("<Escape>", lambda e: cancelar())

	win.wait_window()
	if owns_root:
		master.destroy()
	return result["val"]

def seleccionar_hoja(archivo: str, multiple=False) -> str | list[str]:
	"""Intenta UI; si no, cae a CLI."""
	if _can_use_tk():
		sel = seleccionar_hoja_tk(archivo, master=None, multiple=multiple)
		if sel:
			return sel
	return _seleccionar_hoja_cli(archivo, multiple=multiple)

def cargar_columnas(archivo: str, nombre_hoja: str | None = None) -> tuple[list[str], list[str]]:
	"""
	Carga:
	- columnas: [<nombre_hoja>, <col1>, <col2>, ...]
	- segunda_fila: valores de la primera fila de datos (debajo del encabezado), alineados a columnas[1:]
	"""
	try:
		with pd.ExcelFile(archivo, engine="openpyxl") as xls:
			hoja = nombre_hoja or str(xls.sheet_names[0])
			# Leemos como texto y reemplazamos NaN por vacío para evitar tipos mixtos
			df = pd.read_excel(xls, sheet_name=hoja, dtype=str).fillna("")

		columnas_sin_hoja: list[str] = [str(c) for c in df.columns.tolist()]
		columnas: list[str] = [hoja] + columnas_sin_hoja

		# “Segunda fila de datos”: primera fila de datos bajo el header
		if len(df) > 0:
			segunda_fila: list[str] = [str(v) for v in df.iloc[0].tolist()]
		else:
			segunda_fila = [""] * len(columnas_sin_hoja)

		return columnas, segunda_fila
	except Exception as e:
		print(f"Error al cargar columnas: {e}")
		return ["", ""], []

print("Cargando último término de búsqueda...")

REAL_UA = (
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/537.36 "
	"(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

def inicializar_navegacion_lista(page: Page):
	"""
	Navega a la sección de lista y espera a que cargue
	"""
	page.click("a[href*='/list']")
	page.wait_for_load_state("domcontentloaded")

def _generar_archivo_subida_desde_hoja(archivo_excel: str, hoja: str) -> str:
	"""Genera un CSV temporal solo con la hoja indicada y devuelve su ruta."""
	with pd.ExcelFile(archivo_excel, engine="openpyxl") as xls:
		df = pd.read_excel(xls, sheet_name=hoja, dtype=str).fillna("")
	# CSV temporal compatible con Excel (utf-8-sig)
	tmp_path = os.path.join(tempfile.gettempdir(), f"lista_{uuid.uuid4().hex}.csv")
	df.to_csv(tmp_path, index=False, encoding="utf-8-sig")
	return tmp_path

def _cerrar_popup_si_presente(page: Page) -> bool:
	"""Intenta cerrar el popup "Aceptar" si está presente, con clic rápido o JS.

	Retorna True si realizó alguna acción de cierre.
	"""
	try:
		popup = page.locator('a', has_text="Aceptar")
		if popup.count() > 0:
			el = popup.first
			# Intento de clic visible rápido
			try:
				if el.is_visible():
					el.click(timeout=800)
					return True
			except Exception:
				pass
			# Fallback JS
			try:
				page.evaluate(
					"""
					() => { try { if (window.close_form) { window.close_form('recognized-list-popup'); } } catch (e) {} }
					"""
				)
				return True
			except Exception:
				return False
	except Exception:
		return False
	return False

def _esperar_despues_de_anadir(page: Page) -> bool:
	"""
	Después de subir y hacer clic en 'Añadir', esperar de forma robusta a que:
	- Aparezca un popup con botón 'Aceptar' (y hacer clic), o
	- Se cargue directamente la pantalla de mapeo de columnas.

	Retorna True si se detectó uno de los estados esperados.
	"""
	logger = get_logger()
	timeouts = get_timeouts()

	max_espera = min(int(timeouts.get('long_operations', 120)), 180)  # límite de seguridad 180s
	inicio = time.time()
	aceptado = False

	logger.start_timer("esperar_post_anadir")
	# Marcador para medir tiempo hasta mapeo listo
	t0 = time.time()
	# Ventana de gracia para permitir que aparezca el popup 'Aceptar' (sitios lentos)
	gracia_popup_seg = 10.0
	logger.log_checkpoint("post-anadir", f"Esperando popup 'Aceptar' o pantalla de mapeo (max {max_espera}s)")

	while (time.time() - inicio) < max_espera:
		# 1) Primero: ¿ya estamos en la pantalla de mapeo? (evita perder tiempo con un 'Aceptar' oculto)
		try:
			cont = page.locator("div.col", has_text="Columna 2")
			if cont.count() > 0 and cont.first.locator("select").count() > 0:
				# Antes de salir, intentar cerrar el popup si está presente para que no bloquee interacciones
				_cerrar_popup_si_presente(page)
				elapsed = round(time.time() - t0, 2)
				logger.log_success("pantalla_mapeo_detectada", f"Detectada la UI de mapeo de columnas en {elapsed}s")
				logger.end_timer("esperar_post_anadir")
				return True
		except Exception:
			pass

		# 2) Señal alternativa: botón 'Siguiente' visible (propio del paso de mapeo)
		try:
			btn_sig = page.locator('a:visible', has_text="Siguiente")
			if btn_sig.count() > 0:
				# Antes de salir, intentar cerrar el popup si está presente para que no bloquee interacciones
				_cerrar_popup_si_presente(page)
				elapsed = round(time.time() - t0, 2)
				logger.log_checkpoint("btn_siguiente_visible", f"Señal alternativa de mapeo listo en {elapsed}s")
				logger.end_timer("esperar_post_anadir")
				return True
		except Exception:
			pass

		# 3) ¿Hay popup 'Aceptar'? Manejarlo sin reintentos largos
		try:
			popup = page.locator('a', has_text="Aceptar")
			if popup.count() > 0:
				el = popup.first
				# Si está visible ahora mismo, clic rápido con timeout corto; no usar retry_click_element
				try:
					if el.is_visible():
						logger.log_browser_action("Popup detectado", "Aceptar (visible)")
						el.click(timeout=1200)
						aceptado = True
						logger.log_success("click_popup_aceptar", "Se hizo clic rápido en 'Aceptar'")
						try:
							page.wait_for_load_state("domcontentloaded", timeout=2000)
						except Exception:
							pass
						# Continuar el bucle para detectar mapeo
						continue
				except Exception:
					# ignorar y probar JS
					pass

				# Si no está visible: si estamos dentro de la ventana de gracia, esperar brevemente a visibilidad
				try:
					if (time.time() - t0) < gracia_popup_seg:
						el.wait_for(state="visible", timeout=1200)
						el.click(timeout=1200)
						aceptado = True
						logger.log_success("click_popup_aceptar_gracia", "'Aceptar' apareció durante la ventana de gracia")
						try:
							page.wait_for_load_state("domcontentloaded", timeout=1500)
						except Exception:
							pass
						continue
				except Exception:
					pass

				# Si sigue oculto o el clic falló, intentar cerrar por JS y seguir
				try:
					page.evaluate(
						"""
						() => { try { if (window.close_form) { window.close_form('recognized-list-popup'); } } catch (e) {} }
						"""
					)
					aceptado = True
					logger.log_success("click_popup_aceptar_js", "Se cerró popup por JS close_form('recognized-list-popup')")
					try:
						page.wait_for_load_state("domcontentloaded", timeout=1500)
					except Exception:
						pass
					continue
				except Exception:
					# Si no hay función JS o falla, no bloquear; seguir iterando
					logger.log_checkpoint("popup_aceptar_oculto", "Popup presente pero oculto; se omitirá hasta que aparezca mapeo")
					pass
		except Exception:
			pass

		# Pulso de vida y espera breve
		transcurrido = int(time.time() - inicio)
		if transcurrido % 5 == 0:  # cada ~5s
			logger.log_heartbeat("esperar_post_anadir", f"{transcurrido}s transcurridos; aceptado={aceptado}")
		page.wait_for_timeout(300)

	logger.end_timer("esperar_post_anadir", "timeout")
	logger.log_warning("esperar_post_anadir", f"No se detectó popup 'Aceptar' ni pantalla de mapeo tras {int(time.time()-inicio)}s")
	return False

def _click_aniadir_robusto(page: Page) -> bool:
	"""Hace clic en el botón 'Añadir' del paso de carga de archivo con reintentos y verificaciones.

	Retorna True si después del clic se alcanza alguno de los estados esperados por _esperar_despues_de_anadir.
	"""
	logger = get_logger()
	logger.start_timer("click_aniadir_robusto")

	# Intentar encontrar el botón 'Añadir' cerca del input de archivo
	btn = None
	try:
		cont = page.locator('input#id_csv').first
		# Subir a contenedor padre y buscar un 'a' de Añadir dentro
		padre = cont.locator('xpath=..')
		candidato = padre.locator("a:visible", has_text="Añadir")
		if candidato.count() == 0:
			# subir un nivel más
			padre2 = padre.locator('xpath=..')
			candidato = padre2.locator("a:visible", has_text="Añadir")
		if candidato.count() > 0:
			btn = candidato.first
	except Exception:
		pass

	if btn is None:
		# Fallback: cualquier botón 'Añadir' visible
		btn = page.locator("a:visible", has_text="Añadir").first

	max_reintentos = 4
	for intento in range(1, max_reintentos + 1):
		try:
			get_logger().log_checkpoint("click_aniadir", f"Intento {intento}/{max_reintentos}")
			# Asegurar visibilidad y estabilidad
			btn.wait_for(state="visible", timeout=5000)
			try:
				btn.scroll_into_view_if_needed(timeout=1500)
			except Exception:
				pass
			btn.click(timeout=5000)

			# Pequeña espera para que se dispare la transición
			page.wait_for_timeout(400)
			try:
				page.wait_for_load_state("domcontentloaded", timeout=4000)
			except Exception:
				pass

			# Ahora esperar robustamente los siguientes estados
			if _esperar_despues_de_anadir(page):
				logger.end_timer("click_aniadir_robusto")
				return True

		except Exception as e:
			logger.log_warning("click_aniadir", f"Fallo intento {intento}: {e}")
			page.wait_for_timeout(600)

	logger.end_timer("click_aniadir_robusto", "falló")
	logger.log_warning("click_aniadir", "No se pudo confirmar el efecto de 'Añadir' tras varios reintentos")
	return False

def main(nombre_hoja: str | list[str] | None = None, multiple: bool = False):
	config = load_config()
	url = config.get("url", "")
	url_base = config.get("url_base", "")
	extraccion_oculta = bool(config.get("headless", False))
	
	# Seleccionar hojas (múltiples por defecto)
	hojas_seleccionadas = nombre_hoja or seleccionar_hoja(archivo_busqueda, multiple=multiple)
	
	# Asegurar que siempre tengamos una lista
	if isinstance(hojas_seleccionadas, str):
		hojas_seleccionadas = [hojas_seleccionadas]
	elif hojas_seleccionadas is None:
		print("No se seleccionaron hojas.")
		return
	
	print(f"📋 Se crearán {len(hojas_seleccionadas)} listas de suscriptores:")
	for i, hoja in enumerate(hojas_seleccionadas, 1):
		print(f"  {i}. {hoja}")
	
	tmp_subida: str | None = None
	
	with sync_playwright() as p:
		browser = configurar_navegador(p, extraccion_oculta)
		context = crear_contexto_navegador(browser, extraccion_oculta)
		
		page = context.new_page()
		
		safe_goto(page, url_base, "domcontentloaded")
		safe_goto(page, url, "domcontentloaded")
		
		login(page)
		context.storage_state(path=storage_state_path())

		# Procesar cada hoja seleccionada
		listas_creadas = []
		listas_fallidas = []
		listas_canceladas = []
		limite_alcanzado = False
		
		for idx, hoja_actual in enumerate(hojas_seleccionadas, 1):
			print(f"\n🔄 Procesando hoja {idx}/{len(hojas_seleccionadas)}: {hoja_actual}")
			
			try:
				# Cargar datos de la hoja actual
				campos, segunda_fila = cargar_columnas(archivo_busqueda, hoja_actual)
				nombre_lista = campos[0]  # El nombre de la hoja se usa como nombre de lista
				
				print(f"📝 Creando lista: {nombre_lista}")
				
				# Navegar a la sección de listas
				inicializar_navegacion_lista(page)
				page.wait_for_load_state("networkidle")
				
				# Crear nueva lista
				btn_nueva_lista = page.locator('a:has-text("Nueva Lista"):visible')
				from .utils import click_element, fill_field
				click_element(btn_nueva_lista)
				page.wait_for_load_state("networkidle")

				# Llenar nombre de la lista
				input_nombre_lista = page.locator('input#name')
				input_nombre_lista.fill(nombre_lista)

				# Crear lista
				btn_crear_lista = page.locator('input:visible', has_text="Crear")
				click_element(btn_crear_lista)

				# Agregar suscriptores
				btn_agregar_suscriptores = page.locator('a#add-subscribers-link')
				click_element(btn_agregar_suscriptores)
				page.wait_for_load_state("networkidle")

				# Seleccionar archivo CSV/Excel
				page.get_by_label("Archivo CSV/Excel").check()

				# Generar archivo temporal solo con la hoja actual
				tmp_subida = _generar_archivo_subida_desde_hoja(archivo_busqueda, hoja_actual)
				input_archivo = page.locator('input#id_csv')
				input_archivo.set_input_files(tmp_subida)

				# Añadir archivo (robusto)
				if not _click_aniadir_robusto(page):
					get_logger().log_warning("post_anadir", "'Añadir' no produjo cambios detectables, continuando con heurísticas")
					# Intento de último recurso: click directo si encontramos el botón y luego continuar
					try:
						btns_aniadir = page.locator('a:visible', has_text="Añadir")
						if btns_aniadir.count() > 0:
							btns_aniadir.first.click(timeout=4000)
							page.wait_for_timeout(500)
							_esperar_despues_de_anadir(page)
					except Exception:
						pass
				
				# Configurar campos (columnas)
				for indice, columna in enumerate(campos[2:], start=2):
					contenedor = page.locator("div.col", has_text=f"Columna {indice}")
					selector = contenedor.locator("select")
					selector.select_option(label="Crear nueva...")

					contenedor_popup = page.locator(f"#add-field-popup-{indice}")

					input_nombre = contenedor_popup.locator(f"#popup-field-name-{indice}")
					input_nombre.fill(columna)
					
					tipo_campo = field_type_label(segunda_fila[indice - 1]) if indice - 1 < len(segunda_fila) else "Texto"
					selector_tipo = contenedor_popup.locator("select")
					selector_tipo.select_option(label=tipo_campo)

					btn_aniadir = contenedor_popup.locator('input', has_text="Añadir")
					click_element(btn_aniadir)
				
				# Finalizar importación
				btn_siguiente = page.locator('a:visible', has_text="Siguiente")
				click_element(btn_siguiente)

				# Verificar éxito
				try:
					timeouts = get_timeouts()
					page.wait_for_selector('text="Tus suscriptores se han importado con éxito"', timeout=timeouts['long_operations'])
					print(f"✅ Lista '{nombre_lista}' creada exitosamente")
					listas_creadas.append(nombre_lista)

					# Detección de límite de suscriptores (plan alcanzado)
					limite_1 = page.locator('text=No se han importado')
					limite_2 = page.locator('text=has alcanzado el máximo')
					if (limite_1.count() > 0) or (limite_2.count() > 0):
						print("ℹ️ Se ha alcanzado el límite de suscriptores de tu tarifa. Se cancelarán las listas restantes.")
						limite_alcanzado = True
						# Agregar las hojas restantes como canceladas
						if idx < len(hojas_seleccionadas):
							listas_canceladas.extend(hojas_seleccionadas[idx:])
						break
				except PWTimeoutError:
					print(f"⚠️ No se pudo confirmar la importación de '{nombre_lista}'")
					listas_fallidas.append(nombre_lista)

				page.wait_for_load_state("networkidle")
				
				# Limpiar archivo temporal
				if tmp_subida and os.path.exists(tmp_subida):
					os.remove(tmp_subida)
					tmp_subida = None
					
			except Exception as e:
				print(f"❌ Error procesando hoja '{hoja_actual}': {e}")
				listas_fallidas.append(hoja_actual)
				
				# Limpiar archivo temporal en caso de error
				if tmp_subida and os.path.exists(tmp_subida):
					try:
						os.remove(tmp_subida)
					except:
						pass
					tmp_subida = None
		
		browser.close()
		
		# Resumen final
		print(f"\n📊 Resumen del procesamiento:")
		print(f"✅ Listas creadas exitosamente: {len(listas_creadas)}")
		for lista in listas_creadas:
			print(f"   - {lista}")
		
		if listas_fallidas:
			print(f"❌ Listas con errores: {len(listas_fallidas)}")
			for lista in listas_fallidas:
				print(f"   - {lista}")

		if listas_canceladas:
			print(f"⏹️ Listas canceladas por límite: {len(listas_canceladas)}")
			for lista in listas_canceladas:
				print(f"   - {lista}")
		
		# Notificación final
		if limite_alcanzado:
			titulo = "Proceso cancelado por límite de suscriptores"
			msg = f"Creadas: {len(listas_creadas)} | Canceladas: {len(listas_canceladas)} (límite de tarifa)"
			notify(titulo, msg)
		elif listas_creadas and not listas_fallidas:
			notify("Proceso completado", f"Se crearon {len(listas_creadas)} listas exitosamente")
		elif listas_creadas and listas_fallidas:
			notify("Proceso completado con errores", f"Creadas: {len(listas_creadas)}, Errores: {len(listas_fallidas)}")
		else:
			notify("Proceso fallido", "No se pudieron crear las listas de suscriptores")
	
	# Limpiar archivo temporal final (por si acaso)
	try:
		if tmp_subida and os.path.exists(tmp_subida):
			os.remove(tmp_subida)
	except Exception:
		pass

if __name__ == "__main__":
	main(multiple=True)