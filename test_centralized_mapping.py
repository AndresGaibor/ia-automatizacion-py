#!/usr/bin/env python3
"""
Test del sistema centralizado de mapeo email → lista
"""

import sys
sys.path.insert(0, '.')

from src.api import API
from src.demo import construir_mapa_global_email_lista, obtener_lista_de_email
import pandas as pd

def test_centralized_mapping():
    """Prueba el sistema centralizado de mapeo"""

    print("🧪 TEST: Sistema centralizado de mapeo email → lista")
    print("=" * 70)

    # Leer algunos emails del Excel existente para testing
    excel_file = "data/suscriptores/20250918_Com_Infografía de OJM en relación a TI_Alcobendas_TI-20250918_20250922081827.xlsx"

    try:
        df_abiertos = pd.read_excel(excel_file, sheet_name="Abiertos")
        test_emails = df_abiertos['Correo'].head(3).tolist()
        print(f"📧 Emails de prueba: {test_emails}")
    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return False

    with API() as api:
        print(f"\n🔌 Conectado a API")

        # 1. OBTENER LISTAS
        try:
            todas_listas = api.suscriptores.get_lists()
            # Filtrar solo las listas de la campaña para el test
            campaign_list_ids = [1163824, 1165864, 1166843, 1167082]
            listas_campania = [lista for lista in todas_listas if int(lista.id) in campaign_list_ids]

            mapa_listas = {int(lista.id): lista.name for lista in todas_listas}
            print(f"✅ {len(todas_listas)} listas totales, {len(listas_campania)} de campaña")

        except Exception as e:
            print(f"❌ Error obteniendo listas: {e}")
            return False

        # 2. TEST RÁPIDO: construir mapa solo para listas de campaña
        print(f"\n🏗️ CONSTRUYENDO MAPA CENTRALIZADO (solo listas de campaña)")
        print("-" * 60)

        try:
            # Construir mapa solo para listas de campaña (más rápido para testing)
            mapa_global = construir_mapa_global_email_lista(api, listas_campania)
            print(f"✅ Mapa construido: {len(mapa_global)} emails mapeados")

        except Exception as e:
            print(f"❌ Error construyendo mapa: {e}")
            return False

        # 3. PROBAR BÚSQUEDAS
        print(f"\n🔍 PROBANDO BÚSQUEDAS CON MAPA CENTRALIZADO")
        print("-" * 60)

        id_listas_campania = set(campaign_list_ids)
        emails_encontrados = 0

        for email in test_emails:
            print(f"\n📧 Buscando: {email}")

            # Usar la función de búsqueda
            lista_resultado = obtener_lista_de_email(
                email, mapa_global, id_listas_campania, mapa_listas
            )

            if lista_resultado:
                emails_encontrados += 1
                print(f"   ✅ Encontrado en: {lista_resultado}")
            else:
                print(f"   ❌ No encontrado")

        # 4. RESULTADO DEL TEST
        print(f"\n🎯 RESULTADO DEL TEST")
        print("=" * 40)

        success_rate = (emails_encontrados / len(test_emails)) * 100
        print(f"📊 Emails encontrados: {emails_encontrados}/{len(test_emails)} ({success_rate:.1f}%)")

        if success_rate >= 80:
            print(f"🎉 ¡TEST EXITOSO! Sistema centralizado funcionando")
            return True
        elif success_rate > 0:
            print(f"⚠️  TEST PARCIAL: Funciona pero con limitaciones")
            return True
        else:
            print(f"❌ TEST FALLIDO: Sistema no encuentra emails")
            return False

def main():
    success = test_centralized_mapping()

    if success:
        print(f"\n💡 Sistema centralizado listo para usar en demo.py")
    else:
        print(f"\n💡 Revisar sistema antes de ejecutar demo.py")

if __name__ == "__main__":
    main()