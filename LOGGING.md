# Sistema de Logging Avanzado - Acumba Automation

## 🎯 Resumen Ejecutivo

He implementado un **sistema de logging comprehensivo y estructurado** que sigue las mejores prácticas de 2025. El sistema incluye:

✅ **Logs por funcionalidad específica**
✅ **Formato JSON estructurado** para análisis
✅ **Tracking de operaciones** con contexto completo
✅ **Métricas de rendimiento** automáticas
✅ **Manejo avanzado de errores** con stack traces
✅ **Rotación automática** de archivos de log

---

## 📂 Estructura de Archivos de Log

```
data/logs/
├── main_YYYYMMDD.log          # Log principal (texto legible)
├── main_YYYYMMDD.json         # Log principal (JSON estructurado)
├── auth_YYYYMMDD.log          # Autenticación específica
├── auth_YYYYMMDD.json         # Autenticación (JSON)
├── crear_lista_YYYYMMDD.log   # Funcionalidad crear lista
├── crear_lista_YYYYMMDD.json  # Crear lista (JSON)
├── listar_campanias_YYYYMMDD.log # Listar campañas
├── listar_campanias_YYYYMMDD.json # Listar campañas (JSON)
├── browser_YYYYMMDD.log       # Acciones del navegador
├── browser_YYYYMMDD.json      # Navegador (JSON)
├── performance_YYYYMMDD.log   # Métricas de rendimiento
├── performance_YYYYMMDD.json  # Rendimiento (JSON)
└── errors_YYYYMMDD.log        # Solo errores críticos
```

---

## 🚀 Nuevas Características

### 1. **Logging Estructurado JSON**

Cada entrada de log incluye campos consistentes:

```json
{
  "timestamp": "2025-09-15T12:18:43.351319",
  "level": "INFO",
  "logger": "acumba.auth",
  "message": "✅ Login completado exitosamente",
  "module": "autentificacion",
  "function": "login",
  "line": 82,
  "thread": "MainThread",
  "session_id": "e597ea79",
  "operation_id": "abc12345",
  "duration_ms": 1250.5,
  "context": {
    "username": "user***",
    "login_method": "standard"
  }
}
```

### 2. **Tracking de Operaciones Completas**

```python
from src.enhanced_logger import get_auth_logger

logger = get_auth_logger()

# Context manager automático
with logger.operation("login_process", {"user": "admin"}) as op:
    op.log_progress("Validando credenciales")
    # ... código de login ...
    op.log_progress("Login exitoso", 100, 100)
# Automáticamente loggea tiempo total y resultado
```

### 3. **Logs por Funcionalidad**

```python
# Cada módulo tiene su logger específico
from src.enhanced_logger import (
    get_auth_logger,          # Autenticación
    get_crear_lista_logger,   # Crear listas
    get_browser_logger,       # Navegador
    get_performance_logger    # Rendimiento
)

# Usar en tu código
auth_logger = get_auth_logger()
auth_logger.info("Usuario autenticado", context={"user_id": "123"})
```

### 4. **Métricas de Rendimiento Automáticas**

```python
logger = get_performance_logger()

# Log de métricas personalizadas
logger.log_performance_metric("response_time", 250.5, "ms")
logger.log_performance_metric("memory_usage", 128, "MB")

# Obtener resumen automático
summary = logger.get_performance_summary()
print(f"Tiempo promedio: {summary['response_time']['avg']:.2f}ms")
```

### 5. **Decoradores para Logging Automático**

```python
from src.enhanced_logger import log_operation

@log_operation("buscar_campania", "main")
def buscar_campania_por_termino(page, termino, buscador):
    # Tu código aquí...
    pass
# Automáticamente loggea inicio, fin, duración y errores
```

---

## 🔧 Cómo Usar el Nuevo Sistema

### Actualizar Módulos Existentes

1. **Importar el nuevo logger:**
```python
from .enhanced_logger import get_crear_lista_logger, log_operation
```

2. **Usar en funciones:**
```python
@log_operation("nombre_operacion", "crear_lista")
def mi_funcion():
    logger = get_crear_lista_logger()
    logger.info("Iniciando operación", context={"param": "value"})

    try:
        # Tu código aquí
        logger.log_success("Operación completada")
    except Exception as e:
        logger.error("Error en operación", error=e)
        raise
```

3. **Para operaciones largas:**
```python
def procesar_archivo(archivo):
    logger = get_crear_lista_logger()

    with logger.operation("procesar_archivo", {"file": archivo}) as op:
        op.log_progress("Leyendo archivo")
        # ... código ...
        op.log_progress("Procesando datos", 50, 100)
        # ... más código ...
        op.log_progress("Guardando resultados", 100, 100)
```

### Logs Especializados

```python
# Acciones del navegador
browser_logger = get_browser_logger()
browser_logger.log_browser_action("Navegando", "https://example.com")

# Operaciones de archivos
logger.log_file_operation("Leyendo", "/path/file.xlsx", 1024)

# Extracción de datos
logger.log_data_extraction("usuarios", 150, "base de datos")
```

---

## 📊 Análisis y Monitoreo

### 1. **Archivos JSON para Análisis**

Los archivos `.json` pueden ser procesados con herramientas como:
- **jq** para consultas en línea de comandos
- **Elasticsearch/Kibana** para análisis avanzado
- **Scripts Python** para reportes personalizados

### 2. **Consultas de Ejemplo**

```bash
# Ver todos los errores del día
jq 'select(.level == "ERROR")' data/logs/main_20250915.json

# Operaciones más lentas
jq 'select(.duration_ms) | {operation: .operation_id, duration: .duration_ms}' data/logs/*_20250915.json | sort -k2 -nr

# Errores por módulo
jq -r 'select(.level == "ERROR") | .module' data/logs/*_20250915.json | sort | uniq -c
```

### 3. **Métricas de Rendimiento**

```python
from src.enhanced_logger import get_performance_logger

logger = get_performance_logger()
summary = logger.get_performance_summary()

for metric, stats in summary.items():
    print(f"{metric}: avg={stats['avg']:.2f}, max={stats['max']:.2f}")
```

---

## 🛡️ Manejo de Errores Mejorado

### Context Manager para Errores

```python
from src.enhanced_logger import log_errors

with log_errors("operacion_critica", "main") as logger:
    # Tu código aquí
    raise ConnectionError("Error de red")
# Automáticamente captura y loggea el error con contexto completo
```

### Información de Errores Enriquecida

Cada error incluye:
- ✅ **Stack trace completo**
- ✅ **Contexto de la operación**
- ✅ **Tiempo hasta el fallo**
- ✅ **Información del hilo y sesión**

---

## 🔄 Migración Gradual

### Compatibilidad con Sistema Anterior

El nuevo sistema **mantiene compatibilidad** con el logger existente:

```python
# Código anterior sigue funcionando
from .logger import get_logger
logger = get_logger()
logger.start_timer("operacion")
# ...
logger.end_timer("operacion")

# Nuevo código usa sistema mejorado
from .enhanced_logger import get_main_logger
logger = get_main_logger()
with logger.operation("operacion") as op:
    # ...
```

### Estrategia de Migración

1. **Mantener sistema actual** funcionando
2. **Agregar nuevo logging** gradualmente
3. **Migrar módulo por módulo** según prioridad
4. **Eventual deprecación** del sistema anterior

---

## 📋 Configuración Avanzada

### Niveles de Log por Ambiente

```python
# Desarrollo: DEBUG y superior
# Producción: INFO y superior
# Solo errores críticos van a consola

logger.debug("Información detallada")     # Solo en archivos
logger.info("Operación normal")           # Archivos
logger.warning("Situación anómala")       # Archivos + consola
logger.error("Error que requiere atención") # Archivos + consola + errors.log
```

### Rotación Automática

- ✅ **Archivos de 50MB** máximo
- ✅ **5 archivos de backup** automáticos
- ✅ **Logs diarios** con timestamp

---

## 🎉 Beneficios Implementados

### ✅ **Para Debugging**
- Stack traces completos con contexto
- Tracking de operaciones end-to-end
- Métricas de rendimiento automáticas

### ✅ **Para Monitoreo**
- Archivos JSON parseables
- Logs por funcionalidad específica
- Alertas automáticas en errores críticos

### ✅ **Para Análisis**
- Datos estructurados consistentes
- Métricas de rendimiento históricas
- Correlación entre operaciones

### ✅ **Para Mantenimiento**
- Rotación automática de archivos
- Configuración centralizada
- Compatibilidad hacia atrás

---

## 🚀 Próximos Pasos Recomendados

1. **Implementar en módulos críticos** (autenticación, navegador)
2. **Configurar alertas** para errores críticos
3. **Crear dashboards** de métricas de rendimiento
4. **Automatizar análisis** de logs diarios

¿Te gustaría que implemente alguna característica adicional o que migre algún módulo específico al nuevo sistema?