#!/usr/bin/env python3
"""
Create test Excel file with unique data (no duplicates)
"""
import pandas as pd
import os

def create_test_excel():
    # Create test data with 10 initial users (no duplicates)
    data = {
        'Correo Electrónico': [
            'usuario01@test-sinduplicados.com',
            'usuario02@test-sinduplicados.com',
            'usuario03@test-sinduplicados.com',
            'usuario04@test-sinduplicados.com',
            'usuario05@test-sinduplicados.com',
            'usuario06@test-sinduplicados.com',
            'usuario07@test-sinduplicados.com',
            'usuario08@test-sinduplicados.com',
            'usuario09@test-sinduplicados.com',
            'usuario10@test-sinduplicados.com'
        ],
        'PERFIL USUARIO': [
            'JDO DE PRIMERA INSTANCIA',
            'JDO DE LO SOCIAL',
            'TRIB SUP DE JUSTICIA',
            'AUDIENCIA PROVINCIAL',
            'JDO DE PRIMERA INSTANCIA',
            'JDO DE LO SOCIAL',
            'TRIB SUP DE JUSTICIA',
            'AUDIENCIA PROVINCIAL',
            'JDO DE PRIMERA INSTANCIA',
            'JDO DE LO SOCIAL'
        ],
        'ROL USUARIO': [
            'TRAMITADOR',
            'GESTOR',
            'COORDINADOR',
            'SECRETARIO',
            'TRAMITADOR',
            'GESTOR',
            'COORDINADOR',
            'SECRETARIO',
            'TRAMITADOR',
            'GESTOR'
        ],
        'SEDE': [
            'MADRID',
            'MADRID-PRINCESA',
            'BARCELONA',
            'VALENCIA',
            'SEVILLA',
            'BILBAO',
            'ZARAGOZA',
            'MALAGA',
            'MURCIA',
            'PALMA'
        ],
        'ORGANO': [
            'MADRID_GTA',
            'MADRID_JS',
            'BARCELONA_GTA',
            'VALENCIA_JS',
            'SEVILLA_GTA',
            'BILBAO_JS',
            'ZARAGOZA_GTA',
            'MALAGA_JS',
            'MURCIA_GTA',
            'PALMA_JS'
        ],
        'Segmentos': [
            'MADRID_GTA;MADRID_JS',
            'MADRID_JS;BARCELONA_GTA',
            'BARCELONA_GTA;VALENCIA_JS',
            'VALENCIA_JS;SEVILLA_GTA',
            'SEVILLA_GTA;BILBAO_JS',
            'BILBAO_JS;ZARAGOZA_GTA',
            'ZARAGOZA_GTA;MALAGA_JS',
            'MALAGA_JS;MURCIA_GTA',
            'MURCIA_GTA;PALMA_JS',
            'PALMA_JS;MADRID_GTA'
        ],
        'CAMPO_NUEVO_UNICO': [  # New field that should be created
            'DATO_01',
            'DATO_02',
            'DATO_03',
            'DATO_04',
            'DATO_05',
            'DATO_06',
            'DATO_07',
            'DATO_08',
            'DATO_09',
            'DATO_10'
        ]
    }

    df = pd.DataFrame(data)

    # Ensure directory exists
    os.makedirs('data/listas', exist_ok=True)

    # Write to Excel
    excel_path = 'data/listas/Lista_Test_SinDuplicados.xlsx'
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Datos', index=False)

    print(f"✅ Excel file created: {excel_path}")
    print(f"📊 Columns: {list(df.columns)}")
    print(f"👥 Users: {len(df)}")
    print("🔍 Sample data:")
    print(df[['Correo Electrónico', 'PERFIL USUARIO', 'ROL USUARIO', 'SEDE']].head(3))

    return excel_path

if __name__ == "__main__":
    create_test_excel()