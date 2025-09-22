from .excel_utils import agregar_datos, crear_o_cargar_libro_excel, limpiar_hoja_desde_fila, obtener_o_crear_hoja
from .api import API
from .utils import  data_path, notify

# Rutas
ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")

def guardar_datos_en_excel(informe_detalle: list[list[str]], archivo_busqueda: str):
    """
    Guarda los datos en el archivo Excel, reemplazando desde la segunda fila
    """
    try:
        wb = crear_o_cargar_libro_excel(archivo_busqueda)
        encabezados = ["Buscar", "Nombre", "ID Campaña", "Fecha", "Total enviado", "Abierto", "No abierto"]
        ws = obtener_o_crear_hoja(wb, "Campanias", encabezados)
        
        limpiar_hoja_desde_fila(ws, fila_inicial= 2)
        registros_agregados = agregar_datos(ws, datos= informe_detalle)
        
        wb.save(archivo_busqueda)
        print(f"Se agregaron {registros_agregados} registros al archivo {archivo_busqueda}")

    except Exception as e:
        print(f"Error guardando archivo Excel: {e}")

api = API()

def main():
	"""
	Función principal del programa de listado de campañas
	"""

	try:
		informe: list[list[str]] = []
		campanias = api.campaigns.get_all(True)

		for campania in campanias:
			nombre = campania.name
			id = str(campania.id)
			fecha = campania.date
			total_enviado = str(campania.total_delivered)
			abierto = str(campania.opened)
			no_abierto = str(campania.unopened)

			informe.append(['', nombre, id, fecha, total_enviado, abierto, no_abierto])
		
		if informe:
			guardar_datos_en_excel(informe, ARCHIVO_BUSQUEDA)

		notify("Proceso finalizado", f"Lista de campañas obtenida")

	except Exception as e:
		print(f"Error crítico en el programa: {e}")
		raise

if __name__ == "__main__":
	main()