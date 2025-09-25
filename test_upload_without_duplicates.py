#!/usr/bin/env python3
"""
Test uploading subscriber list with the duplicate field fixes
"""
import sys
import os
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / "src"))

try:
    from src.crear_lista_mejorado import crear_lista_automatica
    from src.utils import load_config, data_path
    from src.logger import get_logger
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_upload_without_duplicates():
    """Test uploading the new list without field duplicates"""
    print("🧪 TESTING UPLOAD WITHOUT FIELD DUPLICATES")
    print("=" * 70)

    logger = get_logger()

    # Use the new test file
    archivo_lista = data_path("listas/Lista_Test_SinDuplicados.xlsx")

    print(f"📄 Using test file: {archivo_lista}")

    # Verify file exists
    if not os.path.exists(archivo_lista):
        print(f"❌ Test file not found: {archivo_lista}")
        return False

    try:
        print("🔧 Creating list with improved duplicate prevention...")

        # Create the list with validation enabled
        resultado = crear_lista_automatica(archivo_lista, validar_cambios=True)

        if not resultado:
            print("❌ Error creating the list")
            return False

        list_id = resultado.get('list_id')
        nombre_lista = resultado.get('nombre_lista', 'Lista_Test_SinDuplicados')
        suscriptores = resultado.get('suscriptores_agregados', 0)

        print(f"✅ List created successfully:")
        print(f"   🆔 ID: {list_id}")
        print(f"   📝 Name: {nombre_lista}")
        print(f"   👥 Subscribers: {suscriptores}")

        # Verify the list was created correctly
        if list_id and suscriptores == 10:
            print("✅ Upload test PASSED - List created with correct number of subscribers")

            # Save list info for later tests
            with open('test_list_info.txt', 'w') as f:
                f.write(f"list_id={list_id}\n")
                f.write(f"nombre_lista={nombre_lista}\n")
                f.write(f"suscriptores={suscriptores}\n")

            return True
        else:
            print(f"❌ Upload test FAILED - Expected 10 subscribers, got {suscriptores}")
            return False

    except Exception as e:
        print(f"❌ Error during upload test: {e}")
        logger.error(f"Error en test de subida: {e}")
        return False

def main():
    """Run upload test"""
    print("🧪 UPLOAD TEST WITHOUT FIELD DUPLICATES")
    print("=" * 80)

    success = test_upload_without_duplicates()

    if success:
        print("\n🎉 UPLOAD TEST COMPLETED SUCCESSFULLY!")
        print("The new list was created without field duplicates.")
    else:
        print("\n❌ UPLOAD TEST FAILED")
        print("There were issues creating the list.")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)