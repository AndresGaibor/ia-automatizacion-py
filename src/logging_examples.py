#!/usr/bin/env python3
"""
Ejemplos de uso del sistema de logging estructurado mejorado para acumba-automation

Este archivo muestra cómo usar las nuevas funciones de logging estructurado
que combinan la funcionalidad del logger existente con mejoras modernas.
"""

import time
from .structured_logger import (
    log_success, log_error, log_warning, log_info, log_performance,
    log_data_extraction, log_api_call, log_file_operation, log_browser_action,
    log_checkpoint, log_batch_summary, log_operation, timer_decorator,
    start_timer, end_timer
)

def ejemplo_logging_basico():
    """Ejemplos de logging básico con contexto estructurado"""
    print("=== Ejemplos de Logging Básico ===")
    
    # Logs básicos con contexto
    log_info("Iniciando proceso de ejemplo", user="admin", version="1.2.3")
    log_success("Conexión establecida exitosamente", server="api.acumbamail.com", port=443)
    log_warning("Rate limit cercano", requests_remaining=5, limit=100)
    log_error("Error de validación", field="email", value="invalid-email", error_code="E001")

def ejemplo_performance_tracking():
    """Ejemplos de tracking de performance"""
    print("\n=== Ejemplos de Performance Tracking ===")
    
    # Timing manual
    start_timer("operacion_manual")
    time.sleep(1)  # Simular trabajo
    elapsed = end_timer("operacion_manual", items_processed=100, status="success")
    
    # Usando el decorador
    @timer_decorator("procesamiento_automatico")
    def procesar_datos():
        time.sleep(0.5)  # Simular procesamiento
        return {"items": 50, "status": "completed"}
    
    resultado = procesar_datos()
    log_info("Datos procesados", **resultado)

def ejemplo_context_manager():
    """Ejemplo de context manager para operaciones complejas"""
    print("\n=== Ejemplo de Context Manager ===")
    
    # Operación exitosa
    with log_operation("autenticacion", user="test@example.com", method="oauth"):
        time.sleep(0.3)  # Simular autenticación
        log_info("Token obtenido", expires_in=3600)
    
    # Operación con error
    try:
        with log_operation("operacion_fallida", retry_count=1):
            time.sleep(0.2)
            raise ValueError("Error simulado para demostración")
    except ValueError:
        pass  # Error ya fue loggeado por el context manager

def ejemplo_logging_especializado():
    """Ejemplos de logging especializado para diferentes tipos de operaciones"""
    print("\n=== Ejemplos de Logging Especializado ===")
    
    # API calls
    log_api_call("/api/v1/campaigns", "GET", 200, response_time=0.245)
    log_api_call("/api/v1/lists", "POST", 429, retry_after=30)
    
    # Extracción de datos
    log_data_extraction("campañas", 25, "API", query_time=1.2)
    log_data_extraction("suscriptores", 1500, "scraping", page_count=15)
    
    # Operaciones de archivos
    log_file_operation("crear", "/data/campanas_20250923.xlsx", 2048576, sheets=5)
    log_file_operation("leer", "/config/config.yaml", 1024)
    
    # Acciones del navegador
    log_browser_action("click", "button[data-action='login']", page_url="https://acumbamail.com/login")
    log_browser_action("navigate", url="https://acumbamail.com/dashboard")
    
    # Checkpoints importantes
    log_checkpoint("configuracion_completa", progress="3/5 pasos completados")
    log_checkpoint("datos_validados", validation_errors=0)

def ejemplo_batch_processing():
    """Ejemplo de logging para procesamiento por lotes"""
    print("\n=== Ejemplo de Batch Processing ===")
    
    # Simular procesamiento de múltiples campañas
    total_campaigns = 10
    successful = 8
    failed = 2
    total_time = 45.6
    
    log_batch_summary(
        "procesamiento_campañas", 
        total_campaigns, 
        successful, 
        failed, 
        total_time,
        source="api+scraping",
        files_created=successful
    )

def ejemplo_logging_con_metricas():
    """Ejemplo de logging con métricas detalladas"""
    print("\n=== Ejemplo de Logging con Métricas ===")
    
    # Simular diferentes niveles de performance
    log_performance("query_rapida", 0.5, rows_affected=100, cache_hit=True)
    log_performance("query_normal", 3.2, rows_affected=1000, cache_hit=False)
    log_performance("query_lenta", 8.7, rows_affected=50000, optimization_needed=True)

def main():
    """Ejecuta todos los ejemplos"""
    print("🚀 Demostrando el nuevo sistema de logging estructurado")
    print("=" * 60)
    
    ejemplo_logging_basico()
    ejemplo_performance_tracking()
    ejemplo_context_manager()
    ejemplo_logging_especializado()
    ejemplo_batch_processing()
    ejemplo_logging_con_metricas()
    
    print("\n" + "=" * 60)
    log_success("Todos los ejemplos completados exitosamente", 
               examples_run=6, total_logs_generated=25)

if __name__ == "__main__":
    main()