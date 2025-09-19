#!/usr/bin/env python3
"""
Script de prueba para el sistema de logging mejorado
Verifica que todos los componentes del logging funcionen correctamente
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
    get_crear_lista_logger, get_listar_campanias_logger, get_performance_logger,
    log_operation, log_errors
)

def test_basic_logging():
    """Prueba básica de funcionalidad de logging"""
    print("🧪 Probando logging básico...")

    logger = get_main_logger()

    # Pruebas básicas de logging
    logger.debug("Esta es una prueba de DEBUG")
    logger.info("Esta es una prueba de INFO")
    logger.warning("Esta es una prueba de WARNING")

    # Prueba de logging con contexto
    logger.info("Prueba con contexto", context={"user": "test", "action": "testing"})

    # Prueba de error simulado
    try:
        raise ValueError("Error de prueba")
    except Exception as e:
        logger.error("Error capturado en prueba", error=e, context={"test_type": "error_handling"})

    print("✅ Logging básico completado")

def test_operation_context():
    """Prueba el contexto de operaciones"""
    print("🧪 Probando contexto de operaciones...")

    logger = get_main_logger()

    # Prueba de operación exitosa
    with logger.operation("test_operation_success", {"test_param": "value1"}) as op:
        op.log_progress("Iniciando operación de prueba")
        import time
        time.sleep(0.1)  # Simular trabajo
        op.log_progress("Operación en progreso", 50, 100)
        time.sleep(0.1)
        op.log_progress("Operación completándose", 100, 100)

    # Prueba de operación con error
    try:
        with logger.operation("test_operation_error", {"test_param": "value2"}) as op:
            op.log_progress("Iniciando operación que fallará")
            time.sleep(0.1)
            raise RuntimeError("Error simulado en operación")
    except Exception:
        pass  # Error esperado

    print("✅ Contexto de operaciones completado")

def test_specialized_loggers():
    """Prueba loggers especializados"""
    print("🧪 Probando loggers especializados...")

    # Logger de autenticación
    auth_logger = get_auth_logger()
    auth_logger.info("Prueba de autenticación", context={"username": "test_user"})

    # Logger de navegador
    browser_logger = get_browser_logger()
    browser_logger.log_browser_action("Navegando a página", "https://test.com")

    # Logger de crear lista
    crear_logger = get_crear_lista_logger()
    crear_logger.log_file_operation("Leyendo", "/path/to/test.xlsx", 1024)

    # Logger de campañas
    campanias_logger = get_listar_campanias_logger()
    campanias_logger.log_data_extraction("campañas", 15, "base de datos")

    # Logger de rendimiento
    perf_logger = get_performance_logger()
    perf_logger.log_performance_metric("response_time", 250.5, "ms")

    print("✅ Loggers especializados completados")

def test_decorators():
    """Prueba decoradores de logging"""
    print("🧪 Probando decoradores...")

    @log_operation("test_decorated_function", "main")
    def funcion_decorada(param1, param2="default"):
        """Función de prueba decorada"""
        logger = get_main_logger()
        logger.info(f"Ejecutando función con param1={param1}, param2={param2}")
        return len(param1) + len(param2)

    # Función exitosa
    resultado = funcion_decorada("test", "value")
    print(f"Resultado función decorada: {resultado}")

    # Función con error
    @log_operation("test_decorated_error", "main")
    def funcion_con_error():
        raise ValueError("Error en función decorada")

    try:
        funcion_con_error()
    except ValueError:
        pass  # Error esperado

    print("✅ Decoradores completados")

def test_performance_tracking():
    """Prueba seguimiento de rendimiento"""
    print("🧪 Probando seguimiento de rendimiento...")

    logger = get_performance_logger()

    # Simular varias métricas
    for i in range(5):
        logger.log_performance_metric("operation_time", 100 + i * 50, "ms")
        logger.log_performance_metric("memory_usage", 50 + i * 10, "MB")

    # Obtener resumen
    summary = logger.get_performance_summary()
    print("📊 Resumen de rendimiento:")
    for metric, stats in summary.items():
        print(f"  {metric}: avg={stats['avg']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}")

    print("✅ Seguimiento de rendimiento completado")

def test_log_files():
    """Verifica que se generen archivos de log"""
    print("🧪 Verificando archivos de log...")

    # Obtener directorio de logs
    logger = get_main_logger()
    log_dir = logger.log_dir

    print(f"📂 Directorio de logs: {log_dir}")

    # Listar archivos generados
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log")) + list(log_dir.glob("*.json"))
        print(f"📄 Archivos de log encontrados: {len(log_files)}")

        for log_file in log_files:
            if log_file.exists():
                size = log_file.stat().st_size
                print(f"  📋 {log_file.name}: {size} bytes")

                # Verificar contenido de archivos JSON
                if log_file.suffix == '.json' and size > 0:
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            first_line = f.readline().strip()
                            if first_line:
                                log_entry = json.loads(first_line)
                                print(f"    📝 Ejemplo de entrada: {log_entry.get('level', 'N/A')} - {log_entry.get('message', 'N/A')[:50]}...")
                    except Exception as e:
                        print(f"    ⚠️ Error leyendo JSON: {e}")
    else:
        print("⚠️ Directorio de logs no existe aún")

    print("✅ Verificación de archivos completada")

def test_error_handling():
    """Prueba manejo avanzado de errores"""
    print("🧪 Probando manejo de errores...")

    # Usar context manager para captura de errores
    with log_errors("test_error_context", "main") as logger:
        logger.info("Dentro del contexto de manejo de errores")
        # Esta línea causará un error
        raise ConnectionError("Error de conexión simulado")

    print("✅ Manejo de errores completado")

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas del sistema de logging mejorado")
    print("=" * 60)

    try:
        test_basic_logging()
        print()

        test_operation_context()
        print()

        test_specialized_loggers()
        print()

        test_decorators()
        print()

        test_performance_tracking()
        print()

        test_log_files()
        print()

        # Esta prueba debe ir al final porque puede terminar con error
        try:
            test_error_handling()
        except ConnectionError:
            print("✅ Manejo de errores completado (error esperado capturado)")
        print()

        print("=" * 60)
        print("🎉 Todas las pruebas de logging completadas exitosamente!")

        # Generar reporte final de rendimiento
        perf_logger = get_performance_logger()
        summary = perf_logger.get_performance_summary()

        if summary:
            print("\n📊 REPORTE FINAL DE RENDIMIENTO:")
            for metric, stats in summary.items():
                print(f"  📈 {metric}:")
                print(f"    • Promedio: {stats['avg']:.2f}")
                print(f"    • Mínimo: {stats['min']:.2f}")
                print(f"    • Máximo: {stats['max']:.2f}")
                print(f"    • Total: {stats['total']:.2f}")
                print(f"    • Conteo: {stats['count']}")

    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()