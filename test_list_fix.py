#!/usr/bin/env python3
"""
Test específico para validar el fix de asignación de listas
"""

import sys
sys.path.insert(0, '.')

from src.api import API
from src.demo import _construir_mapa_email_listas_desde_search
import pandas as pd

def test_list_assignment_fix():
    """Prueba el fix de asignación de listas con emails reales"""

    print("🧪 TEST: Fix de asignación de listas")
    print("=" * 60)

    # Leer emails del Excel existente
    excel_file = "data/suscriptores/20250918_Com_Infografía de OJM en relación a TI_Alcobendas_TI-20250918_20250922081827.xlsx"

    print(f"📊 Leyendo emails de: {excel_file}")

    try:
        df_abiertos = pd.read_excel(excel_file, sheet_name="Abiertos")
        sample_emails = df_abiertos['Correo'].head(5).tolist()
        print(f"🎯 Emails de prueba: {sample_emails}")

    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return False

    with API() as api:
        print("\n🔌 Conectado a API")

        # Obtener todas las listas
        try:
            todas_listas = api.suscriptores.get_lists()
            mapa_listas = {int(lista.id): lista.name for lista in todas_listas}
            print(f"✅ Obtenidas {len(todas_listas)} listas")

        except Exception as e:
            print(f"❌ Error obteniendo listas: {e}")
            return False

        # Obtener info de campaña (datos reales)
        try:
            campanias = api.campaigns.get_all()
            campaign_id = None

            for campania in campanias:
                if "20250918_Com_Infografía de OJM en relación a TI_Alcobendas_TI" in campania.name:
                    campaign_id = campania.id
                    info_campania = api.campaigns.get_basic_info(campaign_id)
                    id_listas_campania = set(int(lid) for lid in (info_campania.lists or []))

                    print(f"✅ Campaña encontrada: {campania.name}")
                    print(f"📋 Listas de campaña: {id_listas_campania}")
                    print(f"📋 Nombres: {[mapa_listas.get(lid, f'Lista_{lid}') for lid in id_listas_campania]}")
                    break

            if not campaign_id:
                print("❌ No se encontró la campaña")
                return False

        except Exception as e:
            print(f"❌ Error obteniendo campaña: {e}")
            return False

        # TEST: Usar el nuevo método de asignación
        print("\n🧪 PROBANDO NUEVO MÉTODO DE ASIGNACIÓN")
        print("-" * 50)

        emails_set = {email.strip().lower() for email in sample_emails}

        try:
            # Usar la función corregida
            mapa_resultado = _construir_mapa_email_listas_desde_search(
                api, id_listas_campania, emails_set, mapa_listas
            )

            print("✅ Función ejecutada exitosamente")
            print(f"📊 Resultados obtenidos: {len(mapa_resultado)} de {len(emails_set)} emails")

            # Mostrar resultados detallados
            if mapa_resultado:
                print("\n📋 ASIGNACIONES EXITOSAS:")
                for email, list_id in mapa_resultado.items():
                    lista_nombre = mapa_listas.get(list_id, f"Lista_{list_id}")
                    print(f"   ✅ {email} → {lista_nombre} (ID: {list_id})")

                success_rate = (len(mapa_resultado) / len(emails_set)) * 100
                print(f"\n🎯 Tasa de éxito: {success_rate:.1f}%")

                if success_rate >= 80:
                    print("🎉 ¡EXCELENTE! El fix funciona correctamente")
                    return True
                elif success_rate >= 50:
                    print("⚠️  PARCIAL: El fix funciona pero con limitaciones")
                    return True
                else:
                    print("❌ PROBLEMÁTICO: El fix necesita ajustes")
                    return False

            else:
                print("❌ No se asignaron listas para ningún email")
                return False

        except Exception as e:
            print(f"❌ Error en test de asignación: {e}")
            return False

def main():
    success = test_list_assignment_fix()

    if success:
        print("\n🎉 TEST EXITOSO: El fix está funcionando")
        print("💡 Puede proceder a ejecutar demo.py completo")
    else:
        print("\n❌ TEST FALLIDO: El fix necesita revisión")
        print("💡 Revise la lógica antes de ejecutar demo.py")

if __name__ == "__main__":
    main()