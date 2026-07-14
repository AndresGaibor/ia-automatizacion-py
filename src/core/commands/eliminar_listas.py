"""
Módulo para eliminar listas marcadas de Acumbamail
"""

import pandas as pd
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

from .utils import data_path
from .infrastructure.api import API
from .logger import get_logger


def validar_archivo_busqueda_listas() -> Tuple[bool, str, int]:
    """Valida el archivo de búsqueda de listas y cuenta elementos marcados"""
    archivo = data_path("Busqueda_Listas.xlsx")
    if not os.path.exists(archivo):
        return False, "Error: No existe el archivo Busqueda_Listas.xlsx", 0
    
    try:
        df = pd.read_excel(archivo)
        if 'Buscar' not in df.columns:
            return False, "Error: El archivo Busqueda_Listas.xlsx no tiene la columna 'Buscar'", 0
        
        marcados = df[df['Buscar'].isin(['x', 'X'])].shape[0]
        if marcados == 0:
            return False, "Advertencia: No hay listas marcadas con 'x' en el archivo Busqueda_Listas.xlsx", 0
        
        return True, f"{marcados} listas marcadas para procesar", marcados
    except Exception as e:
        return False, f"Error leyendo Busqueda_Listas.xlsx: {e}", 0


def eliminar_listas_marcadas() -> Tuple[List[int], List[Tuple[int, any, str]], str]:
    """
    Elimina las listas marcadas con 'x' en el archivo Excel
    
    Returns:
        Tuple con:
        - Lista de índices eliminados exitosamente
        - Lista de tuplas (índice, list_id, error) para las fallidas
        - Mensaje de resultado
    """
    logger = get_logger()
    
    # Validar archivo
    valid, message, marcadas = validar_archivo_busqueda_listas()
    if not valid:
        raise ValueError(message)
    
    archivo = data_path("Busqueda_Listas.xlsx")
    df = pd.read_excel(archivo)
    
    # Encontrar filas marcadas con 'x' en la columna 'Buscar'
    mask = df['Buscar'].astype(str).str.strip().str.lower().isin(['x'])
    indices = df[mask].index.tolist()
    
    if not indices:
        return [], [], "No hay listas marcadas para eliminar."
    
    logger.info(f"Eliminando {len(indices)} listas marcadas")
    
    # Preparar API
    api = API()
    exitosas = []
    fallidas = []
    
    try:
        for idx in indices:
            try:
                row = df.loc[idx]
                
                # Intentar obtener el ID de lista desde columnas comunes
                list_id = None
                for col in ['ID_LISTA', 'ID', 'ID LISTA', 'ID_LIST']:
                    if col in df.columns and pd.notna(row.get(col)):
                        list_id = row.get(col)
                        break
                
                # Fallback: usar la segunda columna si existe
                if list_id is None:
                    if len(df.columns) > 1:
                        list_id = row.iloc[1]
                
                if pd.isna(list_id) or str(list_id).strip() == '':
                    fallidas.append((idx, None, 'ID de lista no disponible'))
                    logger.warning(f"Fila {idx}: ID de lista no disponible")
                    continue
                
                try:
                    list_id_int = int(str(list_id).strip())
                except Exception:
                    fallidas.append((idx, list_id, 'ID inválido'))
                    logger.warning(f"Fila {idx}: ID inválido {list_id}")
                    continue
                
                # Llamar a la API para eliminar la lista
                try:
                    api.suscriptores.delete_list(list_id_int)
                    exitosas.append(idx)
                    logger.info(f"Lista {list_id_int} eliminada exitosamente")
                except Exception as e:
                    fallidas.append((idx, list_id_int, str(e)))
                    logger.error(f"Error eliminando lista {list_id_int}: {e}")
            
            except Exception as e:
                fallidas.append((idx, None, str(e)))
                logger.error(f"Error procesando fila {idx}: {e}")
    
    finally:
        # Cerrar cliente API
        try:
            api.close()
        except:
            pass
    
    # Eliminar filas que fueron eliminadas con éxito del Excel
    if exitosas:
        df = df.drop(index=exitosas)
        df.to_excel(archivo, index=False)
        logger.info(f"Actualizando Excel: eliminando {len(exitosas)} filas exitosas")
    
    # Preparar mensaje resumen
    mensaje = f"Eliminadas: {len(exitosas)}. Fallidas: {len(fallidas)}."
    if fallidas:
        mensaje += "\nErrores:"
        for f in fallidas[:5]:  # Mostrar solo las primeras 5
            mensaje += f"\n- Fila {f[0]}: ID {f[1]} - {f[2]}"
        if len(fallidas) > 5:
            mensaje += f"\n... y {len(fallidas) - 5} errores más."
    
    logger.info(f"Proceso completado: {mensaje}")
    
    return exitosas, fallidas, mensaje


def main():
    """Función principal para ejecutar desde línea de comandos"""
    try:
        exitosas, fallidas, mensaje = eliminar_listas_marcadas()
        print(f"✅ {mensaje}")
        return len(exitosas) > 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    main()