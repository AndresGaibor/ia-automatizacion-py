#!/usr/bin/env python3
"""
Test script for JavaScript extraction in subscriber download
"""
import sys
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "src"))

try:
    from src.descargar_suscriptores import extraer_suscriptores_tabla_lista
    from src.utils import crear_contexto_navegador, configurar_navegador, load_config
    from src.autentificacion import login
    from playwright.sync_api import sync_playwright
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_extraction():
    """Test the JavaScript extraction with a real browser context"""
    print("🔍 Starting JavaScript extraction test...")

    config = load_config()
    print(f"✅ Config loaded: {len(config)} entries")

    with sync_playwright() as p:
        try:
            # Configure browser
            browser = configurar_navegador(p, extraccion_oculta=False)
            context = crear_contexto_navegador(browser, extraccion_oculta=False)
            page = context.new_page()

            print("✅ Browser context created")

            # Login to Acumbamail
            print("🔐 Logging in to Acumbamail...")
            try:
                login(page, context)
                print("✅ Login process completed")
            except Exception as e:
                print(f"⚠️ Login process had issues: {e}")
                # Continue anyway, might already be logged in

            # Navigate directly to the specific test list
            test_url = "https://acumbamail.com/app/list/1170058/subscriber/list/"
            list_name = "EVID CONTENCIOSO 19 GTA LAJ BG"
            list_id = 1170058

            print(f"📋 Testing extraction with list: {list_name}")
            print(f"🧭 Navigating to test URL: {test_url}")

            # Navigate directly to the subscriber list
            page.goto(test_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)

            print("🧪 Testing JavaScript extraction function...")

            # Call the extraction function
            suscriptores = extraer_suscriptores_tabla_lista(page, list_name, list_id)

            print("📊 EXTRACTION RESULTS:")
            print(f"   - Total subscribers extracted: {len(suscriptores)}")

            if len(suscriptores) > 0:
                print("   - Sample subscriber (first):")
                primer_suscriptor = suscriptores[0]
                for key, value in primer_suscriptor.items():
                    print(f"      {key}: {value}")

                print(f"   - Total fields extracted: {len(primer_suscriptor.keys())}")
                print(f"   - Fields: {', '.join(primer_suscriptor.keys())}")

                # Test creating Excel file
                print("📄 Testing Excel file generation...")
                from src.excel_helper import ExcelHelper
                import pandas as pd

                df = pd.DataFrame(suscriptores)
                excel_path = "/Users/andresgaibor/code/python/acumba-automation/data/test_extraction_results.xlsx"
                ExcelHelper.escribir_excel(df, excel_path, "Suscriptores", reemplazar=True)
                print(f"   - Excel file created: {excel_path}")
                print(f"   - Columns in Excel: {list(df.columns)}")

                return len(primer_suscriptor.keys()) >= 10  # Should have many fields
            else:
                print("   ❌ No subscribers extracted")
                return False

        except Exception as e:
            print(f"❌ Test error: {e}")
            return False
        finally:
            try:
                context.close()
                browser.close()
            except:
                pass

    return False

if __name__ == "__main__":
    print("🧪 JAVASCRIPT EXTRACTION TEST")
    print("=" * 50)

    success = test_extraction()

    if success:
        print("\n✅ TEST PASSED: JavaScript extraction working correctly")
        sys.exit(0)
    else:
        print("\n❌ TEST FAILED: JavaScript extraction needs improvement")
        sys.exit(1)