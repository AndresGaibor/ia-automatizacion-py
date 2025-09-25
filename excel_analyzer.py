#!/usr/bin/env python3
"""
Herramienta permanente para analizar archivos Excel generados
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
from glob import glob
import argparse
import os
from datetime import datetime

def analyze_excel_file(file_path: str, detailed: bool = False):
    """Analiza un archivo Excel específico"""

    print(f"📊 ANALIZANDO: {file_path}")
    print("=" * 80)

    try:
        xl_file = pd.ExcelFile(file_path)
        print(f"📋 Hojas encontradas: {xl_file.sheet_names}")

        total_subs = 0
        total_assigned = 0
        results = {}

        for sheet_name in xl_file.sheet_names:
            print(f"\n🔍 HOJA: {sheet_name}")
            print("-" * 50)

            df = pd.read_excel(file_path, sheet_name=sheet_name)
            print(f"📏 Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")

            # Mostrar columnas
            print(f"🏷️  Columnas: {list(df.columns)}")

            if 'Lista' in df.columns:
                non_null = df['Lista'].notna().sum()
                null_count = df['Lista'].isna().sum()
                total = len(df)

                total_subs += total
                total_assigned += non_null

                fill_rate = (non_null / total * 100) if total > 0 else 0

                print("📊 Análisis columna 'Lista':")
                print(f"   ✅ Asignadas: {non_null}")
                print(f"   ❌ Vacías: {null_count}")
                print(f"   📈 Total: {total}")
                print(f"   🎯 Tasa completitud: {fill_rate:.1f}%")

                results[sheet_name] = {
                    'total': total,
                    'assigned': non_null,
                    'empty': null_count,
                    'fill_rate': fill_rate
                }

                # Mostrar listas únicas
                unique_lists = df['Lista'].dropna().unique()
                if len(unique_lists) > 0:
                    print(f"   📋 Listas encontradas ({len(unique_lists)}):")
                    for lista in sorted(unique_lists):
                        count = (df['Lista'] == lista).sum()
                        print(f"      • {lista}: {count} suscriptores")
                else:
                    print("   ⚠️  Sin listas específicas")

                if detailed and non_null > 0:
                    print("   📧 Primeros 5 emails con lista:")
                    sample = df[df['Lista'].notna()].head(5)
                    for _, row in sample.iterrows():
                        if 'Correo' in row:
                            print(f"      • {row['Correo']} → {row['Lista']}")

            else:
                print("   ℹ️  No tiene columna 'Lista'")
                results[sheet_name] = {'no_lista_column': True}

        # Resumen general
        print("\n🎉 RESUMEN GENERAL")
        print("=" * 60)
        print(f"📊 Total suscriptores: {total_subs}")
        print(f"✅ Con lista asignada: {total_assigned}")
        print(f"❌ Sin lista: {total_subs - total_assigned}")

        if total_subs > 0:
            overall_rate = (total_assigned / total_subs) * 100
            print(f"🎯 Tasa general de completitud: {overall_rate:.1f}%")

            if overall_rate > 80:
                print("🎉 ¡EXCELENTE! Muy buena asignación de listas")
            elif overall_rate > 50:
                print("⚠️  REGULAR: Necesita mejoras")
            else:
                print("❌ PROBLEMÁTICO: Muchas listas vacías")

        return results

    except Exception as e:
        print(f"❌ Error analizando archivo: {e}")
        return None

def find_latest_excel_files(pattern: str = "*xlsx", directory: str = "data/suscriptores"):
    """Encuentra los archivos Excel más recientes"""

    files = glob(f"{directory}/{pattern}")
    # Filtrar archivos temporales
    files = [f for f in files if not f.split('/')[-1].startswith('~$')]

    if not files:
        return []

    # Ordenar por fecha de modificación (más reciente primero)
    files.sort(key=lambda x: datetime.fromtimestamp(os.path.getmtime(x)), reverse=True)

    return files

def compare_excel_files(file1: str, file2: str):
    """Compara dos archivos Excel para ver mejoras"""

    print("🔄 COMPARANDO ARCHIVOS")
    print("=" * 60)
    print(f"📊 Archivo 1: {file1}")
    print(f"📊 Archivo 2: {file2}")

    results1 = analyze_excel_file(file1, detailed=False)
    print("\n" + "="*80 + "\n")
    results2 = analyze_excel_file(file2, detailed=False)

    if results1 and results2:
        print("\n🔄 COMPARACIÓN DE RESULTADOS")
        print("=" * 60)

        for sheet in results1:
            if sheet in results2 and 'fill_rate' in results1[sheet] and 'fill_rate' in results2[sheet]:
                rate1 = results1[sheet]['fill_rate']
                rate2 = results2[sheet]['fill_rate']
                diff = rate2 - rate1

                if diff > 0:
                    print(f"✅ {sheet}: {rate1:.1f}% → {rate2:.1f}% (↑ {diff:+.1f}%)")
                elif diff < 0:
                    print(f"❌ {sheet}: {rate1:.1f}% → {rate2:.1f}% (↓ {diff:+.1f}%)")
                else:
                    print(f"➡️ {sheet}: {rate1:.1f}% → {rate2:.1f}% (sin cambio)")

def main():
    parser = argparse.ArgumentParser(description='Analizar archivos Excel de campañas')
    parser.add_argument('--file', type=str, help='Archivo específico a analizar')
    parser.add_argument('--latest', action='store_true', help='Analizar archivo más reciente')
    parser.add_argument('--compare', action='store_true', help='Comparar los 2 archivos más recientes')
    parser.add_argument('--detailed', action='store_true', help='Análisis detallado')
    parser.add_argument('--pattern', type=str, default='*xlsx', help='Patrón de búsqueda de archivos')

    args = parser.parse_args()


    if args.file:
        analyze_excel_file(args.file, detailed=args.detailed)

    elif args.compare:
        files = find_latest_excel_files(args.pattern)
        if len(files) >= 2:
            compare_excel_files(files[1], files[0])  # Segundo más reciente vs más reciente
        else:
            print("❌ Se necesitan al menos 2 archivos para comparar")

    elif args.latest:
        files = find_latest_excel_files(args.pattern)
        if files:
            analyze_excel_file(files[0], detailed=args.detailed)
        else:
            print("❌ No se encontraron archivos Excel")

    else:
        files = find_latest_excel_files(args.pattern)
        if files:
            print(f"📁 Archivos Excel encontrados: {len(files)}")
            for i, file in enumerate(files[:5]):  # Mostrar los primeros 5
                print(f"  {i+1}. {file}")
            print("\nUse --latest para analizar el más reciente o --file <ruta> para uno específico")
        else:
            print("❌ No se encontraron archivos Excel")

if __name__ == "__main__":
    main()