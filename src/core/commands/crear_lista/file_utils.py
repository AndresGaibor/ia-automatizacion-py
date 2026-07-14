"""Utilidades de archivos: extracción de IDs, nombres y renombrado."""

import os
import re
import shutil
from pathlib import Path
from typing import Optional

from ....shared.logging.logger import get_logger


def extraer_id_desde_nombre_archivo(nombre_archivo: str) -> Optional[int]:
    """
    Extrae el ID de lista desde el nombre del archivo con formato -ID-[numero].xlsx

    Args:
        nombre_archivo: Nombre del archivo (ej: "MiLista-ID-12345.xlsx")

    Returns:
        ID de la lista como entero o None si no se encuentra
    """
    patron = r'-ID-(\d+)(?:_\d+)?\.xlsx?$'
    match = re.search(patron, nombre_archivo, re.IGNORECASE)

    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    return None


def tiene_formato_id_existente(archivo: str) -> bool:
    """
    Verifica si el archivo tiene formato de ID existente

    Args:
        archivo: Ruta completa del archivo

    Returns:
        True si tiene formato -ID-[numero].xlsx
    """
    nombre_archivo = os.path.basename(archivo)
    return extraer_id_desde_nombre_archivo(nombre_archivo) is not None


def obtener_nombre_lista_desde_archivo(archivo: str) -> str:
    """
    Obtiene el nombre de la lista basado en el nombre del archivo
    """
    nombre_base = Path(archivo).stem

    caracteres_permitidos = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_. "
    nombre_limpio = "".join(c for c in nombre_base if c in caracteres_permitidos)

    if len(nombre_limpio) > 50:
        nombre_limpio = nombre_limpio[:47] + "..."

    return nombre_limpio.strip()


def renombrar_archivo_con_id(archivo_original: str, nombre_lista: str, list_id: int) -> bool:
    """
    Renombra el archivo original con el formato [Nombre de lista]-ID-[ID_LISTA].xlsx

    Args:
        archivo_original: Ruta del archivo original
        nombre_lista: Nombre de la lista creada
        list_id: ID de la lista asignado por la API

    Returns:
        bool: True si se renombró exitosamente
    """
    logger = get_logger()

    try:
        archivo_path = Path(archivo_original)
        directorio = archivo_path.parent
        extension = archivo_path.suffix

        nuevo_nombre = f"{nombre_lista}-ID-{list_id}{extension}"
        nueva_ruta = directorio / nuevo_nombre

        if nueva_ruta.exists():
            print(f"⚠️  El archivo ya existe: {nuevo_nombre}")
            contador = 1
            while nueva_ruta.exists():
                nuevo_nombre = f"{nombre_lista}-ID-{list_id}_{contador}{extension}"
                nueva_ruta = directorio / nuevo_nombre
                contador += 1
            print(f"📝 Usando nombre alternativo: {nuevo_nombre}")

        shutil.move(str(archivo_path), str(nueva_ruta))

        print("✅ Archivo renombrado:")
        print(f"   Anterior: {archivo_path.name}")
        print(f"   Nuevo: {nuevo_nombre}")

        logger.info(f"Archivo renombrado: {archivo_path.name} -> {nuevo_nombre}")
        return True

    except Exception as e:
        logger.error(f"Error renombrando archivo: {e}")
        print(f"❌ Error renombrando archivo: {e}")
        return False
