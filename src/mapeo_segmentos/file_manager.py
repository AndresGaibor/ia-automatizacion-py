"""Gestión del archivo Excel de segmentos."""
import os
import pandas as pd
from collections import defaultdict
from typing import List, Tuple, Any

from ..utils import notify
from ..logger import get_logger
from ..excel_helper import ExcelHelper
from .id_manager import ARCHIVO_SEGMENTOS, obtener_o_buscar_id_lista

logger = get_logger()


def mostrar_estado_listas_segmentos() -> None:
    print("📊 Estado actual de listas en Segmentos.xlsx:")
    print("-" * 50)

    try:
        if not os.path.exists(ARCHIVO_SEGMENTOS):
            print("❌ Archivo Segmentos.xlsx no existe")
            return

        df = pd.read_excel(ARCHIVO_SEGMENTOS)

        if df.empty:
            print("📝 Archivo Segmentos.xlsx está vacío")
            return

        if 'NOMBRE LISTA' not in df.columns:
            print("❌ Columna 'NOMBRE LISTA' no encontrada")
            return

        listas_unicas = df['NOMBRE LISTA'].dropna().unique()

        for nombre_lista in listas_unicas:
            list_id = obtener_o_buscar_id_lista(nombre_lista)
            segmentos_count = len(df[df['NOMBRE LISTA'] == nombre_lista])

            if list_id:
                status = f"✅ ID: {list_id}"
            else:
                status = "❌ Sin ID"

            print(f"  {nombre_lista:<30} {status:<15} ({segmentos_count} segmentos)")

    except Exception as e:
        print(f"❌ Error mostrando estado: {e}")

    print("-" * 50)


def generar_datos_prueba_segmentos() -> pd.DataFrame:
    datos_ejemplo = [
        {
            'ID Lista': None, 'NOMBRE LISTA': 'Lista_Ejemplo_Madrid',
            'NOMBRE SEGMENTO': 'Juzgados_Madrid_Civil',
            'SEDE': 'Madrid', 'ORGANO': 'Juzgado Civil', 'N ORGANO': '1',
            'ROL USUARIO': 'Secretario', 'PERFIL USUARIO': 'Administrativo'
        },
        {
            'ID Lista': None, 'NOMBRE LISTA': 'Lista_Ejemplo_Madrid',
            'NOMBRE SEGMENTO': 'Juzgados_Madrid_Penal',
            'SEDE': 'Madrid', 'ORGANO': 'Juzgado Penal', 'N ORGANO': '2',
            'ROL USUARIO': 'Juez', 'PERFIL USUARIO': 'Judicial'
        },
        {
            'ID Lista': None, 'NOMBRE LISTA': 'Lista_Ejemplo_Barcelona',
            'NOMBRE SEGMENTO': 'Juzgados_Barcelona_Civil',
            'SEDE': 'Barcelona', 'ORGANO': 'Juzgado Civil', 'N ORGANO': '1',
            'ROL USUARIO': 'Secretario', 'PERFIL USUARIO': 'Administrativo'
        },
        {
            'ID Lista': None, 'NOMBRE LISTA': 'Lista_Ejemplo_Valencia',
            'NOMBRE SEGMENTO': 'Juzgados_Valencia_Mercantil',
            'SEDE': 'Valencia', 'ORGANO': 'Juzgado Mercantil', 'N ORGANO': '1',
            'ROL USUARIO': 'Letrado', 'PERFIL USUARIO': 'Legal'
        }
    ]
    return pd.DataFrame(datos_ejemplo)


def inicializar_archivo_segmentos() -> bool:
    try:
        if os.path.exists(ARCHIVO_SEGMENTOS):
            df = pd.read_excel(ARCHIVO_SEGMENTOS)

            if 'CREACION SEGMENTO' in df.columns:
                df = df.drop(columns=['CREACION SEGMENTO'])
                logger.info("Columna 'CREACION SEGMENTO' eliminada de Segmentos.xlsx")
                notify("Actualización", "Columna 'CREACION SEGMENTO' eliminada del archivo Segmentos.xlsx", "info")

            if 'ID Lista' not in df.columns:
                df.insert(0, 'ID Lista', None)
                logger.info("Columna 'ID Lista' agregada al archivo Segmentos.xlsx existente")
                notify("Actualización", "Columna 'ID Lista' agregada al archivo Segmentos.xlsx", "info")

            df.to_excel(ARCHIVO_SEGMENTOS, index=False)

            if len(df) == 0:
                logger.warning("Archivo Segmentos.xlsx existe pero está vacío")
                datos_prueba = generar_datos_prueba_segmentos()
                df = pd.concat([df, datos_prueba], ignore_index=True)
                df.to_excel(ARCHIVO_SEGMENTOS, index=False)
                notify("Datos de Prueba", "Archivo Segmentos.xlsx estaba vacío. Se agregaron datos de ejemplo.", "info")

            return True
        else:
            datos_prueba = generar_datos_prueba_segmentos()
            os.makedirs(os.path.dirname(ARCHIVO_SEGMENTOS), exist_ok=True)
            datos_prueba.to_excel(ARCHIVO_SEGMENTOS, index=False)
            logger.info(f"Archivo Segmentos.xlsx creado con datos de prueba en: {ARCHIVO_SEGMENTOS}")
            notify("Archivo Creado", f"Archivo Segmentos.xlsx creado con datos de ejemplo en: {ARCHIVO_SEGMENTOS}", "info")
            return True

    except Exception as e:
        logger.error(f"Error inicializando archivo Segmentos.xlsx: {e}")
        notify("Error", f"Error inicializando archivo Segmentos.xlsx: {e}", "error")
        return False


def procesar_excel_segmentos(archivo_excel: str) -> Tuple[List[str], List[List[Any]]]:
    logger.info(f"Procesando archivo de segmentos: {archivo_excel}")

    df = pd.read_excel(archivo_excel)

    if 'CREACION SEGMENTO' in df.columns:
        df = df.drop(columns=['CREACION SEGMENTO'])
        logger.info("Columna 'CREACION SEGMENTO' ignorada al procesar segmentos")

    if df.empty:
        logger.warning("Archivo de segmentos está vacío")
        return [], []

    headers = ['NOMBRE SEGMENTO', 'SEDE', 'ORGANO', 'N ORGANO', 'ROL USUARIO', 'PERFIL USUARIO']
    columnas_requeridas = ['NOMBRE LISTA', 'NOMBRE SEGMENTO']
    tiene_columnas, faltantes = ExcelHelper.verificar_columnas(df, columnas_requeridas)

    if not tiene_columnas:
        logger.error(f"Columnas requeridas faltantes: {faltantes}")
        return [], []

    grouped_data = defaultdict(set)

    def get_clean_value(row, col):
        val = row.get(col)
        return None if pd.isna(val) else val

    for _, row in df.iterrows():
        nombre_lista = row['NOMBRE LISTA']
        if pd.isna(nombre_lista):
            continue

        valores = (
            get_clean_value(row, 'NOMBRE SEGMENTO'),
            get_clean_value(row, 'SEDE'),
            get_clean_value(row, 'ORGANO'),
            get_clean_value(row, 'N ORGANO'),
            get_clean_value(row, 'ROL USUARIO'),
            get_clean_value(row, 'PERFIL USUARIO')
        )
        grouped_data[nombre_lista].add(valores)

    resultado_final = []
    for nombre_lista, valores_set in grouped_data.items():
        valores_lista = [list(tupla) for tupla in valores_set]
        resultado_final.append([nombre_lista, valores_lista])

    logger.info(f"Procesadas {len(resultado_final)} listas con segmentos")
    return headers, resultado_final
