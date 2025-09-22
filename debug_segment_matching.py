#!/usr/bin/env python3
"""
Script para debuggear el matching de segmentos
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
from src.utils import data_path

def debug_segment_matching():
    # Leer Segmentos.xlsx
    segmentos_file = data_path("Segmentos.xlsx")
    print(f"📊 Leyendo {segmentos_file}")
    df_segmentos = pd.read_excel(segmentos_file)

    print("\n📋 CONTENIDO DE SEGMENTOS.xlsx:")
    print("=" * 60)
    print(df_segmentos.to_string())

    # Filtrar solo Prueba_SEGMENTOS2
    df_prueba = df_segmentos[df_segmentos['NOMBRE LISTA'] == 'Prueba_SEGMENTOS2']

    print(f"\n🎯 SEGMENTOS PARA 'Prueba_SEGMENTOS2':")
    print("=" * 60)
    print(df_prueba.to_string())

    # Leer archivo de lista
    lista_file = data_path("listas/Prueba_SEGMENTOS2.xlsx")
    print(f"\n📊 Leyendo {lista_file}")
    df_lista = pd.read_excel(lista_file)

    print(f"\n📋 ESTRUCTURA DE Prueba_SEGMENTOS2.xlsx:")
    print("=" * 60)
    print(f"Shape: {df_lista.shape}")
    print(f"Columnas: {list(df_lista.columns)}")

    # Mostrar primeras 5 filas
    print(f"\n📝 PRIMERAS 5 FILAS:")
    print("=" * 60)
    print(df_lista.head().to_string())

    # Analizar valores únicos de cada columna de segmentación
    segmento_cols = ['SEDE', 'ORGANO', 'N ORGANO', 'ROL USUARIO', 'PERFIL USUARIO']

    print(f"\n🔍 VALORES ÚNICOS EN COLUMNAS DE SEGMENTACIÓN:")
    print("=" * 60)

    for col in segmento_cols:
        if col in df_lista.columns:
            valores_unicos = df_lista[col].dropna().unique()
            print(f"{col}: {list(valores_unicos)}")
        else:
            print(f"{col}: [COLUMNA NO EXISTE]")

    # Ahora comparar con las condiciones de los segmentos
    print(f"\n🎯 COMPARACIÓN CON CONDICIONES DE SEGMENTOS:")
    print("=" * 60)

    for _, seg_row in df_prueba.iterrows():
        nombre_segmento = seg_row['NOMBRE SEGMENTO']
        print(f"\n📌 Segmento: {nombre_segmento}")

        for col in segmento_cols:
            if col in df_lista.columns:
                valor_esperado = seg_row.get(col)
                valores_en_lista = df_lista[col].dropna().unique()

                if pd.notna(valor_esperado) and valor_esperado != '':
                    coincide = valor_esperado in valores_en_lista
                    print(f"  {col}: '{valor_esperado}' -> {'✅' if coincide else '❌'} (valores en lista: {list(valores_en_lista)})")
                else:
                    print(f"  {col}: [SIN CONDICIÓN] (valores en lista: {list(valores_en_lista)})")

if __name__ == "__main__":
    debug_segment_matching()