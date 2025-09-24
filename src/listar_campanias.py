import sys
from pathlib import Path

# Agregar el directorio raíz al path cuando se ejecuta directamente
if __name__ == "__main__":
    # Obtener el directorio raíz del proyecto (padre de src)
    current_dir = Path(__file__).parent
    root_dir = current_dir.parent
    sys.path.insert(0, str(root_dir))

# Imports que funcionan tanto ejecutando directamente como módulo
try:
    # Cuando se ejecuta como módulo del paquete
    from .excel_utils import agregar_datos, crear_o_cargar_libro_excel, limpiar_hoja_desde_fila, obtener_o_crear_hoja
    from .api import API
    from .utils import data_path, notify
except ImportError:
    # Cuando se ejecuta directamente
    from src.excel_utils import agregar_datos, crear_o_cargar_libro_excel, limpiar_hoja_desde_fila, obtener_o_crear_hoja
    from src.api import API
    from src.utils import data_path, notify

# Rutas
ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")

def guardar_datos_en_excel(informe_detalle: list[list[str]], archivo_busqueda: str):
    """
    Guarda los datos en el archivo Excel, usando la primera hoja por defecto
    y ajusta automáticamente el ancho de las columnas
    """
    try:
        wb = crear_o_cargar_libro_excel(archivo_busqueda)
        encabezados = ["Buscar", "Nombre", "ID Campaña", "Fecha", "Total enviado", "Abierto", "No abierto"]

        # Usar la primera hoja (Sheet) por defecto en lugar de crear "Campanias"
        if wb.worksheets:
            ws = wb.worksheets[0]  # Primera hoja
            ws.title = "Sheet"  # Asegurar que se llame Sheet
        else:
            ws = wb.create_sheet("Sheet")

        # Limpiar y agregar encabezados
        ws.delete_rows(1, ws.max_row)
        ws.append(encabezados)

        registros_agregados = agregar_datos(ws, datos= informe_detalle)

        # Ajustar automáticamente el ancho de las columnas
        from openpyxl.utils import get_column_letter
        
        # Iterar por cada columna usando índices
        for col_idx in range(1, ws.max_column + 1):
            max_length = 0
            column_letter = get_column_letter(col_idx)
            
            # Revisar todas las celdas de esta columna
            for row_idx in range(1, ws.max_row + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            # Ajustar el ancho (agregar un poco de padding)
            adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres
            ws.column_dimensions[column_letter].width = adjusted_width

        wb.save(archivo_busqueda)
        print(f"Se agregaron {registros_agregados} registros al archivo {archivo_busqueda}")
        print("✅ Columnas ajustadas automáticamente")

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

		# Filtrar campañas válidas
		from datetime import datetime, timedelta
		hoy = datetime.now().strftime("%Y%m%d")

		for campania in campanias:
			nombre = campania.name
			id = str(campania.id)
			fecha = campania.date
			total_enviado = str(campania.total_delivered)
			abierto = str(campania.opened)
			no_abierto = str(campania.unopened)

			# Filtrar campañas de prueba o del mismo día (pueden estar incompletas)
			if (nombre and
				hoy not in nombre and  # Excluir campañas del día actual
				total_enviado != "0"):  # Excluir campañas sin envíos
				informe.append(['', nombre, id, fecha, total_enviado, abierto, no_abierto])
		
		if informe:
			guardar_datos_en_excel(informe, ARCHIVO_BUSQUEDA)

	except Exception as e:
		print(f"Error crítico en el programa: {e}")
		raise

if __name__ == "__main__":
	main()