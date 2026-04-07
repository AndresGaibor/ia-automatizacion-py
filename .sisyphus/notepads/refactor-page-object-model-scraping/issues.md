# Issues — Refactor Page Object Model (Scraping)

## 2026-04-07 — Issues y riesgos detectados en el flujo actual

### I-001: Selectores frágiles — `div.am-responsive-table-cell` con índices fijos
**Archivos:** `src/listar_campanias.py` líneas 149, 155, 165, 175
**Riesgo:** Alto
**Descripción:** Los selectores usan `nth(2)`, `nth(4)`, `nth(5)`, `nth(6)` asumiendo un orden fijo de columnas. Si Acumbamail cambia el orden/agrega columnas, la extracción se rompe silenciosamente (extrae datos de columna equivocada).

### I-002: `time.sleep` / `wait_for_timeout` hardcoded
**Archivos:** `src/utils.py` líneas 237, 258, 384; `src/listar_campanias.py` líneas 238, 434, 484, 491, 529
**Riesgo:** Medio
**Descripción:** Múltiples esperas fijas de 1000-3000ms en lugar de usar auto-waiting de Playwright. Esto hace el scraping lento y frágil ante variaciones de red. El AGENTS.md dice explícitamente: NO usar `time.sleep()`.

### I-003: `is_on_login_page` importado de `shared.utils.legacy_utils`
**Archivos:** `src/listar_campanias.py` línea 21
**Riesgo:** Bajo (consistencia)
**Descripción:** Función de detección de sesión expirada vive en legacy_utils. Necesita ser documentada como parte del contrato de POM.

### I-004: Duplicación de lógica de paginación
**Archivos:** `src/utils.py` — `obtener_total_paginas` (240-341) vs `obtener_total_paginas_rapido` (343-361)
**Riesgo:** Bajo
**Descripción:** Dos versiones similares de la misma función. `obtener_total_paginas_rapido` no se usa actualmente en `listar_campanias.py`.

### I-005: `extraer_campanias_de_pagina` no usa el decorador `@with_session_retry`
**Archivos:** `src/listar_campanias.py` línea 219
**Riesgo:** Medio
**Descripción:** La función SÍ tiene `@with_session_retry(max_retries=2)` pero la lógica interna también maneja errores individualmente (try/except por listitem). Esto crea doble manejo que puede ser confuso.

### I-006: `get_campaign_urls_with_fallback` importado de `demo.py`
**Archivos:** `src/listar_campanias.py` línea 23
**Riesgo:** Alto (acoplamiento)
**Descripción:** La extracción de URLs depende de una función en `demo.py`, creando un acoplamiento cruzado entre módulos. El flujo de `listar_campanias.py` no es autocontenido.

### I-007: Columna "Buscar" siempre vacía
**Archivos:** `src/listar_campanias.py` línea 203
**Riesgo:** Bajo
**Descripción:** La columna `Buscar` se inicializa como `""` para todas las campañas. Esto parece ser un placeholder para UI posterior donde el usuario marca campañas a procesar.

### I-008: Cálculo de "No abierto" no valida overflow
**Archivos:** `src/listar_campanias.py` líneas 185-189
**Riesgo:** Muy bajo
**Descripción:** Si `abierto > total_enviado` (datos corruptos del servidor), el resultado sería negativo. No se valida esta condición.

### I-009: `configurar_navegador` auto-instala Playwright si no existe
**Archivos:** `src/utils.py` líneas 192-228
**Riesgo:** Bajo
**Descripción:** Llama a `playwright.__main__.main()` programáticamente, lo cual puede tener side effects inesperados en entornos de CI/testing.

### I-010: `guardar_datos_en_excel` sobrescribe `Busqueda.xlsx` con datos de campañas
**Archivos:** `src/listar_campanias.py` líneas 316-374
**Riesgo:** Alto (data loss)
**Descripción:** La función usa `ARCHIVO_BUSQUEDA` (`data/Busqueda.xlsx`) como archivo de OUTPUT. Si el usuario tenía datos previos en este archivo, se pierden completamente al ejecutar `listar_campanias.py`. Esto parece ser un error — el archivo de búsqueda (input) no debería ser el mismo que el de resultados (output).
