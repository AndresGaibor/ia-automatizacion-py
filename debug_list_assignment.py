#!/usr/bin/env python3
"""
Script de debug para investigar por qué las listas están vacías
"""

import sys
sys.path.insert(0, '.')

from src.api import API
import pandas as pd

def debug_list_assignment():
    """Debug detallado del sistema de asignación de listas"""

    print("🔍 DEBUGGING: Sistema de asignación de listas")
    print("=" * 60)

    # Leer el Excel más reciente para obtener emails de ejemplo
    excel_file = "data/suscriptores/20250918_Com_Infografía de OJM en relación a TI_Alcobendas_TI-20250918_20250922081827.xlsx"

    print(f"📊 Analizando Excel: {excel_file}")

    # Leer hoja "Abiertos" para obtener emails que deberían tener lista
    df_abiertos = pd.read_excel(excel_file, sheet_name="Abiertos")
    print(f"📧 Emails en 'Abiertos': {len(df_abiertos)}")

    # Tomar los primeros 5 emails como muestra
    sample_emails = df_abiertos['Correo'].head(10).tolist()
    print(f"🎯 Emails de muestra: {sample_emails}")

    # Leer hoja "No abiertos" donde SÍ aparecen las listas
    df_no_abiertos = pd.read_excel(excel_file, sheet_name="No abiertos")
    print(f"📧 Emails en 'No abiertos': {len(df_no_abiertos)}")

    # Ver qué listas aparecen en "No abiertos"
    listas_encontradas = df_no_abiertos['Lista'].unique()
    print(f"📋 Listas en 'No abiertos': {listas_encontradas}")

    with API() as api:
        print("\n🔌 Conectado a API")

        # 1. OBTENER TODAS LAS LISTAS
        print("\n1️⃣ OBTENIENDO TODAS LAS LISTAS")
        print("-" * 40)
        try:
            todas_listas = api.suscriptores.get_lists()
            print(f"✅ Total listas obtenidas: {len(todas_listas)}")

            for lista in todas_listas[:10]:  # Mostrar primeras 10
                print(f"   📋 ID: {lista.id} | Nombre: {lista.name}")

            # Crear mapa ID -> Nombre
            mapa_listas = {int(lista.id): lista.name for lista in todas_listas}
            print(f"📊 Mapa de listas creado: {len(mapa_listas)} entradas")

        except Exception as e:
            print(f"❌ Error obteniendo listas: {e}")
            return

        # 2. BUSCAR EMAILS ESPECÍFICOS EN LISTAS
        print("\n2️⃣ BUSCANDO EMAILS ESPECÍFICOS EN LISTAS")
        print("-" * 50)

        for email in sample_emails[:3]:  # Solo los primeros 3 para no hacer muchas llamadas
            print(f"\n🔍 Buscando: {email}")

            # Método 1: search_subscriber
            try:
                resultados = api.suscriptores.search_subscriber(email)
                print(f"   📋 search_subscriber encontró: {len(resultados)} resultados")

                for resultado in resultados:
                    if hasattr(resultado, 'list_id'):
                        list_id = resultado.list_id
                        lista_nombre = mapa_listas.get(int(list_id), f"Lista_{list_id}")
                        print(f"      ✅ Lista ID: {list_id} | Nombre: {lista_nombre}")

                        # Verificar status del suscriptor
                        if hasattr(resultado, 'status'):
                            print(f"      📊 Status: {resultado.status}")
                    else:
                        print(f"      ⚠️  Resultado sin list_id: {resultado}")

            except Exception as e:
                print(f"   ❌ Error en search_subscriber para {email}: {e}")

            # Método 2: Buscar en cada lista manualmente (sample de primeras 3 listas)
            print("   🔍 Búsqueda manual en listas...")
            encontrado_en = []

            for lista in todas_listas[:3]:  # Solo primeras 3 listas para testing
                try:
                    subscribers = api.suscriptores.get_subscribers(
                        list_id=int(lista.id),
                        status=0,  # activos
                        block_index=0,
                        all_fields=1,
                        complete_json=1
                    )

                    for sub in subscribers:
                        if hasattr(sub, 'email') and sub.email.lower() == email.lower():
                            encontrado_en.append(f"{lista.name} (ID: {lista.id})")
                            print(f"      ✅ Encontrado en: {lista.name} (ID: {lista.id})")
                            break

                except Exception as e:
                    print(f"      ⚠️  Error buscando en lista {lista.name}: {e}")
                    continue

            if not encontrado_en:
                print("      ❌ No encontrado en las primeras 3 listas")

        # 3. ANALIZAR CAMPAÑA ESPECÍFICA
        print("\n3️⃣ ANALIZANDO CAMPAÑA ESPECÍFICA")
        print("-" * 40)

        # Buscar el ID de campaña del archivo Excel
        df_general = pd.read_excel(excel_file, sheet_name="General")
        nombre_campania = df_general['Nombre'].iloc[0]
        print(f"📋 Campaña: {nombre_campania}")

        # Buscar campañas para encontrar el ID
        try:
            campanias = api.campaigns.get_all()
            campaign_id = None

            for campania in campanias:
                if nombre_campania in campania.name:
                    campaign_id = campania.id
                    print(f"✅ ID de campaña encontrado: {campaign_id}")

                    # Obtener info básica de la campaña
                    info_basica = api.campaigns.get_basic_info(campaign_id)
                    print(f"📊 Listas de la campaña: {info_basica.lists}")

                    # Convertir a nombres de lista
                    listas_campania = []
                    for list_id in (info_basica.lists or []):
                        nombre = mapa_listas.get(int(list_id), f"Lista_{list_id}")
                        listas_campania.append(f"{nombre} (ID: {list_id})")

                    print("📋 Nombres de listas en campaña:")
                    for lista in listas_campania:
                        print(f"   - {lista}")

                    break

            if not campaign_id:
                print(f"❌ No se encontró ID de campaña para: {nombre_campania}")

        except Exception as e:
            print(f"❌ Error analizando campaña: {e}")

        # 4. COMPARAR CON DATOS DE "NO ABIERTOS"
        print("\n4️⃣ COMPARACIÓN CON DATOS CORRECTOS")
        print("-" * 45)

        print(f"📊 En 'No abiertos' aparecen estas listas: {list(listas_encontradas)}")
        print("📊 Estas corresponden a las listas de la campaña ✅")
        print("")
        print("🤔 HIPÓTESIS DEL PROBLEMA:")
        print("   1. Los emails de 'Abiertos' SÍ pertenecen a listas")
        print("   2. El sistema de búsqueda API no los está encontrando")
        print("   3. Posibles causas:")
        print("      - Rate limiting impidió completar la búsqueda")
        print("      - Parámetros incorrectos en get_subscribers")
        print("      - Los emails están en estado diferente a 'activo'")
        print("      - Diferencias en formato de email (mayúsculas, espacios)")

def main():
    debug_list_assignment()

if __name__ == "__main__":
    main()