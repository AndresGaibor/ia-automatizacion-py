# Sistema de Logging Estructurado - Acumba Automation

## Visión General

El proyecto acumba-automation ahora cuenta con un sistema de logging profesional que combina:

- **Logging estructurado** con contexto JSON para producción
- **Logs visuales** con emojis y colores para desarrollo 
- **Tracking de performance** automático
- **Compatibilidad** con el logger existente
- **Observabilidad** mejorada para debugging y monitoreo

## Arquitectura del Sistema

### Componentes Principales

1. **`src/logger.py`** - Logger original con performance tracking
2. **`src/structured_logger.py`** - Nuevo logger estructurado con structlog/rich
3. **`src/logging_examples.py`** - Ejemplos de uso y patrones

### Librerías Utilizadas

- **structlog**: Logging estructurado moderno
- **rich**: Formateo visual y colores en terminal
- **pythonjsonlogger**: Salida JSON para producción
- **colorama**: Compatibilidad de colores cross-platform

## Uso Básico

### Importación

```python
from .structured_logger import (
    log_success, log_error, log_warning, log_info, 
    log_performance, log_data_extraction, log_api_call,
    log_operation, timer_decorator
)
```

### Logging Básico con Contexto

```python
# Información general
log_info("Procesando campaña", campania_id="123", nombre="Newsletter Q4")

# Éxito con métricas
log_success("Datos extraídos", total_records=1500, time_elapsed=2.3)

# Errores con contexto
log_error("Error de conexión", endpoint="/api/campaigns", retry_count=3)

# Advertencias
log_warning("Rate limit cercano", requests_remaining=5, limit=100)
```

### Performance Tracking

```python
# Timing manual
start_timer("procesamiento_datos")
# ... hacer trabajo ...
elapsed = end_timer("procesamiento_datos", items_processed=100)

# Decorador automático
@timer_decorator("operacion_compleja")
def procesar_campana(campana_id):
    # función será cronometrada automáticamente
    pass

# Context manager para operaciones
with log_operation("autenticacion", user="admin"):
    # código de autenticación
    # logs automáticos de inicio/fin con timing
    pass
```

### Logging Especializado

```python
# Llamadas a API
log_api_call("/api/v1/campaigns", "GET", 200, response_time=0.245)

# Extracción de datos
log_data_extraction("suscriptores", 1500, "scraping", page_count=15)

# Operaciones de archivos
log_file_operation("crear", "reporte.xlsx", 2048576, sheets=5)

# Acciones del navegador
log_browser_action("click", "button.login", page_url="https://app.com")

# Resúmenes de lotes
log_batch_summary("procesamiento", 10, 8, 2, 45.6, source="hybrid")
```

## Configuración

### Variables de Entorno

```bash
# Nivel de logging
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Formato de salida
export LOG_FORMAT=dev   # 'dev' para desarrollo, 'json' para producción
```

### Configuración en Desarrollo

```bash
# Logs coloridos y legibles en terminal
export LOG_FORMAT=dev
export LOG_LEVEL=DEBUG
```

### Configuración en Producción

```bash
# Logs JSON estructurados
export LOG_FORMAT=json
export LOG_LEVEL=INFO
```

## Ejemplo de Salida

### Formato Desarrollo (dev)

```
ℹ️ 2025-09-23T10:30:15 Procesando campaña [campania_id=123] [nombre=Newsletter Q4]
📊 2025-09-23T10:30:16 DATOS: Extraídos 1500 de suscriptores desde scraping [page_count=15]
⏱️ 2025-09-23T10:30:18 procesamiento_datos - 2.34s [NORMAL] [items_processed=100]
✅ 2025-09-23T10:30:18 Archivo Excel creado exitosamente [archivo=reporte.xlsx] [sheets=5]
```

### Formato Producción (json)

```json
{"timestamp": "2025-09-23T10:30:15.123Z", "level": "info", "message": "Procesando campaña", "campania_id": "123", "nombre": "Newsletter Q4"}
{"timestamp": "2025-09-23T10:30:16.456Z", "level": "info", "message": "DATOS: Extraídos 1500 de suscriptores desde scraping", "data_type": "suscriptores", "count": 1500, "source": "scraping", "page_count": 15}
{"timestamp": "2025-09-23T10:30:18.789Z", "level": "info", "message": "procesamiento_datos - 2.34s [NORMAL]", "operation": "procesamiento_datos", "elapsed_seconds": 2.34, "performance_grade": "NORMAL", "items_processed": 100}
```

## Migración desde Logger Existente

### Compatibilidad

El nuevo sistema es **compatible** con el logger existente. Puedes:

1. **Usar ambos sistemas** lado a lado
2. **Migrar gradualmente** función por función
3. **Mantener** el logger original para compatibilidad

### Ejemplo de Migración

```python
# Antes (logger original)
get_logger().info(f"📊 Procesando {nombre_campania}")
get_logger().info(f"✅ Completado en {elapsed:.2f}s")

# Después (logger estructurado)
log_info("Procesando campaña", nombre=nombre_campania, campania_id=id)
log_success("Campaña procesada", elapsed_seconds=elapsed, nombre=nombre_campania)
```

## Beneficios del Nuevo Sistema

### Para Desarrollo

- **Logs visuales** con emojis y colores
- **Contexto estructurado** fácil de leer
- **Performance automático** con grades de velocidad
- **Context managers** para operaciones complejas

### Para Producción

- **JSON estructurado** para análisis automatizado
- **Métricas integradas** de performance
- **Contexto consistente** en todos los logs
- **Compatibilidad** con sistemas de monitoreo

### Para Debugging

- **Contexto rico** en cada log entry
- **Timing automático** de operaciones
- **Rastreo de errores** con contexto completo
- **Patrones de uso** claros y consistentes

## Patrones Recomendados

### 1. Operaciones de Campaña

```python
with log_operation("procesamiento_campana", campana_id=id, nombre=nombre):
    log_info("Obteniendo datos básicos", source="API")
    datos_basicos = obtener_datos_campana(id)
    
    log_info("Ejecutando scraping", target="hard_bounces")
    datos_scraping = ejecutar_scraping(id)
    
    log_data_extraction("hard_bounces", len(datos_scraping.hard_bounces), "scraping")
    log_success("Campaña procesada", total_datos=len(datos_basicos + datos_scraping))
```

### 2. Operaciones de API

```python
@timer_decorator("api_call_subscribers")
def obtener_suscriptores(lista_id):
    log_api_call(f"/api/lists/{lista_id}/subscribers", "GET")
    try:
        response = api.get_subscribers(lista_id)
        log_success("Suscriptores obtenidos", lista_id=lista_id, count=len(response))
        return response
    except Exception as e:
        log_error("Error obteniendo suscriptores", lista_id=lista_id, error=str(e))
        raise
```

### 3. Procesamiento por Lotes

```python
start_time = time.time()
successful = 0
failed = 0

for i, campana in enumerate(campanas):
    try:
        procesar_campana(campana)
        successful += 1
        log_info(f"Campaña {i+1}/{len(campanas)} procesada", campana_id=campana.id)
    except Exception as e:
        failed += 1
        log_error("Error procesando campaña", campana_id=campana.id, error=str(e))

total_time = time.time() - start_time
log_batch_summary("procesamiento_campanas", len(campanas), successful, failed, total_time)
```

## Próximos Pasos

1. **Migrar** gradualmente funciones críticas al nuevo sistema
2. **Configurar** variables de entorno según el ambiente
3. **Usar** context managers para operaciones complejas
4. **Aprovechar** el contexto estructurado para mejores insights
5. **Implementar** dashboards basados en logs JSON para monitoreo

El nuevo sistema mantiene toda la funcionalidad del logger original mientras añade capacidades modernas de observabilidad y estructura para un mejor debugging y monitoreo en producción.