"""
Infrastructure Excel utilities.

Provides Excel file management for scraping operations.
"""
from .excel_manager import ExcelManager
from .excel_utils import (
    crear_o_cargar_libro_excel,
    obtener_o_crear_hoja,
    agregar_datos,
    crear_hoja_con_datos,
)


class ExcelHelper:
    """Clase helper para operaciones Excel comunes (re-exportado para compatibilidad)."""
    import os as _os
    import pandas as _pd

    @staticmethod
    def leer_excel(archivo, hoja=None):
        if not ExcelHelper._os.path.exists(archivo):
            return ExcelHelper._pd.DataFrame()
        if hoja:
            return ExcelHelper._pd.read_excel(archivo, sheet_name=hoja, engine="openpyxl")
        return ExcelHelper._pd.read_excel(archivo, engine="openpyxl")

    @staticmethod
    def escribir_excel(df, archivo, hoja="Sheet1", reemplazar=True):
        ExcelHelper._os.makedirs(ExcelHelper._os.path.dirname(archivo), exist_ok=True)
        if reemplazar or not ExcelHelper._os.path.exists(archivo):
            df.to_excel(archivo, sheet_name=hoja, index=False, engine="openpyxl")
        else:
            with ExcelHelper._pd.ExcelWriter(archivo, mode='a', engine="openpyxl", if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name=hoja, index=False)
        return True

    @staticmethod
    def obtener_hojas(archivo):
        try:
            if not ExcelHelper._os.path.exists(archivo):
                return []
            return ExcelHelper._pd.ExcelFile(archivo, engine="openpyxl").sheet_names
        except Exception:
            return []

    @staticmethod
    def verificar_columnas(df, columnas_requeridas):
        faltantes = list(set(columnas_requeridas) - set(df.columns))
        return len(faltantes) == 0, faltantes


__all__ = [
    "ExcelManager",
    "ExcelHelper",
    "crear_o_cargar_libro_excel",
    "obtener_o_crear_hoja",
    "agregar_datos",
    "crear_hoja_con_datos",
]