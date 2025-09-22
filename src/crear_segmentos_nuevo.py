"""
Módulo para crear segmentos en listas de suscriptores (DEPRECADO).
NOTA: Esta funcionalidad ha sido reemplazada por el mapeo unificado en mapeo_segmentos.py
que procesa archivos individuales en data/listas/ y los sube a Acumbamail automáticamente.
"""
from .utils import data_path, notify
from .logger import get_logger
from .excel_helper import ExcelHelper
import pandas as pd
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Rutas de archivos
ARCHIVO_SEGMENTOS = data_path("Segmentos.xlsx")
ARCHIVO_LISTA_ENVIO = data_path("Lista_envio.xlsx")

def leer_definiciones_segmentos() -> Dict[str, List[Dict[str, Any]]]:
    """
    Lee las definiciones de segmentos desde el archivo Segmentos.xlsx
    
    Returns:
        Dict con formato: {nombre_lista: [segmentos_con_condiciones]}
    """
    logger = get_logger()
    
    if not os.path.exists(ARCHIVO_SEGMENTOS):
        logger.error(f"Archivo de segmentos no encontrado: {ARCHIVO_SEGMENTOS}")
        return {}
    
    try:
        df = ExcelHelper.leer_excel(ARCHIVO_SEGMENTOS)
        
        if df.empty:
            logger.warning("Archivo de segmentos está vacío")
            return {}
        
        # Verificar columnas requeridas
        columnas_requeridas = ['NOMBRE LISTA', 'NOMBRE SEGMENTO']
        tiene_columnas, faltantes = ExcelHelper.verificar_columnas(df, columnas_requeridas)
        
        if not tiene_columnas:
            logger.error(f"Columnas requeridas faltantes en Segmentos.xlsx: {faltantes}")
            return {}
        
        # Detectar columnas de condiciones (desde SEDE en adelante)
        try:
            if 'SEDE' in df.columns:
                idx_inicio = list(df.columns).index('SEDE')
            else:
                idx_inicio = list(df.columns).index('NOMBRE SEGMENTO') + 1
            columnas_condiciones = list(df.columns)[idx_inicio:]
        except ValueError:
            logger.error("No se pudieron detectar columnas de condiciones")
            return {}
        
        logger.info(f"Columnas de condiciones detectadas: {columnas_condiciones}")
        
        # Organizar por nombre de lista
        definiciones = {}
        
        for nombre_lista in df['NOMBRE LISTA'].dropna().unique():
            df_lista = df[df['NOMBRE LISTA'] == nombre_lista]
            segmentos = []
            
            for nombre_segmento in df_lista['NOMBRE SEGMENTO'].dropna().unique():
                df_segmento = df_lista[df_lista['NOMBRE SEGMENTO'] == nombre_segmento]
                
                # Consolidar condiciones para este segmento
                condiciones = {}
                for col in columnas_condiciones:
                    if col in df_segmento.columns:
                        valores = df_segmento[col].dropna().unique()
                        if len(valores) > 0:
                            condiciones[col] = list(valores) if len(valores) > 1 else valores[0]
                
                if condiciones:  # Solo agregar si tiene condiciones
                    segmentos.append({
                        'nombre': nombre_segmento,
                        'condiciones': condiciones
                    })
            
            if segmentos:
                definiciones[nombre_lista] = segmentos
        
        logger.info(f"Definiciones de segmentos cargadas: {list(definiciones.keys())}")
        return definiciones
        
    except Exception as e:
        logger.error(f"Error leyendo definiciones de segmentos: {e}")
        return {}

def aplicar_segmento_a_lista(nombre_lista: str, segmentos: List[Dict[str, Any]]) -> bool:
    """
    Aplica los segmentos a una hoja específica del archivo Lista_envio.xlsx
    
    Args:
        nombre_lista: Nombre de la hoja/lista a procesar
        segmentos: Lista de definiciones de segmentos
        
    Returns:
        True si se aplicó exitosamente, False si hubo error
    """
    logger = get_logger()
    
    try:
        # Verificar que la hoja existe
        hojas_disponibles = ExcelHelper.obtener_hojas(ARCHIVO_LISTA_ENVIO)
        if nombre_lista not in hojas_disponibles:
            logger.warning(f"Hoja '{nombre_lista}' no encontrada en Lista_envio.xlsx. Hojas disponibles: {hojas_disponibles}")
            return False
        
        # Leer la hoja
        df = ExcelHelper.leer_excel(ARCHIVO_LISTA_ENVIO, nombre_lista)
        
        if df.empty:
            logger.warning(f"Hoja '{nombre_lista}' está vacía")
            return False
        
        print(f"📄 Procesando lista '{nombre_lista}' con {len(df)} filas")
        
        # Agregar columna Segmentos si no existe
        df = ExcelHelper.agregar_columna_si_no_existe(df, 'Segmentos', '')
        
        filas_modificadas = 0
        
        # Aplicar cada segmento
        for segmento in segmentos:
            nombre_segmento = segmento['nombre']
            condiciones = segmento['condiciones']
            
            print(f"  🔍 Aplicando segmento '{nombre_segmento}' con condiciones: {condiciones}")
            
            # Verificar que las columnas de condiciones existan en la hoja
            columnas_faltantes = []
            for col in condiciones.keys():
                if col not in df.columns:
                    columnas_faltantes.append(col)
            
            if columnas_faltantes:
                logger.warning(f"Columnas de condición faltantes en '{nombre_lista}': {columnas_faltantes}")
                continue
            
            # Aplicar condiciones y actualizar columna Segmentos
            df_antes = df.copy()
            df = ExcelHelper.actualizar_valores_por_condicion(
                df=df,
                condiciones=condiciones,
                columna_actualizar='Segmentos',
                nuevo_valor=nombre_segmento,
                acumular=True,
                separador=';'
            )
            
            # Contar filas modificadas en esta iteración
            filas_modificadas_segmento = (df['Segmentos'] != df_antes['Segmentos']).sum()
            filas_modificadas += filas_modificadas_segmento
            
            print(f"    ✅ {filas_modificadas_segmento} filas asignadas al segmento '{nombre_segmento}'")
        
        # Guardar cambios
        if filas_modificadas > 0:
            if ExcelHelper.escribir_excel(df, ARCHIVO_LISTA_ENVIO, nombre_lista, reemplazar=False):
                print(f"  💾 Guardados cambios en '{nombre_lista}': {filas_modificadas} filas modificadas")
                logger.info(f"Segmentos aplicados a '{nombre_lista}': {filas_modificadas} filas modificadas")
                return True
            else:
                logger.error(f"Error guardando cambios en '{nombre_lista}'")
                return False
        else:
            print(f"  ⚠️  No se encontraron filas que cumplan las condiciones en '{nombre_lista}'")
            return True
            
    except Exception as e:
        logger.error(f"Error aplicando segmentos a lista '{nombre_lista}': {e}")
        print(f"❌ Error procesando lista '{nombre_lista}': {e}")
        return False

def actualizar_fecha_creacion_segmentos(listas_procesadas: List[str]):
    """
    Actualiza la fecha de creación en el archivo Segmentos.xlsx para las listas procesadas
    
    Args:
        listas_procesadas: Lista de nombres de listas que se procesaron exitosamente
    """
    logger = get_logger()
    
    try:
        df = ExcelHelper.leer_excel(ARCHIVO_SEGMENTOS)
        
        if df.empty:
            return
        
        # Agregar columna si no existe
        df = ExcelHelper.agregar_columna_si_no_existe(df, 'CREACION SEGMENTO', '')
        
        # Actualizar fecha para listas procesadas
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        
        for nombre_lista in listas_procesadas:
            mask = df['NOMBRE LISTA'] == nombre_lista
            if mask.any():
                df.loc[mask, 'CREACION SEGMENTO'] = fecha_actual
                logger.info(f"Fecha de creación actualizada para lista '{nombre_lista}': {fecha_actual}")
        
        # Guardar cambios
        ExcelHelper.escribir_excel(df, ARCHIVO_SEGMENTOS, reemplazar=True)
        
    except Exception as e:
        logger.error(f"Error actualizando fechas de creación: {e}")

def mostrar_resumen_segmentacion(nombre_lista: str) -> None:
    """
    Muestra un resumen de la segmentación aplicada a una lista
    
    Args:
        nombre_lista: Nombre de la lista a analizar
    """
    try:
        df = ExcelHelper.leer_excel(ARCHIVO_LISTA_ENVIO, nombre_lista)
        
        if df.empty or 'Segmentos' not in df.columns:
            print(f"  📊 '{nombre_lista}': Sin datos de segmentación")
            return
        
        # Contar distribución de segmentos
        segmentos_counts = df['Segmentos'].value_counts(dropna=False)
        
        print(f"  📊 Resumen de '{nombre_lista}':")
        print(f"     Total de filas: {len(df)}")
        
        for segmento, count in segmentos_counts.items():
            if pd.isna(segmento) or segmento == '':
                print(f"     Sin segmento: {count}")
            else:
                print(f"     {segmento}: {count}")
        
    except Exception as e:
        print(f"  ❌ Error generando resumen para '{nombre_lista}': {e}")

def main():
    """
    Función principal para procesar segmentos
    """
    logger = get_logger()
    logger.info("Iniciando proceso de creación de segmentos")
    
    print("🔄 Iniciando proceso de segmentación...")
    
    # Leer definiciones de segmentos
    definiciones = leer_definiciones_segmentos()
    
    if not definiciones:
        print("❌ No se encontraron definiciones de segmentos válidas")
        return
    
    print(f"📋 Se encontraron definiciones para {len(definiciones)} lista(s):")
    for nombre_lista, segmentos in definiciones.items():
        print(f"  • {nombre_lista}: {len(segmentos)} segmento(s)")
    
    # Procesar cada lista
    listas_exitosas = []
    listas_fallidas = []
    
    for nombre_lista, segmentos in definiciones.items():
        print(f"\n🔄 Procesando lista: {nombre_lista}")
        
        if aplicar_segmento_a_lista(nombre_lista, segmentos):
            listas_exitosas.append(nombre_lista)
            mostrar_resumen_segmentacion(nombre_lista)
        else:
            listas_fallidas.append(nombre_lista)
    
    # Actualizar fechas de creación
    if listas_exitosas:
        actualizar_fecha_creacion_segmentos(listas_exitosas)
    
    # Resumen final
    print(f"\n📊 Resumen del proceso:")
    print(f"   ✅ Listas procesadas exitosamente: {len(listas_exitosas)}")
    if listas_exitosas:
        for lista in listas_exitosas:
            print(f"      • {lista}")
    
    print(f"   ❌ Listas con errores: {len(listas_fallidas)}")
    if listas_fallidas:
        for lista in listas_fallidas:
            print(f"      • {lista}")
    
    # Notificación
    if listas_exitosas:
        # notify("Segmentación completada", f"Se procesaron {len(listas_exitosas)} lista(s) exitosamente")
        print(f"🎉 Segmentación completada: Se procesaron {len(listas_exitosas)} lista(s) exitosamente")
    else:
        # notify("Error en segmentación", "No se pudieron procesar las listas")
        print("❌ Error en segmentación: No se pudieron procesar las listas")
    
    logger.info(f"Proceso completado: {len(listas_exitosas)} exitosas, {len(listas_fallidas)} fallidas")

if __name__ == "__main__":
    main()