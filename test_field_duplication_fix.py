#!/usr/bin/env python3
"""
Test script to verify the duplicate field fix
Tests the enhanced field scraping and deduplication logic
"""
import sys
import os
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "src"))

try:
    from src.field_scraper import (
        normalizar_nombre_campo,
        filtrar_campos_necesarios,
        obtener_campos_disponibles_acumba
    )
    from src.utils import crear_contexto_navegador, configurar_navegador
    from src.autentificacion import login
    from playwright.sync_api import sync_playwright
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_field_normalization():
    """Test improved field normalization"""
    print("🧪 TESTING IMPROVED FIELD NORMALIZATION")
    print("=" * 60)

    test_cases = [
        # Expected duplicates that should normalize to same value
        ("ROL USUARIO", "ROL_USUARIO", True),
        ("ROL_USUARIO", "rol_usuario", True),
        ("ROLUSUARIO", "rol_usuario", True),
        ("Segmentos", "segmentos", True),
        ("PERFIL USUARIO", "PERFILUSUARIO", True),
        ("N ORGANO", "NORGANO", True),

        # Different fields that should NOT be duplicates
        ("SEDE", "ORGANO", False),
        ("email", "estado", False),
        ("NOMBRE", "APELLIDO", False),
    ]

    success = True
    for campo1, campo2, should_be_same in test_cases:
        norm1 = normalizar_nombre_campo(campo1)
        norm2 = normalizar_nombre_campo(campo2)
        is_same = norm1 == norm2

        status = "✅" if is_same == should_be_same else "❌"
        print(f"{status} '{campo1}' -> '{norm1}' | '{campo2}' -> '{norm2}' | Same: {is_same}")

        if is_same != should_be_same:
            success = False

    return success

def test_field_filtering_logic():
    """Test enhanced field filtering with duplicate detection"""
    print("\n🧪 TESTING ENHANCED FIELD FILTERING LOGIC")
    print("=" * 60)

    # Simulate Excel fields with duplicates (like the real issue)
    campos_excel = [
        "email",
        "Segmentos",     # Should be mapped
        "ROL USUARIO",   # Should be mapped
        "ROL_USUARIO",   # Should be detected as duplicate and ignored
        "SEDE",          # Should be created (new field)
        "ORGANO",        # Should be created (new field)
        "Segmentos",     # Should be detected as duplicate and ignored
    ]

    # Simulate existing Acumba fields
    campos_acumba = [
        "Correo electrónico",  # Maps to email
        "Estado",
        "Fecha de alta",
        "Segmentos",          # Exists
        "PERFIL USUARIO",     # Exists
        "ROL USUARIO",        # Exists (should catch both ROL variants)
    ]

    print(f"📊 Excel fields: {campos_excel}")
    print(f"📊 Acumba fields: {campos_acumba}")

    resultado = filtrar_campos_necesarios(campos_excel, campos_acumba)

    print(f"\n📊 FILTERING RESULTS:")
    print(f"   🆕 To create: {resultado['crear']}")
    print(f"   🔗 To map: {resultado['mapear']}")
    print(f"   🚫 To ignore: {resultado['ignorar']}")

    # Verify no duplicates in creation list
    expected_crear = ["SEDE", "ORGANO"]  # Only unique new fields
    expected_mapear = ["email", "Segmentos", "ROL USUARIO"]  # Existing fields (no duplicates)
    expected_ignorar_count = 2  # The duplicate ROL_USUARIO and duplicate Segmentos

    success = True
    if set(resultado['crear']) != set(expected_crear):
        print(f"❌ Create fields error: expected {expected_crear}, got {resultado['crear']}")
        success = False

    if set(resultado['mapear']) != set(expected_mapear):
        print(f"❌ Map fields error: expected {expected_mapear}, got {resultado['mapear']}")
        success = False

    if len(resultado['ignorar']) != expected_ignorar_count:
        print(f"❌ Ignore fields error: expected {expected_ignorar_count} ignored, got {len(resultado['ignorar'])}")
        success = False

    if success:
        print("✅ Field filtering with duplicate detection PASSED")

    return success

def test_real_acumba_field_scraping():
    """Test real field scraping from Acumbamail"""
    print("\n🧪 TESTING REAL ACUMBA FIELD SCRAPING")
    print("=" * 60)

    try:
        with sync_playwright() as p:
            browser = configurar_navegador(p, extraccion_oculta=False)
            context = crear_contexto_navegador(browser, extraccion_oculta=False)
            page = context.new_page()

            try:
                login(page, context)
                print("✅ Login completed")

                # Test with the problematic list
                test_list_id = 1170323
                print(f"🔍 Scraping fields from list {test_list_id}")

                campos_info = obtener_campos_disponibles_acumba(page, test_list_id)

                print(f"📊 Fields detected: {len(campos_info['fields'])}")
                print(f"📋 Fields: {campos_info['fields']}")

                # Check for duplicates in detected fields
                campos_norm = [normalizar_nombre_campo(c) for c in campos_info['fields']]
                duplicados = []
                vistos = set()

                for i, campo_norm in enumerate(campos_norm):
                    if campo_norm in vistos:
                        duplicados.append((campos_info['fields'][i], campo_norm))
                    else:
                        vistos.add(campo_norm)

                if duplicados:
                    print(f"❌ Duplicates still detected: {duplicados}")
                    return False
                else:
                    print("✅ No duplicates detected in scraped fields")
                    return True

            finally:
                context.close()
                browser.close()

    except Exception as e:
        print(f"❌ Real scraping test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 DUPLICATE FIELD FIX VERIFICATION")
    print("=" * 70)

    tests = [
        ("Field Normalization", test_field_normalization),
        ("Field Filtering Logic", test_field_filtering_logic),
        ("Real Acumba Field Scraping", test_real_acumba_field_scraping),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("📊 DUPLICATE FIELD FIX TEST RESULTS:")
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   • {test_name}: {status}")
        if result:
            passed += 1

    success_rate = (passed / len(results)) * 100
    print(f"\n📊 Overall: {passed}/{len(results)} tests passed ({success_rate:.1f}%)")

    if success_rate >= 100:
        print("🎉 DUPLICATE FIELD FIX VERIFIED!")
        return True
    else:
        print("❌ DUPLICATE FIELD FIX NEEDS MORE WORK")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)