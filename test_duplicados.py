#!/usr/bin/env python3

import pandas as pd
import os
import tempfile
from src.crear_lista import _generar_archivo_subida_desde_hoja

def crear_archivo_prueba_con_duplicados():
    """Crea un archivo Excel de prueba con emails duplicados"""
    datos = {
        'email': [
            'prueba@gmail.com',
            'usuario1@example.com', 
            'prueba@gmail.com',  # Duplicado
            'usuario2@example.com',
            'test@email.com',
            'prueba@gmail.com',  # Otro duplicado
            'usuario3@example.com',
            'test@email.com'     # Duplicado
        ],
        'localidad': ['Madrid', 'Barcelona', 'Madrid', 'Valencia', 'Sevilla', 'Madrid', 'Bilbao', 'Sevilla'],
        'zona': ['A', 'B', 'A', 'C', 'D', 'A', 'E', 'D'],
        'campoA': ['A1', 'A2', 'A1', 'A3', 'A4', 'A1', 'A5', 'A4'],
        'campoB': ['5.5', '6.0', '5.5', '7.0', '8.0', '5.5', '9.0', '8.0']
    }
    
    df = pd.DataFrame(datos)
    archivo_prueba = "data/Lista_prueba_duplicados.xlsx"
    
    # Crear el directorio si no existe
    os.makedirs(os.path.dirname(archivo_prueba), exist_ok=True)
    
    # Escribir a Excel
    with pd.ExcelWriter(archivo_prueba, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='TestDuplicados', index=False)
    
    return archivo_prueba

def probar_eliminacion_duplicados():
    """Prueba la función de eliminación de duplicados"""
    print("🧪 Creando archivo de prueba con duplicados...")
    archivo_prueba = crear_archivo_prueba_con_duplicados()
    
    print(f"📄 Archivo creado: {archivo_prueba}")
    
    # Mostrar contenido original
    print("\n📋 Contenido original:")
    df_original = pd.read_excel(archivo_prueba, sheet_name='TestDuplicados')
    print(df_original)
    print(f"Total filas: {len(df_original)}")
    
    # Contar duplicados por email
    duplicados = df_original['email'].value_counts()
    print(f"\n📊 Conteo de emails:")
    print(duplicados)
    
    # Probar la función
    print(f"\n🔄 Probando eliminación de duplicados...")
    try:
        csv_temporal = _generar_archivo_subida_desde_hoja(archivo_prueba, 'TestDuplicados')
        
        # Leer el CSV generado
        df_sin_duplicados = pd.read_csv(csv_temporal)
        print(f"\n✅ CSV temporal generado: {csv_temporal}")
        print(f"\n📋 Contenido sin duplicados:")
        print(df_sin_duplicados)
        print(f"Total filas después: {len(df_sin_duplicados)}")
        
        # Limpiar
        if os.path.exists(csv_temporal):
            os.remove(csv_temporal)
            print(f"🗑️ Archivo temporal eliminado")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n📁 Archivo de prueba guardado en: {archivo_prueba}")

if __name__ == "__main__":
    probar_eliminacion_duplicados()