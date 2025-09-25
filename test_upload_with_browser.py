#!/usr/bin/env python3
"""
Test uploading subscriber list WITH browser context for field scraping
"""
import sys
import os
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "src"))

try:
    from src.crear_lista_mejorado import crear_lista_via_api, crear_campos_personalizados, agregar_suscriptores_via_api
    from src.utils import load_config, data_path, crear_contexto_navegador, configurar_navegador
    from src.autentificacion import login
    from src.api import API
    from src.logger import get_logger
    from playwright.sync_api import sync_playwright
    import pandas as pd
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_upload_with_browser_context():
    """Test uploading with browser context for field scraping"""
    print("🧪 TESTING UPLOAD WITH BROWSER CONTEXT")
    print("=" * 70)

    logger = get_logger()
    config = load_config()

    # Use the new test file
    archivo_lista = data_path("listas/Lista_Test_SinDuplicados.xlsx")

    print(f"📄 Using test file: {archivo_lista}")

    if not os.path.exists(archivo_lista):
        print(f"❌ Test file not found: {archivo_lista}")
        return False

    try:
        # Read Excel file
        df = pd.read_excel(archivo_lista, sheet_name="Datos")
        print(f"📊 Loaded {len(df)} rows with columns: {list(df.columns)}")

        # Create API instance
        api = API()

        # Generate list name
        nombre_lista = "Lista_Test_SinDuplicados_Browser"

        with sync_playwright() as p:
            browser = configurar_navegador(p, extraccion_oculta=False)
            context = crear_contexto_navegador(browser, extraccion_oculta=False)
            page = context.new_page()

            try:
                # Login
                login(page, context)
                print("✅ Login completed")

                # Step 1: Create list
                print("🔧 Step 1: Creating list...")
                list_id = crear_lista_via_api(nombre_lista, config, api)
                if not list_id:
                    print("❌ Failed to create list")
                    return False

                print(f"✅ List created with ID: {list_id}")

                # Step 2: Create custom fields with browser context for scraping
                print("🔧 Step 2: Creating custom fields with intelligent filtering...")
                success = crear_campos_personalizados(list_id, df, api, page=page)

                if not success:
                    print("❌ Failed to create custom fields")
                    return False

                print("✅ Custom fields created successfully")

                # Step 3: Add subscribers
                print("👥 Step 3: Adding subscribers...")
                suscriptores_agregados = agregar_suscriptores_via_api(list_id, df, api)

                print(f"✅ Upload completed:")
                print(f"   🆔 List ID: {list_id}")
                print(f"   📝 List Name: {nombre_lista}")
                print(f"   👥 Subscribers Added: {suscriptores_agregados}")

                # Verify success
                if suscriptores_agregados == len(df):
                    print("✅ Upload test PASSED - All subscribers added correctly")

                    # Save list info for later tests
                    with open('test_list_info_browser.txt', 'w') as f:
                        f.write(f"list_id={list_id}\n")
                        f.write(f"nombre_lista={nombre_lista}\n")
                        f.write(f"suscriptores={suscriptores_agregados}\n")

                    return True
                else:
                    print(f"❌ Upload test FAILED - Expected {len(df)} subscribers, got {suscriptores_agregados}")
                    return False

            finally:
                try:
                    context.close()
                    browser.close()
                except:
                    pass

    except Exception as e:
        print(f"❌ Error during browser upload test: {e}")
        logger.error(f"Error en test con navegador: {e}")
        return False

def main():
    """Run upload test with browser context"""
    print("🧪 UPLOAD TEST WITH BROWSER CONTEXT")
    print("=" * 80)

    success = test_upload_with_browser_context()

    if success:
        print("\n🎉 BROWSER UPLOAD TEST COMPLETED SUCCESSFULLY!")
        print("The list was created using intelligent field filtering.")
    else:
        print("\n❌ BROWSER UPLOAD TEST FAILED")
        print("There were issues creating the list with browser context.")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)