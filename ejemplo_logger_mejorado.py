#!/usr/bin/env python3
"""
Ejemplo de uso del sistema de logging mejorado
Demuestra las nuevas funcionalidades implementadas
"""

import time
import random
from src.logger import (
    get_logger, get_minimal_logger, get_normal_logger, get_verbose_logger,
    ErrorSeverity, LogLevel
)


def ejemplo_operacion_simple():
    """Ejemplo básico de logging con diferentes niveles de verbosidad"""
    print("=== EJEMPLO 1: Diferentes niveles de verbosidad ===\n")

    # Logger mínimo - solo errores críticos y resúmenes
    logger_min = get_minimal_logger()
    print("🔹 Logger MÍNIMO (verbose_level=1):")
    logger_min.start_timer("operacion_simple")
    time.sleep(0.1)
    logger_min.log_checkpoint("checkpoint_test", "Este checkpoint NO aparecerá")
    logger_min.log_heartbeat("heartbeat_test", "Este heartbeat NO aparecerá")
    logger_min.end_timer("operacion_simple")

    # Logger normal - balance entre detalle y ruido
    logger_normal = get_normal_logger()
    print("\n🔹 Logger NORMAL (verbose_level=3):")
    logger_normal.start_timer("operacion_normal")
    time.sleep(0.1)
    logger_normal.log_checkpoint("checkpoint_important", "Checkpoint importante SÍ aparece")
    logger_normal.log_heartbeat("heartbeat_normal", "Heartbeat moderado")
    logger_normal.end_timer("operacion_normal")

    # Logger verbose - máximo detalle
    logger_verbose = get_verbose_logger()
    print("\n🔹 Logger VERBOSE (verbose_level=5):")
    logger_verbose.start_timer("operacion_verbose")
    time.sleep(0.1)
    logger_verbose.log_checkpoint("checkpoint_detail", "Todos los checkpoints aparecen")
    logger_verbose.log_browser_action("navegacion", "ejemplo.com", "Acción detallada")
    logger_verbose.log_heartbeat("heartbeat_verbose", "Heartbeats frecuentes")
    logger_verbose.end_timer("operacion_verbose")


def ejemplo_clasificacion_errores():
    """Ejemplo de clasificación inteligente de errores"""
    print("\n\n=== EJEMPLO 2: Clasificación inteligente de errores ===\n")

    logger = get_logger()

    # Diferentes tipos de errores
    print("🔹 Errores ESPERADOS (ej: cookies, límites de plan):")
    try:
        raise TimeoutError("Botón de cookies no encontrado")
    except Exception as e:
        logger.log_error("accept_cookies", e, "Elemento opcional", ErrorSeverity.EXPECTED)

    print("\n🔹 Errores RECUPERABLES (se pueden reintentar):")
    try:
        raise ConnectionError("Conexión temporal perdida")
    except Exception as e:
        logger.log_error("network_request", e, "Reintentando...", ErrorSeverity.RECOVERABLE)

    print("\n🔹 Errores TÉCNICOS (selectores, cambios UI):")
    try:
        raise ValueError("Selector '.old-button' no encontrado")
    except Exception as e:
        logger.log_error("ui_interaction", e, "Posible cambio en UI", ErrorSeverity.TECHNICAL)

    print("\n🔹 Errores CRÍTICOS (detienen el proceso):")
    try:
        raise RuntimeError("Fallo crítico del sistema")
    except Exception as e:
        logger.log_error("system_critical", e, "Proceso detenido", ErrorSeverity.CRITICAL)


def ejemplo_agrupacion_operaciones():
    """Ejemplo de agrupación inteligente de operaciones"""
    print("\n\n=== EJEMPLO 3: Agrupación inteligente de operaciones ===\n")

    logger = get_logger()

    # Simular navegación de páginas (antes: 25 logs individuales)
    print("🔹 ANTES: Cada página generaba un log individual")
    print("🔹 AHORA: Agrupación inteligente con resumen al final")

    # Iniciar operación por lotes
    total_paginas = 5
    logger.start_batch_operation('navegacion_paginas', 'navigation', total_paginas)

    for i in range(1, total_paginas + 1):
        # Simular navegación
        logger.start_timer(f"navegar_pagina_{i}", batch_key='navegacion_paginas')
        time.sleep(random.uniform(0.1, 0.3))  # Simular tiempo variable
        logger.end_timer(f"navegar_pagina_{i}", f"Página {i} completada", batch_key='navegacion_paginas')

        # Simular progreso inteligente (no cada página)
        logger.log_progress(i, total_paginas, "navegación páginas")

    # Finalizar y obtener resumen
    summary = logger.end_batch_operation('navegacion_paginas')
    print(f"\n📊 Resumen recibido: {summary['performance_grade']} grade, {summary['success_rate']:.1f}% éxito")


def ejemplo_deteccion_problemas():
    """Ejemplo de detección proactiva de problemas"""
    print("\n\n=== EJEMPLO 4: Detección proactiva de problemas ===\n")

    logger = get_logger()

    print("🔹 Simulando errores repetitivos para detectar problemas de UI...")

    # Simular el mismo error varias veces (detectará cambio de UI)
    for i in range(4):
        try:
            raise TimeoutError("Locator '.submit-button' timeout exceeded")
        except Exception as e:
            logger.log_error("submit_form", e, f"Intento {i+1}", ErrorSeverity.TECHNICAL)
            time.sleep(0.1)

    print("\n🔹 Simulando degradación de performance...")

    # Simular degradación de performance
    logger.start_timer("operacion_lenta_1")
    time.sleep(0.05)  # Operación rápida inicial
    logger.end_timer("operacion_lenta_1")

    # Misma operación pero más lenta (debería detectar degradación)
    logger.start_timer("operacion_lenta_1")
    time.sleep(0.15)  # 3x más lenta
    logger.end_timer("operacion_lenta_1")


def ejemplo_progreso_mejorado():
    """Ejemplo de cálculo de progreso mejorado"""
    print("\n\n=== EJEMPLO 5: Progreso mejorado (antes 0.0% siempre) ===\n")

    logger = get_logger()

    # Simular procesamiento con progreso real
    total_items = 23
    print(f"🔹 Procesando {total_items} elementos...")

    for i in range(1, total_items + 1):
        # Simular trabajo
        time.sleep(0.01)

        # El progreso ahora es inteligente (no cada item)
        logger.log_progress(i, total_items, "procesamiento items")


def ejemplo_reporte_estructurado():
    """Ejemplo de reporte de performance estructurado"""
    print("\n\n=== EJEMPLO 6: Reporte estructurado mejorado ===\n")

    logger = get_logger()

    # Simular varias operaciones para el reporte
    for op_type in ['login', 'navegacion', 'extraccion']:
        for i in range(3):
            logger.start_timer(f"{op_type}_{i+1}")
            time.sleep(random.uniform(0.02, 0.08))
            logger.end_timer(f"{op_type}_{i+1}")

    # Mostrar reporte mejorado
    print("🔹 Reporte de performance estructurado:")
    logger.print_performance_report(show_in_console=True)


if __name__ == "__main__":
    print("🚀 DEMO: Sistema de Logging Mejorado\n")
    print("Este ejemplo demuestra las mejoras implementadas:")
    print("• Reducción de verbosidad con niveles configurables")
    print("• Clasificación inteligente de errores")
    print("• Agrupación de operaciones similares")
    print("• Detección proactiva de problemas UI/performance")
    print("• Cálculo correcto de progreso")
    print("• Reportes estructurados\n")

    ejemplo_operacion_simple()
    ejemplo_clasificacion_errores()
    ejemplo_agrupacion_operaciones()
    ejemplo_deteccion_problemas()
    ejemplo_progreso_mejorado()
    ejemplo_reporte_estructurado()

    print("\n✅ Demo completada. Revisa los logs para ver las diferencias!")