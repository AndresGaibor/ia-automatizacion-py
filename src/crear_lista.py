from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page
from .utils import cargar_terminos_busqueda, crear_contexto_navegador, configurar_navegador, navegar_a_reportes, navegar_siguiente_pagina, obtener_total_paginas, load_config, data_path, storage_state_path, notify
from .autentificacion import login
from .tipo_campo import field_type_label
import pandas as pd
import os
import threading
import tkinter as tk
from tkinter import messagebox
import tempfile
import uuid

archivo_busqueda = data_path("Lista_envio.xlsx")

def listar_hojas(archivo: str) -> list[str]:
	"""Devuelve la lista de hojas del archivo Excel."""
	with pd.ExcelFile(archivo, engine="openpyxl") as xls:
		return [str(n) for n in xls.sheet_names]

def _seleccionar_hoja_cli(archivo: str) -> str:
	"""Selector por consola (fallback)."""
	hojas = listar_hojas(archivo)
	if not hojas:
		raise ValueError("El archivo no contiene hojas.")
	if len(hojas) == 1:
		print(f"Usando única hoja: {hojas[0]}")
		return hojas[0]
	print("\nHojas disponibles en el Excel:")
	for i, h in enumerate(hojas, 1):
		print(f"  {i}) {h}")
	while True:
		op = input(f"Selecciona la hoja (1-{len(hojas)}) [1]: ").strip()
		if op == "":
			return hojas[0]
		if op.isdigit():
			idx = int(op)
			if 1 <= idx <= len(hojas):
				return hojas[idx - 1]
		print("Opción inválida. Intenta nuevamente.")

def _can_use_tk() -> bool:
	"""Tk solo en hilo principal."""
	return threading.current_thread() is threading.main_thread()

def seleccionar_hoja_tk(archivo: str, master=None):
	"""Ventana modal para elegir hoja. Devuelve nombre o None."""
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

	result = {"val": None}

	win = tk.Toplevel(master)
	win.title("Seleccionar hoja")
	win.resizable(False, False)
	win.grab_set()
	win.transient(master)
	# Ventana más amplia para nombres largos
	try:
		win.geometry("820x520")
	except Exception:
		pass

	tk.Label(win, text="Selecciona la hoja a usar:").pack(padx=12, pady=(12, 6), anchor="w")

	# Contenedor con scrollbars para ver nombres largos
	frame_lb = tk.Frame(win)
	frame_lb.pack(padx=12, fill="both", expand=True)
	frame_lb.rowconfigure(0, weight=1)
	frame_lb.columnconfigure(0, weight=1)

	lb = tk.Listbox(frame_lb, height=min(14, len(hojas)), exportselection=False)
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
			idx = lb.curselection()[0]
			result["val"] = hojas[idx]
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

def seleccionar_hoja(archivo: str) -> str:
	"""Intenta UI; si no, cae a CLI."""
	if _can_use_tk():
		sel = seleccionar_hoja_tk(archivo)
		if sel:
			return sel
	return _seleccionar_hoja_cli(archivo)

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

def main(nombre_hoja: str | None = None):
	config = load_config()
	url = config.get("url", "")
	url_base = config.get("url_base", "")
	extraccion_oculta = bool(config.get("headless", False))
	hoja_seleccionada = nombre_hoja or seleccionar_hoja(archivo_busqueda)
	campos, segunda_fila = cargar_columnas(archivo_busqueda, hoja_seleccionada)

	nombre_lista = campos[0]
	# Ejemplo de uso: mostrar valor de ejemplo para cada columna a mapear
	# for indice, columna in enumerate(campos[2:], start=2):
	# 	valor_ejemplo = segunda_fila[indice - 1] if indice - 1 < len(segunda_fila) else ""
	# 	print(f"Columna {indice}: {columna} | Ejemplo: {valor_ejemplo}")

	tmp_subida: str | None = None
	with sync_playwright() as p:
		browser = configurar_navegador(p, extraccion_oculta)
		context = crear_contexto_navegador(browser, extraccion_oculta)
		
		page = context.new_page()
		
		page.goto(url_base, wait_until="domcontentloaded", timeout=30000)
		page.goto(url, wait_until="domcontentloaded", timeout=60000)
		
		login(page)
		context.storage_state(path=storage_state_path())

		inicializar_navegacion_lista(page)

		page.wait_for_load_state("networkidle")
		
		btn_nueva_lista = page.locator('a:has-text("Nueva Lista"):visible')

		btn_nueva_lista.click()

		page.wait_for_load_state("networkidle")

		input_nombre_lista = page.locator('input#name')
		input_nombre_lista.fill(nombre_lista)
		# ahora = datetime.now()
		# fecha_texto = ahora.strftime("%Y%m%d")
		# input_nombre_lista.fill(f"{nombre_lista}_{fecha_texto}")

		btn_crear_lista = page.locator('input:visible', has_text="Crear")
		btn_crear_lista.click()

		btn_agregar_suscriptores = page.locator('a#add-subscribers-link')
		btn_agregar_suscriptores.click()

		page.wait_for_load_state("networkidle")

		page.get_by_label("Archivo CSV/Excel").check()

		# Generar archivo temporal solo con la hoja seleccionada
		tmp_subida = _generar_archivo_subida_desde_hoja(archivo_busqueda, hoja_seleccionada)
		input_archivo = page.locator('input#id_csv')
		input_archivo.set_input_files(tmp_subida)

		btn_aniadir = page.locator('a:visible', has_text="Añadir")
		btn_aniadir.click()

		page.wait_for_load_state("networkidle")

		try:
			btn_close_poup = page.locator('a', has_text="Aceptar")
			btn_close_poup.click()
		except PWTimeoutError:
			print("No se mostró popup de error")
		
		for indice, columna in enumerate(campos[2:], start=2):
			# print(f"Columna {indice}: {columna}")
			# Si quieres usar el valor ejemplo:
			# valor_ejemplo = segunda_fila[indice - 1] if indice - 1 < len(segunda_fila) else ""
			# print(f"  Ejemplo: {valor_ejemplo}")
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
			btn_aniadir.click()
		
		btn_siguiente = page.locator('a:visible', has_text="Siguiente")
		btn_siguiente.click()

		try:
			# Esperar a que aparezca el mensaje de éxito
			page.wait_for_selector('text="Tus suscriptores se han importado con éxito"', timeout=30000)
			print("Suscriptores importados con éxito")
		except PWTimeoutError:
			print("No se pudo confirmar la importación de suscriptores")

		page.wait_for_load_state("networkidle")
		
		browser.close()
		notify("Proceso finalizado", f"Lista '{nombre_lista}' cargada")
	# Limpiar archivo temporal
	try:
		if tmp_subida and os.path.exists(tmp_subida):
			os.remove(tmp_subida)
	except Exception:
		pass

if __name__ == "__main__":
	main()