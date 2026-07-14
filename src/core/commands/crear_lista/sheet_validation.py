"""Validación de hojas Excel y selección de archivos."""

import os
import tkinter as tk
from tkinter import filedialog
from typing import Dict, Any, Optional

from ....utils import data_path
from ....infrastructure.excel import ExcelHelper
from ....shared.logging.logger import get_logger


def seleccionar_archivo_excel(directorio_inicial: str = None) -> Optional[str]:
    """
    Abre diálogo para seleccionar archivo Excel
    """
    root = tk.Tk()
    root.withdraw()

    if not directorio_inicial:
        directorio_inicial = data_path("listas")

    archivo = filedialog.askopenfilename(
        title="Seleccionar archivo Excel",
        initialdir=directorio_inicial,
        filetypes=[
            ("Archivos Excel", "*.xlsx"),
            ("Archivos Excel antiguos", "*.xls"),
            ("Todos los archivos", "*.*")
        ]
    )

    root.destroy()
    return archivo if archivo else None


def validar_diferencias_hojas(archivo: str) -> Dict[str, Any]:
    """
    Valida diferencias entre hojas "Datos" y "Cambios"

    Returns:
        Dict con información de validación:
        - tiene_datos: bool
        - tiene_cambios: bool
        - emails_solo_datos: Set[str]
        - emails_solo_cambios: Set[str]
        - es_problematico: bool
        - mensaje: str
    """
    logger = get_logger()
    resultado = {
        'tiene_datos': False,
        'tiene_cambios': False,
        'emails_solo_datos': set(),
        'emails_solo_cambios': set(),
        'es_problematico': False,
        'mensaje': ''
    }

    try:
        hojas = ExcelHelper.obtener_hojas(archivo)

        resultado['tiene_datos'] = 'Datos' in hojas
        resultado['tiene_cambios'] = 'Cambios' in hojas

        if not resultado['tiene_datos']:
            resultado['mensaje'] = "❌ No se encontró la hoja 'Datos'"
            resultado['es_problematico'] = True
            return resultado

        if not resultado['tiene_cambios']:
            resultado['mensaje'] = "✅ Solo tiene hoja 'Datos' - Procesamiento normal"
            return resultado

        df_datos = ExcelHelper.leer_excel(archivo, 'Datos')
        df_cambios = ExcelHelper.leer_excel(archivo, 'Cambios')

        if 'email' not in df_datos.columns:
            resultado['mensaje'] = "❌ Hoja 'Datos' no tiene columna 'email'"
            resultado['es_problematico'] = True
            return resultado

        if 'email' not in df_cambios.columns:
            resultado['mensaje'] = "⚠️  Hoja 'Cambios' no tiene columna 'email'"
            return resultado

        emails_datos = set(df_datos['email'].dropna().astype(str))
        emails_cambios = set(df_cambios['email'].dropna().astype(str))

        resultado['emails_solo_datos'] = emails_datos - emails_cambios
        resultado['emails_solo_cambios'] = emails_cambios - emails_datos

        if len(resultado['emails_solo_cambios']) > 0:
            resultado['es_problematico'] = True
            resultado['mensaje'] = (
                f"🚨 PROBLEMA: La hoja 'Cambios' tiene {len(resultado['emails_solo_cambios'])} "
                f"emails que NO están en 'Datos'. Esto puede indicar inconsistencia."
            )
        else:
            resultado['mensaje'] = (
                f"✅ Validación OK: 'Cambios' es un subconjunto de 'Datos' "
                f"({len(emails_cambios)} de {len(emails_datos)} emails)"
            )

        logger.info(f"Validación hojas: Datos={len(emails_datos)}, Cambios={len(emails_cambios)}, "
                   f"Solo en Datos={len(resultado['emails_solo_datos'])}, "
                   f"Solo en Cambios={len(resultado['emails_solo_cambios'])}")

    except Exception as e:
        logger.error(f"Error validando hojas: {e}")
        resultado['mensaje'] = f"❌ Error validando hojas: {e}"
        resultado['es_problematico'] = True

    return resultado
