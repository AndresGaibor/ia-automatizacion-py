from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from typing import Optional

def crear_o_cargar_libro_excel(archivo: str) -> Workbook:
    """
    Carga un libro Excel existente o crea uno nuevo si no existe.
    """
    try:
        return load_workbook(archivo)
    except FileNotFoundError:
        return Workbook()

def obtener_o_crear_hoja(libro: Workbook, nombre_hoja: str, encabezados: Optional[list[str]] = None) -> Worksheet:
    """
    Obtiene una hoja existente o crea una nueva con los encabezados especificados.
    """
    try:
        ws = libro[nombre_hoja]
    except KeyError:
        ws = libro.create_sheet(title=nombre_hoja)
        if encabezados:
            agregar_encabezados(ws, encabezados)
    return ws

def agregar_encabezados(hoja: Worksheet, encabezados: list[str]) -> None:
    """
    Agrega encabezados a una hoja de Excel.
    """
    for col_idx, encabezado in enumerate(encabezados, 1):
        hoja.cell(row=1, column=col_idx, value=encabezado)

def limpiar_hoja_desde_fila(hoja: Worksheet, fila_inicial: int = 2) -> None:
    """
    Elimina todas las filas desde la fila especificada hasta el final.
    """
    max_row = hoja.max_row
    if max_row >= fila_inicial:
        hoja.delete_rows(fila_inicial, max_row - fila_inicial + 1)

def agregar_datos(hoja: Worksheet, datos: list[list[str]]) -> int:
    """
    Agrega datos a una hoja y retorna el número de registros agregados.
    """
    registros_agregados = 0
    for fila in datos:
        if any(fila):  # Solo agregar filas con datos
            hoja.append(fila)
            registros_agregados += 1
    return registros_agregados

def crear_hoja_con_datos(wb: Workbook, nombre_hoja: str, datos: list[list[str]], encabezados: list[str]) -> None:
    """
    Crea una hoja con encabezados y datos específicos.
    """
    ws = wb.create_sheet(title=nombre_hoja)
    agregar_encabezados(ws, encabezados)
    agregar_datos(ws, datos)
