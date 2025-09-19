#!/usr/bin/env python3

import pandas as pd
import sys

def explorar_excel(archivo):
    """Explora la estructura del archivo Excel"""
    try:
        with pd.ExcelFile(archivo, engine="openpyxl") as xls:
            print(f"Hojas disponibles: {xls.sheet_names}")
            
            for hoja in xls.sheet_names:
                print(f"\n--- Hoja: {hoja} ---")
                df = pd.read_excel(xls, sheet_name=hoja, dtype=str).fillna("")
                print(f"Columnas: {list(df.columns)}")
                print(f"Filas: {len(df)}")
                
                if len(df) > 0:
                    print("Primeras 3 filas:")
                    print(df.head(3))
                    
                    # Buscar columnas que puedan contener emails
                    for col in df.columns:
                        if any(keyword in str(col).lower() for keyword in ['email', 'correo', 'mail']):
                            print(f"\nColumna de email detectada: {col}")
                            emails = df[col].value_counts()
                            duplicados = emails[emails > 1]
                            if len(duplicados) > 0:
                                print(f"Emails duplicados encontrados:")
                                print(duplicados)
                            else:
                                print("No se encontraron emails duplicados")
                    
    except Exception as e:
        print(f"Error explorando el archivo: {e}")

if __name__ == "__main__":
    archivo = "data/Lista_envio.xlsx"
    explorar_excel(archivo)