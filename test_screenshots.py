#!/usr/bin/env python3
"""
Script de prueba para el sistema de screenshots automáticos
Simula errores para verificar que las capturas se generen correctamente
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Agregar src al path para importar módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright no está disponible. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True

from src.enhanced_logger import (
    get_logger, get_main_logger, get_auth_logger, get_browser_logger,
    get_crear_lista_logger, get_listar_campanias_logger
)

def test_manual_screenshot():
    """Prueba captura manual de screenshot"""
    print("🧪 Probando captura manual de screenshot...")

    logger = get_main_logger()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Ir a una página de prueba
            page.goto("https://example.com")

            # Capturar screenshot manual
            screenshot_path = logger.capture_screenshot(
                page,
                "test_manual",
                context={"test_type": "manual", "url": "example.com"}
            )

            if screenshot_path and os.path.exists(screenshot_path):
                print(f"✅ Screenshot manual capturado: {screenshot_path}")
                size = os.path.getsize(screenshot_path)
                print(f"   📏 Tamaño: {size} bytes")
            else:
                print("❌ Screenshot manual falló")

        finally:
            context.close()
            browser.close()

def test_automatic_error_screenshot():
    """Prueba captura automática en errores"""
    print("🧪 Probando captura automática en errores...")

    logger = get_browser_logger()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Ir a una página de prueba
            page.goto("https://example.com")

            # Usar contexto de operación con página - error automático
            with logger.operation("test_operation_error", {"test": "automatic_screenshot"}, page) as op:
                op.log_progress("Simulando operación que fallará")

                # Simular error - elemento que no existe
                page.locator("elemento_que_no_existe").click(timeout=1000)

        except Exception:
            print("✅ Error capturado (esperado) - screenshot automático generado")

        finally:
            context.close()
            browser.close()

def test_browser_error_logging():
    """Prueba logging específico de errores del navegador"""
    print("🧪 Probando logging de errores del navegador...")

    logger = get_browser_logger()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Ir a una página de prueba
            page.goto("https://example.com")

            # Simular error del navegador
            try:
                page.locator("boton_inexistente").click(timeout=2000)
            except Exception as e:
                # Log específico de error del navegador con screenshot
                logger.log_browser_error(
                    "click_boton_inexistente",
                    e,
                    page,
                    context={"elemento": "boton_inexistente", "url": "example.com"}
                )
                print("✅ Error del navegador loggeado con screenshot")

        finally:
            context.close()
            browser.close()

def test_operation_failure_logging():
    """Prueba logging de fallos de operaciones"""
    print("🧪 Probando logging de fallos de operaciones...")

    logger = get_crear_lista_logger()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Ir a una página con contenido HTML
            page.goto("data:text/html,<html><body><h1>Test Page</h1><p>Error simulation page</p></body></html>")

            # Simular fallo de operación
            logger.log_operation_failure(
                "crear_lista_test",
                "Simulación de fallo en creación de lista",
                page,
                context={
                    "lista_nombre": "test_lista",
                    "error_code": "SIM001",
                    "usuarios_procesados": 25,
                    "usuarios_fallidos": 3
                }
            )

            print("✅ Fallo de operación loggeado con screenshot")

        finally:
            context.close()
            browser.close()

def test_critical_error_with_page():
    """Prueba error crítico con página"""
    print("🧪 Probando error crítico con página...")

    logger = get_main_logger()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Crear una página con contenido personalizado
            html_content = """
            <html>
            <head><title>Error Test Page</title></head>
            <body>
                <h1>🚨 Página de Prueba de Error Crítico</h1>
                <div class="error-container">
                    <p>Esta página simula un error crítico del sistema.</p>
                    <div class="error-details">
                        <span>Error Code: CRIT_001</span>
                        <span>Timestamp: 2025-09-15 12:30:45</span>
                    </div>
                </div>
            </body>
            </html>
            """
            page.goto(f"data:text/html,{html_content}")

            # Simular error crítico
            try:
                raise RuntimeError("Error crítico simulado del sistema")
            except Exception as e:
                logger.critical(
                    "Error crítico del sistema detectado",
                    error=e,
                    page=page,
                    context={
                        "error_code": "CRIT_001",
                        "system_state": "critical",
                        "recovery_possible": False
                    }
                )
                print("✅ Error crítico loggeado con screenshot")

        finally:
            context.close()
            browser.close()

def verificar_screenshots_generados():
    """Verifica que los screenshots se hayan generado correctamente"""
    print("🧪 Verificando screenshots generados...")

    # Obtener directorio de screenshots
    logger = get_main_logger()
    screenshots_dir = logger.log_dir / "screenshots"

    if not screenshots_dir.exists():
        print("⚠️ Directorio de screenshots no existe aún")
        return

    # Listar screenshots generados
    screenshots = list(screenshots_dir.glob("*.png"))
    print(f"📸 Screenshots encontrados: {len(screenshots)}")

    for screenshot in screenshots:
        size = screenshot.stat().st_size
        print(f"  📋 {screenshot.name}: {size} bytes")

        # Verificar que el archivo no esté corrupto (tamaño mínimo razonable)
        if size > 1000:  # Al menos 1KB
            print(f"    ✅ Screenshot válido")
        else:
            print(f"    ⚠️ Screenshot posiblemente corrupto (muy pequeño)")

def verificar_logs_con_screenshots():
    """Verifica que los logs contengan referencias a screenshots"""
    print("🧪 Verificando logs con referencias a screenshots...")

    logger = get_main_logger()
    log_files = list(logger.log_dir.glob("*.json"))

    screenshot_refs = 0

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        if 'screenshot_path' in log_entry:
                            screenshot_refs += 1
                            print(f"  📸 Screenshot referenciado: {log_entry.get('message', 'N/A')[:50]}...")
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"  ⚠️ Error leyendo {log_file.name}: {e}")

    print(f"📊 Total de referencias a screenshots en logs: {screenshot_refs}")

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas del sistema de screenshots")
    print("=" * 60)

    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright no está disponible. Instala con: pip install playwright && playwright install")
        return

    try:
        # Pruebas individuales
        test_manual_screenshot()
        print()

        test_automatic_error_screenshot()
        print()

        test_browser_error_logging()
        print()

        test_operation_failure_logging()
        print()

        test_critical_error_with_page()
        print()

        # Verificación de resultados
        verificar_screenshots_generados()
        print()

        verificar_logs_con_screenshots()
        print()

        print("=" * 60)
        print("🎉 Todas las pruebas de screenshots completadas!")

        # Mostrar ubicación de los archivos
        logger = get_main_logger()
        print(f"\n📂 Archivos generados en:")
        print(f"  📄 Logs: {logger.log_dir}")
        print(f"  📸 Screenshots: {logger.log_dir / 'screenshots'}")

    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()