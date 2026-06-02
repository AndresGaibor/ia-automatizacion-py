"""Lógica de procesamiento de condiciones de segmentación."""
import pandas as pd
from typing import List, Tuple, Any

from ..logger import get_logger

logger = get_logger()


def verificar_columnas_compatibles(df: pd.DataFrame, headers: List[str]) -> Tuple[bool, List[str]]:
    columnas_disponibles = []
    es_compatible = True

    for header in headers:
        if header in df.columns:
            columnas_disponibles.append(header)
        else:
            logger.warning(f"Columna '{header}' no encontrada en archivo de lista")
            es_compatible = False

    return es_compatible, columnas_disponibles


def aplicar_condiciones_segmento(df: pd.DataFrame, condiciones: List[Any], headers: List[str]) -> pd.Series:
    nombre_segmento = condiciones[0]
    valores_condiciones = condiciones[1:]

    mask = pd.Series([True] * len(df))

    for i, valor in enumerate(valores_condiciones):
        if i >= len(headers):
            logger.warning(f"Se ignoró condición adicional más allá de los headers disponibles")
            break

        columna = headers[i]
        if columna not in df.columns:
            mask = pd.Series([False] * len(df))
            logger.warning(f"Columna '{columna}' no encontrada, segmento '{nombre_segmento}' no aplica")
            break

        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            continue

        valor_str = str(valor).strip().lower()
        col_vals = df[columna].astype(str).str.strip().str.lower()
        mask_col = col_vals == valor_str
        mask = mask & mask_col

    return mask


def actualizar_columna_segmentos(df: pd.DataFrame, mask: pd.Series, nombre_segmento: str) -> Tuple[pd.DataFrame, List[int]]:
    filas_modificadas = []

    if 'Segmentos' not in df.columns:
        df['Segmentos'] = ''

    for idx in df[mask].index:
        valor_actual = str(df.loc[idx, 'Segmentos']) if pd.notna(df.loc[idx, 'Segmentos']) else ''
        segmentos_list = [s.strip() for s in valor_actual.split(',') if s.strip()]

        if nombre_segmento not in segmentos_list:
            segmentos_list.append(nombre_segmento)
            df.loc[idx, 'Segmentos'] = ', '.join(segmentos_list)
            filas_modificadas.append(idx)

    return df, filas_modificadas


def detectar_cambios_segmentos(df_original: pd.DataFrame, df_nuevo: pd.DataFrame) -> pd.DataFrame:
    if 'Segmentos' not in df_original.columns or 'Segmentos' not in df_nuevo.columns:
        return pd.DataFrame()

    df_original = df_original.reset_index(drop=True)
    df_nuevo = df_nuevo.reset_index(drop=True)

    cambios = df_original['Segmentos'].fillna('').astype(str) != df_nuevo['Segmentos'].fillna('').astype(str)

    if cambios.any():
        df_cambios = df_nuevo[cambios].copy()
        df_cambios['segmentos_previos'] = df_original.loc[cambios, 'Segmentos'].fillna('').astype(str)
        logger.info(f"Detectados {len(df_cambios)} cambios en segmentos")
        return df_cambios

    logger.info("No se detectaron cambios en segmentos")
    return pd.DataFrame()
