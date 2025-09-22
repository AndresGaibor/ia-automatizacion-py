from .api import API
from .utils import  data_path, notify

from openpyxl import Workbook, load_workbook

# Rutas
ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")

def guardar_datos_en_excel(informe_detalle: list[list[str]], archivo_busqueda: str):
	"""
	Guarda los datos en el archivo Excel, reemplazando desde la segunda fila
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
			ws.append(["Buscar", "Nombre", "ID Campaña", "Fecha", "Total enviado", "Abierto", "No abierto"])

		# Limpiar datos existentes desde la segunda fila
		if ws is not None:
			# Obtener el número máximo de filas con datos
			max_row = ws.max_row
			if max_row > 1:
				# Eliminar todas las filas desde la segunda hasta la última
				ws.delete_rows(2, max_row - 1)

		# Agregar nuevos datos
		registros_agregados = 0
		for fila in informe_detalle:
			if ws is not None and any(fila):  # Solo agregar filas con datos
				ws.append(fila)
				registros_agregados += 1

		wb.save(archivo_busqueda)

	except Exception as e:
		print(f"Error guardando archivo Excel: {e}")

api = API()

def main():
	"""
	Función principal del programa de listado de campañas
	"""

	try:
	
		informe2: list[list[str]] = []
		campanias = api.campaigns.get_all(True)

		for campania in campanias:
			informe2.append(['', campania.name, str(campania.id), campania.date, 
						str(campania.total_delivered), str(campania.opened), str(campania.unopened)
						])
		
		if informe2:
			guardar_datos_en_excel(informe2, ARCHIVO_BUSQUEDA)

		notify("Proceso finalizado", f"Lista de campañas obtenida")

	except Exception as e:
		print(f"Error crítico en el programa: {e}")
		raise

if __name__ == "__main__":
	main()