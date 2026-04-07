# Learnings — Refactor Page Object Model (Scraping)

## 2026-04-07 — Baseline: Flujo completo de scraping (`listar_campanias.py`)

**Archivos analizados:**
- `src/listar_campanias.py` (569 líneas) — Orquestador principal
- `src/utils.py` (511 líneas) — Utilidades de navegador, paginación, config
- `src/autentificacion.py` (453 líneas) — Login, cookies, verificación de sesión
- `src/excel_utils.py` (92 líneas) — Helpers de openpyxl

### Cadena de ejecución (`main()` → líneas 500-569)

1. **Setup navegador** (`configurar_navegador` + `crear_contexto_navegador`)
   - Chromium con `--disable-blink-features=AutomationControlled`, `--no-sandbox`
   - Contexto con UA real (Chrome 126), viewport 1366x768, timezone Europe/Madrid
   - `storage_state` se carga desde `data/datos_sesion.json` si existe (persistencia de sesión)
   - Timeouts del contexto: default=30s, navigation=60s

2. **Login** (`autentificacion.login`, líneas 313-453)
   - Navega a `config.url` con `domcontentloaded`
   - Verifica si sesión existente es válida (`verificar_login_exitoso`)
   - Maneja popup de cookies con estrategias múltiples (`manejar_popup_cookies`)
   - Si no autenticado: clic en "Entra", rellena email/password, clic en "Entrar"
   - Guarda `context.storage_state(path=storage_state_path())` tras login exitoso

3. **Navegar a reportes** (`navegar_a_reportes`, utils.py:230-238)
   - `page.click("a[href*='/reports']")`
   - `page.wait_for_load_state('networkidle', timeout=60000)`
   - `page.wait_for_timeout(2000)` — espera adicional fija

4. **Procesar todas las páginas** (`procesar_todas_las_paginas`, líneas 377-444)
   - Obtiene `total_paginas` con `obtener_total_paginas(page)`
   - Itera página 1..N:
     - `extraer_campanias_de_pagina(page)` extrae campañas de la página actual
     - Filtra duplicados globales con `ids_globales` (set de IDs)
     - Si no es última página: `navegar_siguiente_pagina_con_recuperacion(page, pagina_actual)`
     - Espera 2s tras navegación entre páginas

5. **Extraer URLs de correo** (`extraer_urls_de_campanias`, líneas 447-497)
   - Para cada campaña, llama a `get_campaign_urls_with_fallback(page, int(id_campania))` (de `demo.py`)
   - Agrega URL como última columna a cada fila
   - Espera 1s entre campañas
   - Verifica sesión expirada tras cada navegación; re-autentica si necesario

6. **Guardar en Excel** (`guardar_datos_en_excel`, líneas 316-374)
   - Carga/crea `data/Busqueda.xlsx`
   - Hoja "Sheet", limpia desde fila 1
   - Encabezados + datos
   - Ajuste automático de ancho de columnas (max 50 chars + 2 padding)

### Extracción de datos por campaña (`extraer_datos_campania_de_listitem`, líneas 122-207)

**Columnas de output (índice 0-6, sin URL):**
| Índice | Columna | Origen |
|--------|---------|--------|
| 0 | `Buscar` | String vacío `""` |
| 1 | `Nombre` | `a[href*="/report/campaign/"]` → `inner_text()` |
| 2 | `ID Campaña` | Regex `/campaign/(\d+)` del href |
| 3 | `Fecha` | `div.am-responsive-table-cell:nth(2)` → `span` |
| 4 | `Total enviado` | `div.am-responsive-table-cell:nth(4)` → `a` o `span` |
| 5 | `Abierto` | `div.am-responsive-table-cell:nth(5)` → `a` o `span` |
| 6 | `No abierto` | **Calculado**: `int(total_enviado) - int(abierto)` |

**Luego se agrega:**
| Índice | Columna | Origen |
|--------|---------|--------|
| 7 | `URL de Correo` | `get_campaign_urls_with_fallback()` |

**Encabezados finales en Excel:**
`["Buscar", "Nombre", "ID Campaña", "Fecha", "Total enviado", "Abierto", "No abierto", "URL de Correo"]`

### Paginación (`obtener_total_paginas`, utils.py:240-341)

1. **Optimiza items por página**: Intenta seleccionar el último option del dropdown (maximiza a 200)
2. **Calcula desde total de elementos**: Busca `span.font-color-darkblue-1` con regex "de X elementos"
3. **Verifica items_por_pagina real**: Lee el valor del select (parsea `items_per_page=N`)
4. **Fallback 1**: Navegación tradicional con `ul > li > a` con texto "1"
5. **Fallback 2**: Retorna 1

**Navegación siguiente página** (`navegar_siguiente_pagina`, utils.py:363-391):
- Busca enlace con texto `siguiente_pagina` en paginación
- Click → `domcontentloaded` → espera 1500ms

### Deduplicación

- **Por página**: `ids_vistos` (set) en `extraer_campanias_de_pagina` — filtra duplicados dentro de la misma página
- **Global**: `ids_globales` (set) en `procesar_todas_las_paginas` — filtra duplicados entre páginas
- **Clave de deduplicación**: `datos[2]` = ID de campaña (string numérico extraído del URL)

### Filtros de campañas válidas (`extraer_campanias_de_pagina`, líneas 252-281)

Cada `<li>` con `a[href*="/report/campaign/"]` se valida con:
1. `tiene_fecha`: regex `\d{2}/\d{2}/\d{2}` (formato DD/MM/YY)
2. `tiene_numeros_final`: regex `\d+[\s,]*\d*[\s,]*\d*\s*$`
3. `longitud_suficiente`: `len(text.strip()) > 30`
4. `no_es_anidado`: `text.count("\n") <= 3`

### Session retry (`@with_session_retry`, líneas 36-107)

- Decorador con `max_retries=2`
- Si detecta login page o error de sesión: re-autentica + navega a reportes
- Detecta session error por: "session expired", "login", "unauthorized", "timeout", o `is_on_login_page()`
- Espera 2s entre reintentos

### Selectores CSS críticos (a migrar a POM)

| Selector | Uso | Archivo:Línea |
|----------|-----|---------------|
| `a[href*='/reports']` | Navegar a reportes | utils.py:234 |
| `ul li` | Esperar lista | listar_campanias.py:237 |
| `li:has(a[href*="/report/campaign/"])` | Filtrar campañas | listar_campanias.py:245 |
| `div.am-responsive-table-cell` | Celdas de tabla | listar_campanias.py:149,155,165,175 |
| `span.font-color-darkblue-1` | Total elementos | utils.py:267 |
| `select` (con option "15") | Dropdown paginación | utils.py:250 |
