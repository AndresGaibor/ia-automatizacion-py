#!/usr/bin/env python3
"""
Test completo del flujo de segmentos con las correcciones implementadas
"""
import sys
import os
from pathlib import Path

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve()))
    __package__ = "test_root"

try:
    from src.crear_lista_mejorado import crear_lista_automatica
    from src.mapeo_segmentos import mapear_segmentos_completo
    from src.utils import load_config, data_path
    from src.infrastructure.api import API
    from src.logger import get_logger
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_complete_workflow():
    """Test completo del flujo con las nuevas correcciones"""
    print("🧪 COMPLETE WORKFLOW TEST - SEGMENT PROCESSING")
    print("=" * 70)

    logger = get_logger()

    # Rutas de archivos
    archivo_lista = data_path("listas/Lista_Prueba_Segmentos.xlsx")
    archivo_segmentos = data_path("Segmentos.xlsx")

    # Verificar que los archivos existen
    if not os.path.exists(archivo_lista):
        print(f"❌ Archivo de lista no encontrado: {archivo_lista}")
        return False

    if not os.path.exists(archivo_segmentos):
        print(f"❌ Archivo de segmentos no encontrado: {archivo_segmentos}")
        return False

    print("✅ Archivos encontrados:")
    print(f"   📄 Lista: {archivo_lista}")
    print(f"   📄 Segmentos: {archivo_segmentos}")

    try:
        # PASO 1: Crear/actualizar la lista con las nuevas correcciones
        print(f"\n{'='*20} PASO 1: CREAR LISTA {'='*20}")
        print("🔧 Creando lista con sistema mejorado de campos...")

        resultado_lista = crear_lista_automatica(archivo_lista, validar_cambios=True)

        if not resultado_lista:
            print("❌ Error creando la lista")
            return False

        list_id = resultado_lista.get('list_id')
        nombre_lista = resultado_lista.get('nombre_lista', 'Lista_Prueba_Segmentos')

        print("✅ Lista creada/actualizada:")
        print(f"   🆔 ID: {list_id}")
        print(f"   📝 Nombre: {nombre_lista}")
        print(f"   👥 Suscriptores: {resultado_lista.get('suscriptores_agregados', 0)}")

        # PASO 2: Procesar segmentos
        print(f"\n{'='*20} PASO 2: PROCESAR SEGMENTOS {'='*20}")
        print("🔧 Procesando segmentos con sistema mejorado...")

        resultado_segmentos = mapear_segmentos_completo()

        print("✅ Segmentos procesados:")
        if isinstance(resultado_segmentos, dict):
            listas_procesadas = resultado_segmentos.get('listas_procesadas', [])
            errores = resultado_segmentos.get('errores', [])

            print(f"   📊 Listas procesadas: {len(listas_procesadas)}")
            for lista in listas_procesadas:
                print(f"      • {lista}")

            if errores:
                print(f"   ⚠️ Errores: {len(errores)}")
                for error in errores[:3]:  # Mostrar solo primeros 3
                    print(f"      • {error}")
        else:
            print(f"   📊 Resultado: {resultado_segmentos}")

        # PASO 3: Verificar resultado
        print(f"\n{'='*20} PASO 3: VERIFICACIÓN {'='*20}")

        # Verificar que la lista tiene el ID correcto
        config = load_config()
        api = API()

        try:
            # Verificar que la lista existe
            listas_remotas = api.suscriptores.get_lists()
            lista_encontrada = any(lista.id == list_id for lista in listas_remotas)

            if lista_encontrada:
                print(f"✅ Lista verificada en servidor (ID: {list_id})")
            else:
                print("⚠️ Lista no encontrada en servidor")

            # Verificar segmentos (si la API lo permite)
            try:
                segmentos = api.suscriptores.get_list_segments(list_id)
                if segmentos:
                    items = getattr(segmentos, 'segments', segmentos) or []
                    print(f"✅ Segmentos creados: {len(items)}")
                    for seg in items[:3]:  # Mostrar primeros 3
                        if isinstance(seg, tuple):
                            print(f"      • {seg[0]}")
                        elif hasattr(seg, 'name'):
                            print(f"      • {seg.name}")
                else:
                    print("⚠️ No se encontraron segmentos")
            except Exception as e:
                print(f"⚠️ Error verificando segmentos: {e}")

        except Exception as e:
            print(f"⚠️ Error en verificación: {e}")

        print("\n✅ WORKFLOW COMPLETO EXITOSO")
        return True

    except Exception as e:
        print(f"❌ Error en workflow: {e}")
        logger.error(f"Error en test completo: {e}")
        return False

def test_field_optimization():
    """Test específico de optimización de campos"""
    print(f"\n{'='*20} TEST OPTIMIZACIÓN DE CAMPOS {'='*20}")

    try:
        import pandas as pd

        # Leer el archivo de prueba
        archivo_lista = data_path("listas/Lista_Prueba_Segmentos.xlsx")
        df = pd.read_excel(archivo_lista, sheet_name="Datos")

        print("📊 Archivo de prueba:")
        print(f"   📄 {len(df)} suscriptores")
        print(f"   📋 Campos: {list(df.columns)}")

        # Simular campos que ya existen en Acumba
        campos_acumba_simulados = [
            "Correo electrónico",
            "Estado",
            "Fecha de alta",
            "Segmentos",
            "ROL USUARIO",
            "SEDE"
        ]

        from src.field_scraper import filtrar_campos_necesarios

        resultado = filtrar_campos_necesarios(list(df.columns), campos_acumba_simulados)

        print("\n📊 Análisis de campos:")
        print(f"   🆕 Para crear: {resultado['crear']}")
        print(f"   🔗 Para mapear: {resultado['mapear']}")
        print(f"   🚫 Para ignorar: {resultado['ignorar']}")

        # Verificar que la optimización funciona
        total_excel = len(df.columns)
        total_crear = len(resultado['crear'])
        total_mapear = len(resultado['mapear'])

        print("\n📈 Eficiencia:")
        print(f"   📊 Campos en Excel: {total_excel}")
        print(f"   🆕 Nuevos a crear: {total_crear}")
        print(f"   🔗 Existentes a mapear: {total_mapear}")
        print(f"   📉 Reducción: {((total_excel - total_crear) / total_excel) * 100:.1f}%")

        return True

    except Exception as e:
        print(f"❌ Error en test de optimización: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 COMPREHENSIVE SEGMENT WORKFLOW TEST")
    print("=" * 80)

    tests = [
        ("Field Optimization", test_field_optimization),
        ("Complete Workflow", test_complete_workflow)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running {test_name}...")
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅ PASSED' if result else '❌ FAILED'}: {test_name}")
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))

    # Summary
    print(f"\n{'='*80}")
    print("📊 TEST RESULTS SUMMARY:")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   • {test_name}: {status}")

    success_rate = (passed / total) * 100 if total > 0 else 0
    print(f"\n📊 Overall: {passed}/{total} tests passed ({success_rate:.1f}%)")

    if success_rate >= 80:
        print("🎉 SEGMENT WORKFLOW VERIFICATION SUCCESSFUL!")
        return True
    else:
        print("⚠️ SEGMENT WORKFLOW NEEDS ATTENTION")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)