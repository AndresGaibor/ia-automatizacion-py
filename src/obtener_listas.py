from datetime import datetime
import pandas as pd
import os
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
    from .utils import data_path, notify
    from .api import API
    from .logger import get_logger
    from .excel_helper import ExcelHelper
except ImportError:
    # Cuando se ejecuta directamente
    from src.utils import data_path, notify
    from src.api import API
    from src.logger import get_logger
    from src.excel_helper import ExcelHelper

# Rutas
ARCHIVO_BUSQUEDA = data_path("Busqueda_Listas.xlsx")

def cargar_datos_existentes(archivo_busqueda: str) -> list[list[str]]:
	"""
	Carga los datos existentes del archivo Excel
	"""
	try:
		if not os.path.exists(archivo_busqueda):
			return []
		
		df = ExcelHelper.leer_excel(archivo_busqueda)
		
		if df.empty:
			return []
		
		# Convertir DataFrame a lista de listas
		datos = []
		for _, fila in df.iterrows():
			datos.append([str(val) if pd.notna(val) else '' for val in fila.values])
		
		return datos
		
	except Exception as e:
		logger = get_logger()
		logger.warning(f"Error cargando datos existentes: {e}")
		return []

def ordenar_por_fecha(fecha_str: str) -> tuple:
	"""
	Convierte fecha string a tupla para ordenamiento
	Fechas vacías van al final (más antiguas)
	"""
	if not fecha_str or str(fecha_str).strip() == '' or str(fecha_str).lower() == 'nan':
		# Sin fecha = más antigua (valor mínimo)
		return (0, 0, 0, 0, 0, 0)
	
	try:
		# Intentar parsear diferentes formatos de fecha
		fecha_str = str(fecha_str).strip()
		
		# Formato: 2024-09-16 10:30:00 o similar
		if len(fecha_str) >= 10:
			# Extraer año, mes, día, hora, minuto, segundo
			parts = fecha_str.replace('/', '-').replace(' ', '-').replace(':', '-').split('-')
			if len(parts) >= 3:
				year = int(parts[0]) if parts[0].isdigit() else 2000
				month = int(parts[1]) if parts[1].isdigit() else 1
				day = int(parts[2]) if parts[2].isdigit() else 1
				hour = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
				minute = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
				second = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0
				
				return (year, month, day, hour, minute, second)
	
	except (ValueError, IndexError):
		pass
	
	# Si no se puede parsear, tratarla como muy antigua
	return (0, 0, 0, 0, 0, 0)



def obtener_listas_via_api() -> list[list[str]]:
	"""
	Obtiene todas las listas usando la API de suscriptores de forma incremental
	"""
	informe_detalle = []
	logger = get_logger()
	
	try:
		# Cargar datos existentes del Excel
		datos_existentes = cargar_datos_existentes(ARCHIVO_BUSQUEDA)
		listas_existentes = {int(fila[1]): fila for fila in datos_existentes if fila[1] and str(fila[1]).isdigit()}
		
		api = API()
		listas = api.suscriptores.get_lists()
		
		print(f"Se encontraron {len(listas)} listas en la API")
		print(f"Ya existen {len(listas_existentes)} listas en el archivo Excel")
		
		listas_nuevas = []
		listas_sin_fecha = []
		
		for lista in listas:
			if lista.id in listas_existentes:
				# Lista ya existe, verificar si tiene fecha
				fila_existente = listas_existentes[lista.id]
				if not fila_existente[4] or str(fila_existente[4]).strip() == '':  # Sin fecha de creación
					listas_sin_fecha.append(lista)
				# Mantener la fila existente
				informe_detalle.append(fila_existente)
			else:
				# Lista nueva, necesita ser procesada
				listas_nuevas.append(lista)
		
		print(f"Listas nuevas encontradas: {len(listas_nuevas)}")
		print(f"Listas existentes sin fecha: {len(listas_sin_fecha)}")
		
		# Procesar solo las listas que necesitan get_list_stats
		listas_a_procesar = listas_nuevas + listas_sin_fecha
		
		if listas_a_procesar:
			print(f"Obteniendo detalles para {len(listas_a_procesar)} listas...")

			for i, lista in enumerate(listas_a_procesar):
				try:
					# Agregar delay conservador para evitar rate limit estricto
					if i > 0:  # No delay en la primera lista
						delay = 5  # 5 segundos fijos entre cada llamada para rate limit estricto
						print(f"Esperando {delay}s para evitar rate limit... ({i+1}/{len(listas_a_procesar)})")
						import time
						time.sleep(delay)

					print(f"Procesando lista {i+1}/{len(listas_a_procesar)}: {lista.name} (ID: {lista.id})")
					stats = api.suscriptores.get_list_stats(lista.id)
					# Formato: ['Buscar', 'ID_LISTA', 'NOMBRE LISTA', 'SUSCRIPTORES', 'CREACION']
					fila = [
						'',  # Buscar (columna vacía)
						str(lista.id),  # ID_LISTA
						lista.name,  # NOMBRE LISTA
						str(stats.total_subscribers) if hasattr(stats, 'total_subscribers') else '0',  # SUSCRIPTORES
						stats.create_date if hasattr(stats, 'create_date') else ''  # CREACION
					]
					
					# Si es una lista existente sin fecha, actualizar en lugar de agregar
					if lista.id in listas_existentes:
						# Encontrar y reemplazar en informe_detalle
						for i, fila_det in enumerate(informe_detalle):
							if fila_det[1] == str(lista.id):
								informe_detalle[i] = fila
								break
					else:
						# Lista nueva, agregar a las nuevas
						informe_detalle.append(fila)
					
				except Exception as e:
					error_str = str(e).lower()
					if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
						# Error de rate limit: esperar más tiempo y reintentar una vez
						print(f"⚠️ Rate limit detectado para lista {lista.id}. Esperando 60 segundos...")
						import time
						time.sleep(60)
						try:
							print(f"Reintentando lista {lista.id}: {lista.name}")
							stats = api.suscriptores.get_list_stats(lista.id)
							# Procesar stats exitosas después del reintento
							fila = [
								'',  # Buscar (columna vacía)
								str(lista.id),  # ID_LISTA
								lista.name,  # NOMBRE LISTA
								str(stats.total_subscribers) if hasattr(stats, 'total_subscribers') else '0',  # SUSCRIPTORES
								stats.create_date if hasattr(stats, 'create_date') else ''  # CREACION
							]

							if lista.id in listas_existentes:
								# Encontrar y reemplazar en informe_detalle
								for j, fila_det in enumerate(informe_detalle):
									if fila_det[1] == str(lista.id):
										informe_detalle[j] = fila
										break
							else:
								informe_detalle.append(fila)

							print(f"✅ Lista {lista.id} procesada exitosamente después del reintento")
							continue
						except Exception as e2:
							logger.warning(f"Error obteniendo stats para lista {lista.id} después del reintento: {e2}")
					else:
						logger.warning(f"Error obteniendo stats para lista {lista.id}: {e}")

					# Fallback sin estadísticas detalladas
					fila = ['', str(lista.id), lista.name, '0', '']

					if lista.id in listas_existentes:
						# Actualizar existente
						for j, fila_det in enumerate(informe_detalle):
							if fila_det[1] == str(lista.id):
								informe_detalle[j] = fila
								break
					else:
						informe_detalle.append(fila)
		
		# Ordenar por fecha de creación (más vieja primero, sin fecha al final)
		informe_detalle.sort(key=lambda x: ordenar_por_fecha(x[4]), reverse=False)
		
		logger.info(f"Obtenidas {len(informe_detalle)} listas via API ({len(listas_nuevas)} nuevas)")
		api.close()
		
	except Exception as e:
		logger.error(f"Error obteniendo listas via API: {e}")
		print(f"Error obteniendo listas via API: {e}")
		
	return informe_detalle

def guardar_datos_en_excel(informe_detalle: list[list[str]], archivo_busqueda: str):
	"""
	Guarda los datos en el archivo Excel usando ExcelHelper con las nuevas columnas
	y ajusta automáticamente el ancho de las columnas
	"""
	if not informe_detalle:
		print("No hay datos para guardar.")
		return

	try:
		# Crear DataFrame con los datos incluyendo ID_LISTA
		columnas = ["Buscar", "ID_LISTA", "NOMBRE LISTA", "SUSCRIPTORES", "CREACION"]
		df = pd.DataFrame(informe_detalle, columns=columnas)
		
		# Guardar con ajuste automático de columnas usando ExcelWriter
		with pd.ExcelWriter(archivo_busqueda, engine='openpyxl') as writer:
			df.to_excel(writer, sheet_name='Sheet1', index=False)
			
			# Ajustar automáticamente el ancho de las columnas
			worksheet = writer.sheets['Sheet1']
			
			for column in worksheet.columns:
				max_length = 0
				column_letter = column[0].column_letter
				
				for cell in column:
					try:
						# Calcular la longitud máxima del contenido
						if len(str(cell.value)) > max_length:
							max_length = len(str(cell.value))
					except:
						pass
				
				# Ajustar el ancho (agregar un poco de padding)
				adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres
				worksheet.column_dimensions[column_letter].width = adjusted_width
		
		print(f"Se guardaron {len(informe_detalle)} registros en {archivo_busqueda}")
		print("✅ Columnas ajustadas automáticamente")

	except Exception as e:
		logger = get_logger()
		logger.error(f"Error guardando archivo Excel: {e}")
		print(f"Error guardando archivo Excel: {e}")
		
		# Fallback: usar ExcelHelper tradicional
		try:
			df = pd.DataFrame(informe_detalle, columns=["Buscar", "ID_LISTA", "NOMBRE LISTA", "SUSCRIPTORES", "CREACION"])
			ExcelHelper.escribir_excel(df, archivo_busqueda, "Sheet1", reemplazar=True)
			print(f"Se guardaron {len(informe_detalle)} registros en {archivo_busqueda} (modo fallback)")
		except Exception as e2:
			print(f"Error en fallback: {e2}")

def main():
	"""
	Función principal del programa de listado de listas usando API
	"""
	logger = get_logger()
	
	try:
		# Obtener listas via API
		informe_detalle = obtener_listas_via_api()
		
		if informe_detalle:
			guardar_datos_en_excel(informe_detalle, ARCHIVO_BUSQUEDA)
			# notify("Proceso finalizado", f"Listas obtenidas via API: {len(informe_detalle)}")
			print(f"🎉 Proceso finalizado: Listas obtenidas via API: {len(informe_detalle)}")
		else:
			print("No se obtuvieron datos de listas")
			# notify("Proceso finalizado", "No se obtuvieron listas")
			print("⚠️ Proceso finalizado: No se obtuvieron listas")

	except Exception as e:
		logger.error(f"Error crítico en el programa: {e}")
		print(f"Error crítico en el programa: {e}")
		raise

if __name__ == "__main__":
	main()