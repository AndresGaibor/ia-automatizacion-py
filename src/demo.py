from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError, Page
import yaml
from openpyxl import Workbook, load_workbook
import pandas as pd
import time



REAL_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


with open('config.yaml', 'r') as file:
	config = yaml.safe_load(file)

username = config["user"]
password = config["password"]
url = config["url"]
archivo_busqueda = config["archivo_busqueda"]
archivo_informes = config["archivo_informes"]

terminos = []
df = pd.read_excel(archivo_busqueda, engine="openpyxl")

# Mostrar contenido
print(df)

# Acceder a una columna
print(df["Informes"])

# Iterar por filas
for index, row in df.iterrows():
	terminos.append(row['Informes'])



def login(page: Page):
	# page.wait_for_load_state("domcontentloaded")

	if(page.url != url):
		print("no es igual")
		try:
			page.get_by_role("button", name="Aceptar todas").click();
		except PWTimeoutError:
			pass

		page.get_by_role("link", name="Entra").click()

		page.get_by_label("Correo electrónico").fill(username)
		page.get_by_label("Contraseña").fill(password)

		# <input type="submit" value="Entrar" class="g-recaptcha signup-button" id="login-button" data-sitekey="6LeOaagZAAAAADEGihAZSe2cFNNTWgxfUM5NET9Z" data-callback="onSubmit" data-action="submit">
		with page.expect_navigation(wait_until="domcontentloaded"):
			page.get_by_role("button", name="Entrar").click()
	
	try:
		page.wait_for_selector("a[href*='/reports']", timeout=10000)
		print("Login OK")
	except PWTimeoutError:
			print("Parece que no se completó el login (¿captcha?).")
			print("Resuelve el captcha manualmente en la ventana y presiona Enter aquí…")
			input()
            # Espera a que aparezca el enlace a informes
			page.wait_for_selector("a[href*='/reports']", timeout=20000)

	

def main():
	with sync_playwright() as p:
		browser = p.chromium.launch(
			headless=False,
			# slow_mo=120,
			args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
			) # headless=False para ver
		context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=REAL_UA,
            locale="es-ES",
            timezone_id="Europe/Madrid",
            ignore_https_errors=True,
			storage_state="data/storage_state.json"
        )
		
		context.set_default_timeout(30000)
		context.set_default_navigation_timeout(120000)
		page = context.new_page()
		page.goto(url)
		
		login(page)
		context.storage_state(path="data/storage_state.json")

		# page.get_by_role("link", name="Entra2").click()

		informe_detalle: list[list[str]] = []
		informe_detallado: list[list[str]] = []
		# <input placeholder="Buscar informe" type="text" 
		# name="search_word" class="height-32 bordered 
		# bg-color-white-1 border-radius-03 padding-left-32 padding-right-32 font-size-13 font-color-darkblue-1 line-height-20" value="">
		buscador = page.get_by_placeholder("Buscar informe");
		for termino in terminos:
			page.click("a[href*='/reports']")

			buscador.fill("");
			buscador.fill(termino)
			page.keyboard.press("Enter")

			tabla_reporte = page.locator('#newsletter-reports')

			tabla_reporte.locator("a").first.wait_for(timeout=10000)

			td = tabla_reporte.locator('li').nth(1)

			divs = td.locator('div')

			nombre = divs.nth(0)
			nombre_txt = nombre.nth(0).inner_text()
			tipo = divs.nth(1).inner_text()
			fecha_envio = divs.nth(2).inner_text()
			listas = divs.nth(3).inner_text()
			emails = divs.nth(4).inner_text()
			abiertos = divs.nth(5).inner_text()
			clics = divs.nth(6).inner_text()

			informe_detalle.append([
				nombre_txt, tipo, fecha_envio, listas, emails, abiertos, clics
			])

			nombre.locator('a').click()
			page.wait_for_load_state("networkidle")
			page.get_by_role('link', name="Detalles suscriptores").click()

			tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))

			suscriptores = tabla_suscriptores.locator('li')

			count = suscriptores.count()

			for i in range(1, count):  # empieza en 1 → segundo elemento
				datos_suscriptor = suscriptores.nth(i).locator('div')

				correo = datos_suscriptor.nth(0).inner_text()
				fecha_apertura = datos_suscriptor.nth(1).inner_text()
				pais_apertura = datos_suscriptor.nth(2).inner_text()
				aperturas = datos_suscriptor.nth(3).inner_text()
				lista = datos_suscriptor.nth(4).inner_text()
				estado = datos_suscriptor.nth(5).inner_text()
				calidad = datos_suscriptor.nth(6).inner_text()

				informe_detallado.append([
					nombre_txt, correo, fecha_apertura, pais_apertura, aperturas, lista, estado, calidad
				])

			# <a class="font-size-13 transition-02 line-height-18 display-block font-color-grey-3 font-weight-400" href="/report/campaign/3331731/url/" onclick="trackAmplitudeEvent(&quot;campaign report item clicked&quot;, {&quot;item&quot;: &quot;url tracking&quot;})">Seguimiento url's</a>
			page.get_by_role('link', name="Seguimiento url's").click()

			# Click en el botón de los tres puntos (ícono)
			# page.locator('div.dropleft >> div.dropdown-toggle').click()
			fil = page.locator('ul').filter(has=page.locator("span", has_text="Han hecho clic"))
			# print(fil.inner_html())
			prueb = fil.locator('li').nth(1)
			# print(prueb.inner_html())
			prueb2 = prueb.locator('div.dropleft')
			# print(prueb2.inner_html())
			prueb2.click()
			# <div aria-expanded="true" aria-haspopup="true" class="dropdown-toggle am-button squared height-32 bg-color-white-1 transition-02" data-toggle="dropdown">
            #       <a class="font-color-grey-3 font-size-13 font-weight-400 transition-02 font-align-center cursor-pointer">
            #           <i class="am-icon am-icon-16 am-icon-more display-block position-relative"></i>
            #       </a>
            #   </div>

			# time.sleep(5)

			# <a class="font-size-13 font-weight-400 font-color-grey-3 line-height-32 display-inline-block width-100 padding-left-20 padding-right-20 transition-02" href="/report/campaign/click/837253076/details/">Detalles</a>
			prueb.get_by_role('link', name="Detalles").click()
			# page.locator('a:has-text("Detalles")').click()
			# page.locator('a[href^="/report/campaign/click/"][href$="/details/"]').click()

		# 	<span class="font-size-11 font-weight-400 line-height-18 font-color-grey-3 font-uppercase">
        #     Suscriptores que han hecho clic
        # </span>
			tabla_clics = page.locator('ul').filter(has=page.locator("span", has_text="Suscriptores que han hecho clic"))
			
			# print(tabla_clics.inner_html())

			clics = tabla_clics.locator('li')

			count3 = clics.count()

			for k in range(1, count3):  # empieza en 1 → segundo elemento
				email = clics.nth(k).inner_text()
				for detalle in informe_detallado:
					print(f"Correo es {email} {detalle[1]}")
					if detalle[1].strip() == email.strip():
						# Remove existing "si" if present to avoid duplicates
						if len(detalle) == 9:
							detalle.pop()
						detalle.append("si")
					elif len(detalle) < 9:
						# Add empty string for non-matching emails
						detalle.append("")

			# for suscriptor in range(s):
			print("Haciendo clic para volver a la paginas de reportes")
			page.get_by_role('link', name='Emails').click()
			# page.get_by_role('link', name='Informes')
			# page.click("a[href*='/reports']")


		# Crear un libro y una hoja
		wb = Workbook()
		ws = wb.active
		if ws is not None:
			ws.title = "Hoja1"
		else:
			ws = wb.create_sheet(title="Hoja1")
		


		# Escribir datos
		ws['A1'] = "Nombre"
		ws['B1'] = "Tipo"
		ws['C1'] = "Fecha envio"
		ws['D1'] = "Listas"
		ws['E1'] = "Emails"
		ws['F1'] = "Abiertos"
		ws['G1'] = "Clics"

		for fila in informe_detalle:
			ws.append(fila)
		
		ws = wb.create_sheet(title="Hoja2")

		ws['A1'] = "Proyecto"
		ws['B1'] = "Correo"
		ws['C1'] = "Fecha apertura"
		ws['D1'] = "Pais apertura"
		ws['E1'] = "Aperturas"
		ws['F1'] = "Lista"
		ws['G1'] = "Estado"
		ws['H1'] = "Calidad"
		ws['I1'] = "Seguimiento url"

		for fila in informe_detallado:
			print(fila)
			ws.append(fila)
			
		# ws.append(["Luis", 30])

		# Guardar archivo
		wb.save(archivo_informes)

		browser.close()
if __name__ == "__main__":
	main()