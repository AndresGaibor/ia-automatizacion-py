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

### I-011: Import relativos fallan en ejecución directa de módulos
**Archivos:** `src/infrastructure/excel/campaign_report_exporter.py` (inicialmente)
**Riesgo:** Medio (descubierto durante implementación)
**Descripción:** Los imports relativos `....core.dto` fallan con `ImportError: beyond top-level package` cuando el módulo se ejecuta directamente. Solución: usar imports absolutos `src.core.dto`.

### I-012: `_safe_diff` necesita manejar formato con puntos
**Archivos:** `src/core/dto/campaign_summary.py`
**Riesgo:** Bajo (mitigado durante implementación)
**Descripción:** Los valores de `total_enviado` y `abierto` pueden contener dots (`5.000`). El cálculo `int(a) - int(b)` falla sin `.replace(".", "")`. Ya corregido en `_safe_diff`.

### I-013: `no_abierto` puede ser negativo sin clamping
**Archivos:** `src/core/dto/campaign_summary.py` (`_safe_diff`)
**Riesgo:** Bajo (preservación de contrato)
**Descripción:** Para preservar comportamiento exacto del runtime actual, `_safe_diff` NO clampa valores negativos. Si `abierto > total_enviado` (datos corruptos), `no_abierto` será negativo (ej. `-100`). El código original `listar_campanias.py:186` hace exactamente `int(total_enviado) - int(abierto)` sin validación. Esto se preserva intencionalmente en el DTO.

### I-014: Duplicación de lógica de autenticación entre `autentificacion.py` y POM Components
**Archivos:** `src/autentificacion.py` vs `src/infrastructure/scraping/components/` + `flows/auth_flow.py`
**Riesgo:** Medio (mantenimiento)
**Descripción:** La lógica de login, cookies y verificación existe duplicada: una vez en `autentificacion.py` (activo) y otra en los nuevos Components/Flows POM. Esto es intencional para la fase de transición — `autentificacion.py` preserva comportamiento, los nuevos POM pieces son infraestructura para migración futura. Se debe eliminar la duplicación cuando se migre completamente al flujo POM.

## 2026-04-07 — Task 8 issues

### I-020: `wait_for_timeout(2000)` persiste en FilterSelectorComponent
**Archivos:** `filter_selector.py:27`, `subscribers_page.py:63`
**Riesgo:** Medio
**Descripción:** El `wait_for_timeout(2000)` después de `select_option` y `wait_for_load_state` persiste como hardcoded wait. Esto es necesaria para esperar que la tabla se actualice después del filtro, pero viola el principio de no usar esperas fijas. La alternativa (auto-waiting de Playwright) no funciona aquí porque el filtro cambia el contenido dinámicamente sin señal clara.

### I-021: Test import path pre-existente incorrecto
**Archivos:** `tests/integration/test_scraping_suscriptores.py:9`
**Riesgo:** Bajo (pre-existente)
**Descripción:** El test importa `from src.scraping.endpoints.suscriptores` pero el módulo real está en `src.infrastructure.scraping.endpoints.suscriptores`. Esto es un problema pre-existente al task 8. El test necesita actualizarse a `from src.infrastructure.scraping.endpoints.suscriptores import SubscribersScraper`.

### I-022: No se agregó session recovery en SubscribersFlow
**Archivos:** `subscribers_flow.py`
**Riesgo:** Bajo (por diseño)
**Descripción:** No se integró `ScrapingSession.run_with_recovery()` dentro de `SubscribersFlow` porque `HybridDataService._extract_scraping_data()` ya maneja la re-autenticación a nivel de servicio. Agregar双重 retry complicaría el flujo sin beneficio adicional.

### I-023: `SubscribersFlow.extract_filter()` nunca invocaba `select_fn` (BUG — FIXED)
**Archivos:** `flows/subscribers_flow.py` (antes de fix)
**Riesgo:** Crítico (bug en task 8 original)
**Descripción:** El mapa de filtros recuperaba `select_fn` del diccionario pero NUNCA lo llamaba antes de paginar. La tabla se iteraba sin filtro aplicado. Fix: agregar `select_fn()` justo después de resolverlo, seguido de `wait_for_table()`.

### I-024: `SubscribersScraper.extraer_suscriptores_completos` no delegaba al POM flow (BUG — FIXED)
**Archivos:** `endpoints/suscriptores.py` (antes de fix)
**Riesgo:** Crítico (el público API iba por código procedural, no por flow)
**Descripción:** El método público `extraer_suscriptores_completos` usaba los métodos procedurales (`extraer_hard_bounces`, `extraer_no_abiertos`, `extraer_suscriptores_optimizado`) directamente. `SubscribersFlow` existía pero nunca era llamado desde el entry point público. Fix: `extraer_suscriptores_completos` ahora crea `SubscribersFlow(page)` y delega a `extract_hard_bounces_and_no_abiertos`.

### I-025: Condición incorrecta en `extract_hard_bounces_and_no_abiertos` (BUG — FIXED)
**Archivos:** `flows/subscribers_flow.py` (antes de fix)
**Riesgo:** Alto (silently droppea hard bounces cuando use_optimized=False)
**Descripción:** La condición `if config.extract_hard_bounces and config.use_optimized_extraction` hacía que hard bounces nunca se extrajera cuando `use_optimized=False`. El código original tenía dos ramas (optimized vs non-optimized) con lógica idéntica — `use_optimized` controlaba single-pass vs two-pass, NO si se extraía. Fix: separar en dos ramas que invocan `extract_filter` condicionalmente según `extract_*` flags.

### I-026: `extraer_datos_filtro` navegaba a campaign_id=0 (BUG — FIXED)
**Archivos:** `endpoints/suscriptores.py` (antes de fix)
**Riesgo:** Crítico (navegación a URL inválida)
**Descripción:** `CampaignBasicInfo` NO tiene atributo `campaign_id`. `hasattr(campania, "campaign_id")` siempre era `False`, causando `navegar_a_detalle_suscriptores(page, campaign_id=0)` — navegando a `/report/campaign/0/`. El contrato original de `extraer_datos_filtro` era helper de extracción puro, sin navegación. Fix: wrapper delgado sin navegación, `flow.extract_filter(campania, 0, filter_type)`. El `0` es dummy para el objeto resultado, no para navegación.
