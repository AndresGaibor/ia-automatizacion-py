"""Gestión del cache local de IDs de listas."""
import os
from typing import Optional

from ..utils import data_path
from ..logger import get_logger
from ..crear_lista_mejorado import extraer_id_desde_nombre_archivo

logger = get_logger()

ARCHIVO_SEGMENTOS = data_path("Segmentos.xlsx")
CARPETA_LISTAS = data_path("listas")


def obtener_id_lista_desde_archivo(nombre_lista: str) -> Optional[int]:
    if not os.path.exists(CARPETA_LISTAS):
        return None

    for archivo in os.listdir(CARPETA_LISTAS):
        if archivo.endswith('.xlsx'):
            archivo_sin_extension = os.path.splitext(archivo)[0]
            if archivo_sin_extension.startswith(nombre_lista + '-ID-'):
                list_id = extraer_id_desde_nombre_archivo(archivo)
                if list_id is not None:
                    logger.info(f"ID encontrado para lista '{nombre_lista}': {list_id}")
                    return list_id
            elif archivo_sin_extension == nombre_lista:
                logger.info(f"Archivo encontrado para lista '{nombre_lista}' pero sin ID")
                return None

    logger.info(f"No se encontró archivo para lista '{nombre_lista}'")
    return None


def asegurar_nombre_archivo_con_id(nombre_lista: str, list_id: int) -> str:
    ruta_base = os.path.join(CARPETA_LISTAS, nombre_lista)
    ruta_con_id = os.path.join(CARPETA_LISTAS, f"{nombre_lista}-ID-{list_id}.xlsx")
    ruta_sin_id = f"{ruta_base}.xlsx"

    if os.path.exists(ruta_con_id):
        return ruta_con_id

    if os.path.exists(ruta_sin_id):
        try:
            os.rename(ruta_sin_id, ruta_con_id)
            logger.info(f"Archivo renombrado: '{ruta_sin_id}' → '{ruta_con_id}'")
            return ruta_con_id
        except Exception as e:
            logger.warning(f"Error renombrando archivo: {e}")
            return ruta_sin_id

    return ruta_con_id


def actualizar_id_en_segmentos(nombre_lista: str, list_id: int) -> bool:
    import pandas as pd
    try:
        if not os.path.exists(ARCHIVO_SEGMENTOS):
            return False

        df = pd.read_excel(ARCHIVO_SEGMENTOS)
        mask = df['NOMBRE LISTA'] == nombre_lista
        if mask.any():
            df.loc[mask, 'ID Lista'] = list_id
            df.to_excel(ARCHIVO_SEGMENTOS, index=False)
            logger.info(f"ID {list_id} actualizado en Segmentos.xlsx para lista '{nombre_lista}'")
            return True

        logger.info(f"Lista '{nombre_lista}' no encontrada en Segmentos.xlsx")
        return False
    except Exception as e:
        logger.error(f"Error actualizando ID en Segmentos.xlsx: {e}")
        return False


def obtener_id_desde_segmentos(nombre_lista: str) -> Optional[int]:
    import pandas as pd
    try:
        if not os.path.exists(ARCHIVO_SEGMENTOS):
            return None

        df = pd.read_excel(ARCHIVO_SEGMENTOS)
        mask = df['NOMBRE LISTA'] == nombre_lista
        if mask.any():
            id_valor = df.loc[mask, 'ID Lista'].iloc[0]
            return int(id_valor) if pd.notna(id_valor) else None

        return None
    except Exception as e:
        logger.error(f"Error obteniendo ID desde Segmentos.xlsx: {e}")
        return None


def obtener_o_buscar_id_lista(nombre_lista: str) -> Optional[int]:
    list_id = obtener_id_lista_desde_archivo(nombre_lista)
    if list_id is not None:
        return list_id
    return obtener_id_desde_segmentos(nombre_lista)


def obtener_ruta_archivo_lista(nombre_lista: str) -> str:
    os.makedirs(CARPETA_LISTAS, exist_ok=True)
    nombre_archivo = f"{nombre_lista}.xlsx"
    return os.path.join(CARPETA_LISTAS, nombre_archivo)
