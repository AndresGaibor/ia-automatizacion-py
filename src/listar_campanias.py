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
    from .logger import get_logger
except ImportError:
    # Cuando se ejecuta directamente
    from src.excel_utils import agregar_datos, crear_o_cargar_libro_excel, limpiar_hoja_desde_fila, obtener_o_crear_hoja
    from src.api import API
    from src.utils import data_path, notify
    from src.logger import get_logger

# Rutas
ARCHIVO_BUSQUEDA = data_path("Busqueda.xlsx")

logger = get_logger()

def guardar_datos_en_excel(informe_detalle: list[list[str]], archivo_busqueda: str):
    """
    Guarda los datos en el archivo Excel, usando la primera hoja por defecto
    y ajusta automáticamente el ancho de las columnas
    """
    try:
        logger.info("🚀 Iniciando guardado de datos en Excel", archivo=archivo_busqueda, registros=len(informe_detalle))
        
        wb = crear_o_cargar_libro_excel(archivo_busqueda)
        encabezados = ["Buscar", "Nombre", "ID Campaña", "Fecha", "Total enviado", "Abierto", "No abierto"]

        # Usar la primera hoja (Sheet) por defecto en lugar de crear "Campanias"
        if wb.worksheets:
            ws = wb.worksheets[0]  # Primera hoja
            ws.title = "Sheet"  # Asegurar que se llame Sheet
            logger.info("📝 Usando hoja existente", titulo_hoja=ws.title)
        else:
            ws = wb.create_sheet("Sheet")
            logger.info("🆕 Creando nueva hoja", titulo_hoja=ws.title)

        # Limpiar y agregar encabezados
        logger.info("🧹 Limpiando hoja y agregando encabezados")
        ws.delete_rows(1, ws.max_row)
        ws.append(encabezados)

        registros_agregados = agregar_datos(ws, datos= informe_detalle)
        logger.info("📊 Datos agregados", registros_agregados=registros_agregados)

        # Ajustar automáticamente el ancho de las columnas
        from openpyxl.utils import get_column_letter
        
        # Iterar por cada columna usando índices
        logger.info("📐 Ajustando ancho de columnas")
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
        logger.success("✅ Archivo guardado exitosamente", archivo=archivo_busqueda, registros_agregados=registros_agregados)
        logger.info(f"Se agregaron {registros_agregados} registros al archivo {archivo_busqueda}")
        logger.info("✅ Columnas ajustadas automáticamente")

    except Exception as e:
        logger.error("❌ Error guardando archivo Excel", error=str(e))
        print(f"Error guardando archivo Excel: {e}")

api = API()

def main():
	"""
	Función principal del programa de listado de campañas
	"""

	try:
		logger.info("🚀 Iniciando programa de listado de campañas")
		
		informe: list[list[str]] = []
		logger.info("🌐 Obteniendo campañas desde la API")
		campanias = api.campaigns.get_all(True)
		logger.info("📥 Campañas obtenidas", total_campañas=len(campanias))

		# Filtrar campañas válidas
		from datetime import datetime, timedelta
		hoy = datetime.now().strftime("%Y%m%d")
		logger.info("筛选_filtros_aplicados", fecha_actual=hoy)

		campanias_filtradas = 0
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
				campanias_filtradas += 1
		
		logger.info("📊 Filtrado completado", campañas_filtradas=campanias_filtradas, campañas_para_guardar=len(informe))
		
		if informe:
			logger.info("💾 Guardando datos en archivo Excel")
			guardar_datos_en_excel(informe, ARCHIVO_BUSQUEDA)
			logger.success("✅ Programa completado exitosamente")
		else:
			logger.warning("⚠️ No hay datos para guardar después del filtrado")

	except Exception as e:
		logger.error("❌ Error crítico en el programa", error=str(e))
		print(f"Error crítico en el programa: {e}")
		raise

if __name__ == "__main__":
	main()