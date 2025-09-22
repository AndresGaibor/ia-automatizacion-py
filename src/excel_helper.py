"""
Utilidades para manejar archivos Excel de forma más sencilla y robusta.
Centraliza operaciones comunes como leer, escribir, verificar columnas, etc.
"""
import pandas as pd
import os
from typing import List, Dict, Optional, Any, Union
from pathlib import Path
from .logger import get_logger

logger = get_logger()

class ExcelHelper:
    """Clase helper para operaciones Excel comunes"""
    
    @staticmethod
    def leer_excel(archivo: Union[str, Path], hoja: Optional[str] = None) -> pd.DataFrame:
        """
        Lee un archivo Excel de forma segura
        
        Args:
            archivo: Ruta al archivo Excel
            hoja: Nombre de la hoja (None = primera hoja)
            
        Returns:
            DataFrame con los datos o DataFrame vacío si hay error
        """
        try:
            if not os.path.exists(archivo):
                logger.warning(f"Archivo no existe: {archivo}")
                return pd.DataFrame()
                
            if hoja:
                df = pd.read_excel(archivo, sheet_name=hoja, engine="openpyxl")
            else:
                df = pd.read_excel(archivo, engine="openpyxl")
                
            logger.info(f"Leído Excel: {archivo} ({len(df)} filas)")
            return df
            
        except Exception as e:
            logger.error(f"Error leyendo Excel {archivo}: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def escribir_excel(df: pd.DataFrame, archivo: Union[str, Path], hoja: str = "Sheet1", 
                      reemplazar: bool = True) -> bool:
        """
        Escribe DataFrame a Excel de forma segura
        
        Args:
            df: DataFrame a escribir
            archivo: Ruta del archivo destino
            hoja: Nombre de la hoja
            reemplazar: Si True, reemplaza archivo completo. Si False, agrega hoja.
            
        Returns:
            True si exitoso, False si hay error
        """
        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(archivo), exist_ok=True)
            
            if reemplazar or not os.path.exists(archivo):
                # Crear archivo nuevo
                df.to_excel(archivo, sheet_name=hoja, index=False, engine="openpyxl")
            else:
                # Agregar a archivo existente
                with pd.ExcelWriter(archivo, mode='a', engine="openpyxl", 
                                  if_sheet_exists='replace') as writer:
                    df.to_excel(writer, sheet_name=hoja, index=False)
                    
            logger.info(f"Escrito Excel: {archivo} - {hoja} ({len(df)} filas)")
            return True
            
        except Exception as e:
            logger.error(f"Error escribiendo Excel {archivo}: {e}")
            return False
    
    @staticmethod
    def obtener_hojas(archivo: Union[str, Path]) -> List[str]:
        """
        Obtiene lista de nombres de hojas en un archivo Excel
        
        Args:
            archivo: Ruta al archivo Excel
            
        Returns:
            Lista de nombres de hojas
        """
        try:
            if not os.path.exists(archivo):
                return []
                
            excel_file = pd.ExcelFile(archivo, engine="openpyxl")
            return excel_file.sheet_names
            
        except Exception as e:
            logger.error(f"Error obteniendo hojas de {archivo}: {e}")
            return []
    
    @staticmethod
    def verificar_columnas(df: pd.DataFrame, columnas_requeridas: List[str]) -> tuple[bool, List[str]]:
        """
        Verifica que un DataFrame tenga las columnas requeridas
        
        Args:
            df: DataFrame a verificar
            columnas_requeridas: Lista de nombres de columnas requeridas
            
        Returns:
            (tiene_todas, columnas_faltantes)
        """
        columnas_actuales = set(df.columns)
        columnas_req_set = set(columnas_requeridas)
        
        faltantes = list(columnas_req_set - columnas_actuales)
        tiene_todas = len(faltantes) == 0
        
        return tiene_todas, faltantes
    
    @staticmethod
    def agregar_columna_si_no_existe(df: pd.DataFrame, nombre_columna: str, 
                                   valor_defecto: Any = "") -> pd.DataFrame:
        """
        Agrega una columna al DataFrame si no existe
        
        Args:
            df: DataFrame a modificar
            nombre_columna: Nombre de la columna a agregar
            valor_defecto: Valor por defecto para la columna
            
        Returns:
            DataFrame con la columna agregada (o sin cambios si ya existía)
        """
        if nombre_columna not in df.columns:
            df[nombre_columna] = valor_defecto
            logger.info(f"Agregada columna '{nombre_columna}' con valor defecto: {valor_defecto}")
        
        return df
    
    @staticmethod
    def filtrar_filas_por_condiciones(df: pd.DataFrame, condiciones: Dict[str, Any]) -> pd.DataFrame:
        """
        Filtra filas del DataFrame basado en condiciones múltiples
        
        Args:
            df: DataFrame a filtrar
            condiciones: Dict con formato {columna: valor_o_lista_valores}
            
        Returns:
            DataFrame filtrado
        """
        df_filtrado = df.copy()
        
        for columna, valor in condiciones.items():
            if columna not in df.columns:
                logger.warning(f"Columna '{columna}' no existe en DataFrame")
                continue
                
            if isinstance(valor, (list, tuple)):
                # Múltiples valores posibles
                df_filtrado = df_filtrado[df_filtrado[columna].isin(valor)]
            else:
                # Valor único
                df_filtrado = df_filtrado[df_filtrado[columna] == valor]
        
        logger.info(f"Filtrado: {len(df)} -> {len(df_filtrado)} filas")
        return df_filtrado
    
    @staticmethod
    def actualizar_valores_por_condicion(df: pd.DataFrame, condiciones: Dict[str, Any], 
                                        columna_actualizar: str, nuevo_valor: Any,
                                        acumular: bool = False, separador: str = ";") -> pd.DataFrame:
        """
        Actualiza valores en una columna basado en condiciones
        
        Args:
            df: DataFrame a modificar
            condiciones: Dict con condiciones de filtro
            columna_actualizar: Nombre de la columna a actualizar
            nuevo_valor: Valor a asignar
            acumular: Si True, acumula valores existentes con separador
            separador: Separador para acumulación
            
        Returns:
            DataFrame modificado
        """
        # Filtrar filas que cumplen condiciones
        mask = pd.Series([True] * len(df))
        
        for columna, valor in condiciones.items():
            if columna not in df.columns:
                continue
                
            if isinstance(valor, (list, tuple)):
                mask &= df[columna].isin(valor)
            else:
                mask &= (df[columna] == valor)
        
        # Agregar columna si no existe
        df = ExcelHelper.agregar_columna_si_no_existe(df, columna_actualizar, "")
        
        if acumular:
            # Acumular valores existentes
            for idx in df[mask].index:
                valor_actual = str(df.loc[idx, columna_actualizar]).strip()
                if valor_actual and valor_actual != nuevo_valor:
                    # Solo agregar si no está ya presente
                    valores_existentes = valor_actual.split(separador)
                    if nuevo_valor not in valores_existentes:
                        df.loc[idx, columna_actualizar] = f"{valor_actual}{separador}{nuevo_valor}"
                else:
                    df.loc[idx, columna_actualizar] = nuevo_valor
        else:
            # Reemplazar valores
            df.loc[mask, columna_actualizar] = nuevo_valor
        
        filas_afectadas = mask.sum()
        logger.info(f"Actualizadas {filas_afectadas} filas en columna '{columna_actualizar}'")
        
        return df

    @staticmethod
    def crear_archivo_si_no_existe(archivo: Union[str, Path], columnas: List[str], 
                                  hoja: str = "Sheet1") -> bool:
        """
        Crea un archivo Excel con columnas específicas si no existe
        
        Args:
            archivo: Ruta del archivo a crear
            columnas: Lista de nombres de columnas
            hoja: Nombre de la hoja
            
        Returns:
            True si se creó o ya existía, False si error
        """
        try:
            if os.path.exists(archivo):
                return True
                
            df_vacio = pd.DataFrame(columns=columnas)
            return ExcelHelper.escribir_excel(df_vacio, archivo, hoja)
            
        except Exception as e:
            logger.error(f"Error creando archivo {archivo}: {e}")
            return False

    @staticmethod
    def obtener_ultima_fila_por_columnas(df: pd.DataFrame, columnas_clave: List[str]) -> Optional[Dict[str, Any]]:
        """
        Obtiene la última fila basada en columnas específicas para búsqueda incremental
        
        Args:
            df: DataFrame a analizar
            columnas_clave: Columnas que identifican el último registro
            
        Returns:
            Dict con valores de la última fila o None si está vacío
        """
        try:
            if df.empty:
                return None
                
            # Verificar que existan las columnas
            tiene_columnas, faltantes = ExcelHelper.verificar_columnas(df, columnas_clave)
            if not tiene_columnas:
                logger.warning(f"Columnas faltantes para búsqueda: {faltantes}")
                return None
            
            ultima_fila = df.iloc[-1]
            resultado = {col: ultima_fila[col] for col in columnas_clave}
            
            logger.info(f"Última fila encontrada: {resultado}")
            return resultado
            
        except Exception as e:
            logger.error(f"Error obteniendo última fila: {e}")
            return None