"""
Funciones utilitarias compartidas para automatización de Acumba
"""
from playwright.sync_api import Page, TimeoutError as PWTimeoutError
import pandas as pd
import json
import os

REAL_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

def cargar_terminos_busqueda(archivo_busqueda: str) -> list[list[str]]:
    """
    Carga los términos de búsqueda desde el archivo Excel
    """
    terminos = []
    df = pd.read_excel(archivo_busqueda, engine="openpyxl")
    
    for index, row in df.iterrows():
        buscar = row['Buscar']
        if(buscar == 'x' or buscar == 'X'):
            terminos.append([row['Nombre'], row['Listas']])
    
    return terminos

def crear_contexto_navegador(browser, extraccion_oculta: bool = False):
    """
    Crea y configura el contexto del navegador
    """
    storage_state_path = "data/storage_state.json"
    if not os.path.exists(storage_state_path):
        with open(storage_state_path, "w") as f:
            json.dump({}, f)
    
    context = browser.new_context(
        viewport={"width": 1400, "height": 900},
        user_agent=REAL_UA,
        locale="es-ES",
        timezone_id="Europe/Madrid",
        ignore_https_errors=True,
        storage_state=storage_state_path
    )
    
    return context

def configurar_navegador(p, extraccion_oculta: bool = False):
    """
    Configura y lanza el navegador
    """
    browser = p.chromium.launch(
        headless=extraccion_oculta,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    )
    return browser

def navegar_a_reportes(page: Page):
    """
    Navega a la sección de reportes
    """
    page.click("a[href*='/reports']")
    page.wait_for_load_state('networkidle')


def obtener_total_paginas(page: Page) -> int:
	"""
	Obtiene el número total de páginas de reportes
	"""
	try:
		items_por_pagina = page.locator('select').filter(has=page.locator('option', has_text="15"))
		# items_por_pagina.wait_for(timeout=2000)
		
		ultimo_option = items_por_pagina.locator('option').last
		value_ultimo_option = ultimo_option.get_attribute('value')
		items_por_pagina.select_option(value=value_ultimo_option)
		page.wait_for_load_state("networkidle")
	except Exception as e:
		print(f"No se encontro o hubo un error en la opcion de aumentar items por pagina")

	try:
		navegacion = page.locator('ul').filter(has=page.locator('li').locator('a', has_text="1")).last
		# navegacion.wait_for(timeout=2000)
		
		ultimo_elemento = navegacion.locator('li').last
		texto = ultimo_elemento.inner_text()
		
		if texto.isdigit():
			return int(texto)
		else:
			return 1
	except Exception as e:
		# print(f"No se pudo obtener el total de páginas: {e}")
		return 1

def navegar_siguiente_pagina(page: Page, pagina_actual: int) -> bool:
	"""
	Navega a la siguiente página si existe
	"""
	siguiente_pagina = pagina_actual + 1
	
	try:
		navegacion = page.locator('ul').filter(
			has=page.locator('li').locator('a', has_text=f"{siguiente_pagina}")
		).last
		
		enlace = navegacion.locator('a', has_text=f"{siguiente_pagina}").first
		
		if enlace.count() > 0:
			enlace.click()
			page.wait_for_load_state("networkidle")
			return True
		else:
			return False
			
	except Exception as e:
		print(f"⚠️ Advertencia al navegar a la página {siguiente_pagina}: {e}")
		# print(f"No se pudo navegar a la página {siguiente_pagina}")
		return False

