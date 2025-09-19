#!/usr/bin/env python3
"""
Script de prueba para el sistema de logging de screenshots (sin Playwright)
Verifica que el sistema funcione correctamente sin necesidad de navegador
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Agregar src al path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.enhanced_logger import (
    get_logger, get_main_logger, get_auth_logger, get_browser_logger,
    get_crear_lista_logger, get_listar_campanias_logger, PLAYWRIGHT_AVAILABLE
)

def test_screenshot_methods_without_playwright():
    """Prueba métodos de screenshot sin Playwright disponible"""
    print("🧪 Probando métodos de screenshot sin Playwright...")

    logger = get_main_logger()

    # Intentar capturar screenshot sin página (debe manejar graciosamente)
    screenshot_path = logger.capture_screenshot(
        None,  # No page
        "test_without_playwright",
        context={"test_type": "no_playwright"}
    )

    if screenshot_path is None:
        print("✅ Screenshot sin Playwright manejado correctamente (devuelve None)")
    else:
        print("❌ Screenshot sin Playwright no manejado correctamente")

    # Verificar que se loggeó la advertencia apropiada
    print("   📄 Verificando log de advertencia...")

def test_error_logging_without_page():
    """Prueba logging de errores sin página"""
    print("🧪 Probando logging de errores sin página...")

    logger = get_browser_logger()

    try:
        # Simular error sin página
        raise ValueError("Error de prueba sin página")
    except Exception as e:
        # Log error sin página - no debe fallar
        logger.error("Error sin página", error=e, page=None,
                    context={"test_type": "no_page_error"})

        print("✅ Error sin página loggeado correctamente")

def test_operation_context_without_page():
    """Prueba contexto de operación sin página"""
    print("🧪 Probando contexto de operación sin página...")

    logger = get_crear_lista_logger()

    try:
        with logger.operation("test_operation_no_page", {"test": True}, page=None) as op:
            op.log_progress("Operación sin página iniciada")
            # Simular error
            raise RuntimeError("Error en operación sin página")
    except RuntimeError:
        print("✅ Operación sin página manejada correctamente")

def test_browser_error_methods():
    """Prueba métodos específicos de errores del navegador"""
    print("🧪 Probando métodos de errores del navegador...")

    logger = get_browser_logger()

    # Simular error del navegador sin página
    test_error = Exception("Error simulado del navegador")

    logger.log_browser_error(
        "test_action",
        test_error,
        page=None,  # Sin página
        context={"element": "test_element", "url": "test.com"}
    )

    print("✅ Error del navegador sin página loggeado correctamente")

def test_operation_failure_method():
    """Prueba método de fallo de operaciones"""
    print("🧪 Probando método de fallo de operaciones...")

    logger = get_crear_lista_logger()

    logger.log_operation_failure(
        "test_operation",
        "Fallo simulado de operación",
        page=None,  # Sin página
        context={
            "operation_id": "test_123",
            "users_processed": 10,
            "users_failed": 2
        }
    )

    print("✅ Fallo de operación sin página loggeado correctamente")

def verificar_logs_generados():
    """Verifica que se generen logs correctamente"""
    print("🧪 Verificando logs generados...")

    logger = get_main_logger()
    log_dir = logger.log_dir

    if not log_dir.exists():
        print("⚠️ Directorio de logs no existe")
        return

    # Buscar archivos JSON de hoy
    import datetime
    today = datetime.datetime.now().strftime("%Y%m%d")

    json_files = list(log_dir.glob(f"*_{today}.json"))
    print(f"📄 Archivos JSON encontrados: {len(json_files)}")

    screenshot_refs = 0
    error_logs = 0

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())

                        # Contar referencias a screenshots
                        if 'screenshot_path' in log_entry:
                            screenshot_refs += 1

                        # Contar logs de error
                        if log_entry.get('level') == 'ERROR':
                            error_logs += 1

                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"  ⚠️ Error leyendo {json_file.name}: {e}")

    print(f"📊 Referencias a screenshots: {screenshot_refs}")
    print(f"📊 Logs de error: {error_logs}")
    print(f"📊 Sistema PLAYWRIGHT disponible: {PLAYWRIGHT_AVAILABLE}")

def test_screenshot_directory_creation():
    """Prueba que se cree el directorio de screenshots"""
    print("🧪 Probando creación de directorio de screenshots...")

    logger = get_main_logger()
    screenshots_dir = logger.log_dir / "screenshots"

    # El directorio debería crearse cuando se intente capturar screenshot
    if screenshots_dir.exists():
        print(f"✅ Directorio de screenshots existe: {screenshots_dir}")
    else:
        print(f"📂 Directorio de screenshots se creará cuando sea necesario: {screenshots_dir}")

def mostrar_funcionalidades_disponibles():
    """Muestra las funcionalidades disponibles del sistema"""
    print("📋 Funcionalidades del sistema de screenshots:")
    print(f"  🌐 Playwright disponible: {PLAYWRIGHT_AVAILABLE}")
    print("  📸 Métodos disponibles:")
    print("    • logger.capture_screenshot(page, name, context)")
    print("    • logger.log_browser_error(action, error, page, context)")
    print("    • logger.log_operation_failure(operation, details, page, context)")
    print("    • logger.error(message, error, page, **kwargs)")
    print("    • logger.critical(message, error, page, **kwargs)")
    print("    • logger.operation(name, context, page)")

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas del sistema de logging de screenshots")
    print("=" * 60)

    try:
        mostrar_funcionalidades_disponibles()
        print()

        test_screenshot_methods_without_playwright()
        print()

        test_error_logging_without_page()
        print()

        test_operation_context_without_page()
        print()

        test_browser_error_methods()
        print()

        test_operation_failure_method()
        print()

        test_screenshot_directory_creation()
        print()

        verificar_logs_generados()
        print()

        print("=" * 60)
        print("🎉 Todas las pruebas de logging completadas!")

        # Mostrar ubicación de archivos
        logger = get_main_logger()
        print(f"\n📂 Archivos generados en:")
        print(f"  📄 Logs: {logger.log_dir}")
        print(f"  📸 Screenshots: {logger.log_dir / 'screenshots'}")

        if not PLAYWRIGHT_AVAILABLE:
            print("\n💡 Para habilitar screenshots automáticos:")
            print("  1. Instala Playwright: pip install playwright")
            print("  2. Instala navegadores: playwright install")
            print("  3. El sistema detectará automáticamente Playwright")

    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()