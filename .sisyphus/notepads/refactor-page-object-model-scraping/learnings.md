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

## 2026-04-07 — Arquitectura POM definida

**Decisión:** Se definió el mapa de arquitectura POM en `.sisyphus/notepads/refactor-page-object-model-scraping/pom-architecture.md`.

**Estructura de capas (de fuera a dentro):**
1. `presentation` (CLI/GUI) → importa Flows
2. `infrastructure/scraping/flows/` → importa Pages + DTOs
3. `infrastructure/scraping/pages/` → importa Components
4. `infrastructure/scraping/components/` → importa Browser infra + Selectores
5. `infrastructure/browser/` → BrowserManager, PageWrapper (compartido)

**Reglas clave:**
- `Page` y `Locator` solo viven en `browser/` y `components/`
- `nth()` encapsulado exclusivamente en `CampaignRowComponent`
- DTOs (`core/dto/`) sin dependencias de Playwright/Excel
- Excel como puerto de salida independiente, recibe solo DTOs
- Flows orquestan Pages, nunca tocan selectores ni locators

**Migración fase 1:** 15+ funciones/archivos existentes mapeados a destinos POM específicos. Contrato: preservar comportamiento exacto, no agregar features.

## 2026-04-07 — Shared primitives y foundation DTO/export creados

**Archivos nuevos:**
- `src/core/dto/__init__.py` — Re-exports puros
- `src/core/dto/campaign_summary.py` — `CampaignSummary` dataclass, reemplaza `list[str]`
- `src/core/dto/scraping_result.py` — `ScrapingResult` contenedor con metadata
- `src/infrastructure/scraping/utils/selectors.py` — Agregados `ReportPageSelectors` (verificados) y `SessionSelectors`
- `src/infrastructure/excel/campaign_report_exporter.py` — `CampaignReportExporter` consume DTOs, no Playwright

**Archivos existentes reutilizados:**
- `src/infrastructure/browser/browser_manager.py` — `BrowserManager`, `PageWrapper` (ya existen, listos para usar)
- `src/infrastructure/scraping/base.py` — `BaseScraper` (ya existe, tiene retry + screenshots)
- `src/infrastructure/excel/excel_manager.py` — `ExcelManager` (ya existe, limpio)
- `src/infrastructure/scraping/models/campanias.py` — Modelos Pydantic existentes (para suscriptores, stats, URLs)

**Decisiones:**
- `CampaignSummary` usa `dataclass(frozen=True)` — inmutabilidad, hashable para sets de deduplicación
- `_safe_diff` maneja dots (`5.000` → `5000`) y negativos (fallback "0")
- `CampaignReportExporter` usa `openpyxl` directamente (no `ExcelManager`) para control fino del formato actual
- `ReportPageSelectors` tiene índices numéricos (`cell_date_index: int = 2`) para que `CampaignRowComponent` los use sin hardcodear
- Imports absolutos (`src.core.dto`) en vez de relativos para evitar `ImportError: beyond top-level package` en ejecución directa

**Verificación:**
- `uv run py_compile` pasa en todos los archivos nuevos y existentes
- DTOs no importan `playwright` ni `openpyxl` (verificado con `sys.modules`)
- Exporter produce Excel idéntico al formato actual: 8 columnas, mismo orden, mismo cálculo de `no_abierto`
- `CampaignSummary.to_excel_row()` produce `list[str]` compatible con el output actual

## 2026-04-07 — Auth/Navigation POM components creados

**Componentes creados (infrastructure/scraping/components/):**
- `CookieBannerComponent` — Encapsula detección y aceptación de cookies con 11 estrategias, retry agresivo
- `LoginFormComponent` — Encapsula login form: `click_entrar_link()`, `fill_credentials()`, `submit()`
- `SessionGuardComponent` — Encapsula verificación de sesión: `is_on_login_page()`, `is_authenticated()`, `verify_login()`

**Pages creadas (infrastructure/scraping/pages/):**
- `BasePage` — Wrapper mínimo con `page`, `url`, `navigate()`, `wait_for_load()`
- `LoginPage` — Orquesta `CookieBannerComponent` + `LoginFormComponent` + `SessionGuardComponent`
- `ReportsPage` — Orquesta `SessionGuardComponent` + `ReportPageSelectors`, con `navigate_to()`

**Flows creados (infrastructure/scraping/flows/):**
- `AuthFlow` — Orquesta login completo: navigate → cookies → credentials → verify → save session
- `ScrapingSession` — Decorador/context manager para retry con re-auth automática

**Archivo original preservado:** `src/autentificacion.py` NO fue modificado. Los componentes POM son nueva infraestructura que puede usarse en futuro sin romper el código existente.

**Patrón exitoso:** Components contienen selectores, Pages orquestan Components, Flows orquestan Pages. Playwright nunca sale de `infrastructure/`.

## 2026-04-07 — Task 8: Mapeo completo del flujo de subscribers

### Archivos analizados para task 8

| Archivo | Líneas | Rol en subscribers |
|---------|-------|-------------------|
| `src/infrastructure/scraping/endpoints/suscriptores.py` | 368 | `SubscribersScraper` (POM nuevo, usa utils legacy) |
| `src/scrapping/endpoints/subscriber_details.py` | 702 | `SubscriberDetailsService` (legacy activo, usado por HybridDataService) |
| `src/hybrid_service.py` | 618 | `HybridDataService` - orquesta API + scraping |
| `src/demo.py` | 934 | Entry point que usa HybridDataService |
| `src/infrastructure/scraping/models/suscriptores.py` | 232 | Modelos Pydantic (DTOs) |
| `tests/integration/test_scraping_suscriptores.py` | 457 | Tests de integración |

### Cadena de ejecución actual (fuente legacy → hybrid_service.py)

```
demo.py:main()
  └── HybridDataService.get_complete_campaign_data(campaign_id)
        ├── PASO 1: API.get_basic_info() — datos básicos de campaña
        ├── PASO 2: API.get_total_info(), .get_clicks(), .get_openers(), .get_soft_bounces(), .get_lists()
        └── PASO 3: _extract_scraping_data()
              └── SubscriberDetailsService (page)
                    ├── navigate_to_subscriber_details(campaign_id, filter_index=N)
                    │     └── URL: /report/campaign/{id}/subscribers/?filter={filter_index}
                    │           (filter_index: 0=Abiertos, 1=Hard bounces, 5=No abiertos)
                    ├── extract_subscribers_from_table(expected_columns=4)
                    │     ├── Selector: ul.filter(has=li:has-text("Correo electrónico"))
                    │     ├── Filas: tabla_locator.locator('> li')
                    │     └── Extracción: nth(i).locator('> div') → [correo, lista, estado, calidad]
                    ├── obtener_total_paginas(page) — optimiza a max items/página
                    └── navegar_siguiente_pagina(page, pagina_actual)
```

### Flujo de Suscriptores (SubscribersScraper POM nuevo — infraestructura/scraping/endpoints/suscriptores.py)

El nuevo `SubscribersScraper` usa helpers de `legacy_utils` directamente:
- `obtener_total_paginas(page)` — de `shared.utils.legacy_utils`
- `navegar_siguiente_pagina(page, pagina_actual)` — de `shared.utils.legacy_utils`

**Métodos y responsabilidades:**

| Método | Selector/Comportamiento | Archivo:Línea |
|-------|------------------------|---------------|
| `navegar_a_detalle_suscriptores(page, campaign_id)` | Navega a `/report/campaign/{id}/` → clic "Detalles suscriptores" | suscriptores.py:111-134 |
| `seleccionar_filtro(page, label)` | `page.locator("#query-filter").select_option(label=label)` + wait_for_timeout(2000) | suscriptores.py:24-40 |
| `extraer_suscriptores_tabla(page, cantidad_campos=4)` | `ul.filter(has=li:has-text("Correo electrónico")).locator('> li')` → nth(0..3) | suscriptores.py:42-109 |
| `extraer_datos_filtro(page, campania, filter_type)` | Loop: `extraer_suscriptores_tabla` + `navegar_siguiente_pagina` por página | suscriptores.py:136-189 |
| `extraer_hard_bounces(page, campania, campaign_id)` | `navegar_a_detalle` → `seleccionar_filtro("Hard bounces")` → loop paginado | suscriptores.py:191-226 |
| `extraer_no_abiertos(page, campania, campaign_id)` | `seleccionar_filtro("No abiertos")` → loop paginado (asume ya en detalle) | suscriptores.py:228-263 |
| `extraer_suscriptores_optimizado(page, campania, campaign_id)` | Navega una vez, extrae ambos filtros consecutivamente | suscriptores.py:265-311 |
| `extraer_suscriptores_completos(page, campania, campaign_id, config)` | Orchestrator con `ScrapingSession` tracking | suscriptores.py:313-368 |

### Navegación y URL pattern

| Paso | URL | Selector/acción |
|------|-----|-----------------|
| Navegación a detalle | `/report/campaign/{campaign_id}/` → clic "Detalles suscriptores" | `get_by_role("link", name="Detalles suscriptores")` |
| Filtro por URL | `/report/campaign/{campaign_id}/subscribers/?filter={index}` | `page.goto(url)` |
| Selector filtro UI | `select#query-filter` | `select_option(label="Hard bounces"\|"No abiertos")` |

### Paginación (reusada de legacy_utils)

- `obtener_total_paginas(page)` — obtiene total elementos + optimiza items/página (max dropdown)
- `navegar_siguiente_pagina(page, pagina_actual)` — busca `<ul>` con link a página siguiente

### Selectores CSS críticos (suscriptores)

| Selector | Uso | Archivo:Línea |
|----------|-----|---------------|
| `#query-filter` | Dropdown de filtros en página suscriptores | suscriptores.py:30 |
| `ul` filter with `li:has-text("Correo electrónico")` | Tabla principal de suscriptores | suscriptores.py:55, subscriber_details.py:245 |
| `ul > li` | Filas de la tabla (incluye header) | suscriptores.py:58 |
| `> div` (4 campos) | Datos por fila: [correo, lista, estado, calidad] | suscriptores.py:81-88 |
| `a[href*="/report/campaign/"]` | Links de navegación a campaña | subscriber_details.py:123 |

### DTOs existentes (src/infrastructure/scraping/models/suscriptores.py)

| Modelo | Campos | Uso |
|--------|--------|-----|
| `SubscriberScrapingData` | proyecto, lista, correo, fecha_apertura, pais, aperturas, lista2, estado, calidad | Datos extraídos por scraping |
| `SubscriberTableData` | correo, lista, estado, calidad | Datos crudos de tabla |
| `SubscriberFilterResult` | filter_type, subscribers[], total_pages, total_subscribers | Resultado de filtro |
| `CampaignSubscriberReport` | campaign_id, campaign_name, fecha_envio, abiertos[], no_abiertos[], clics[], hard_bounces[], soft_bounces[] | Informe completo |
| `ScrapingSession` | session_id, campaign_ids[], total_subscribers_extracted, errors | Tracking de sesión |
| `SubscriberExtractionConfig` | extract_hard_bounces, extract_no_abiertos, use_optimized_extraction, etc. | Config de extracción |

### Issues detectados para task 8

- **I-015**: `SubscribersScraper` usa `obtener_total_paginas` y `navegar_siguiente_pagina` directamente de `legacy_utils` — debería encapsularse en `PaginationComponent`
- **I-016**: `seleccionar_filtro` usa `wait_for_timeout(2000)` hardcoded — viola rule AGENTS.md
- **I-017**: `SubscribersScraper` y `SubscriberDetailsService` tienen lógica duplicada de extracción de tabla
- **I-018**: `navegar_a_detalle_suscriptores` hace `goto + click` en lugar de navegar directo a `/subscribers/` — podría ser más directo
- **I-019**: `CampaignSubscriberReport` incluye `abiertos`, `clics`, `soft_bounces` que se obtienen por API, no por scraping — confusión de responsabilidades

### Componentes POM sugeridos para task 8

**Pages:**
- `SubscribersPage` — encapsula navegación a `/report/campaign/{id}/subscribers/` con filtros
- `SubscriberDetailPage` — encapsula `/report/campaign/{id}/subscribers/` con selector de filtro

**Components:**
- `FilterSelectorComponent` — `#query-filter` select + wait states
- `SubscriberTableComponent` — extracción de `ul > li > div` (4 columnas)
- `PaginationComponent` — reusa `obtener_total_paginas` + `navegar_siguiente_pagina` (ya existe parcialmente en legacy_utils)

**Actions/Flows:**
- `ExtractHardBouncesFlow` — navigate → filter → paginate → extract
- `ExtractNoOpensFlow` — filter → paginate → extract (asume navegación ya hecha)
- `ExtractSubscribersFlow` — orchestrator que extrae ambos con optimización

### Dependencias con tasks anteriores (5, 6, 7)

- Task 5 (auth/nav): `LoginPage`, `SessionGuardComponent` → reusable para session validation en subscribers
- Task 6 (reports): `ReportsPage`, `CampaignRow` → patrón similar para `SubscribersPage`
- Task 7 (excel): `CampaignReportExporter` → similar patrón para `SubscriberReportExporter`

## 2026-04-07 — Task 8: POM Foundation Analysis (Reuse Patterns for Subscribers)

### Files Analyzed

| Archivo | Líneas | Rol |
|---------|-------|-----|
| `src/infrastructure/scraping/pages/base_page.py` | 24 | `BasePage` — minimal wrapper with `page`, `url`, `navigate()`, `wait_for_load()` |
| `src/infrastructure/scraping/pages/reports_page.py` | 142 | `ReportsPage` — pagination + campaign row orchestration |
| `src/infrastructure/scraping/pages/login_page.py` | 24 | `LoginPage` — orchestrates 3 components |
| `src/infrastructure/scraping/components/campaign_row.py` | 128 | `CampaignRow` — nth()-based extraction for campaigns |
| `src/infrastructure/scraping/components/session_guard.py` | 110 | `SessionGuardComponent` — session verification |
| `src/infrastructure/scraping/components/cookie_banner.py` | 99 | `CookieBannerComponent` — multi-strategy cookie handling |
| `src/infrastructure/scraping/components/login_form.py` | 32 | `LoginFormComponent` — login form interaction |
| `src/infrastructure/scraping/flows/auth_flow.py` | 129 | `AuthFlow` + `ScrapingSession` — auth + session retry |
| `src/infrastructure/scraping/flows/report_listing_flow.py` | 170 | `ReportListingFlow` — paginated campaign extraction |
| `src/infrastructure/scraping/utils/selectors.py` | 202 | `ReportPageSelectors` (verified) + `CampaignSelectors` (placeholder) + `SessionSelectors` |
| `src/infrastructure/scraping/endpoints/suscriptores.py` | 368 | `SubscribersScraper` — subscriber scraping with legacy utils |
| `src/shared/utils/legacy_utils.py` | 265-409 | `obtener_total_paginas`, `navegar_siguiente_pagina` |

### Reusable Pattern Map

#### 1. Pagination Pattern — TWO IMPLEMENTATIONS, ONE SHOULD WIN

**ReportsPage (POM):**
- `ReportsPage.get_total_pages()` — lines 43-74: calculates from `span.font-color-darkblue-1` + `_detect_items_per_page()`
- `ReportsPage.navigate_to_next_page(current_page)` — lines 99-117: clicks link with text `siguiente_pagina`
- `ReportsPage.optimize_items_per_page()` — lines 29-41: selects max option from dropdown

**legacy_utils (Legacy):**
- `obtener_total_paginas(page)` — lines 265-362: 3-step (get total → optimize dropdown → calculate)
- `navegar_siguiente_pagina(page, pagina_actual)` — lines 388-425: finds `ul` with link to next page

**Assessment:** Both implement the SAME 3-step pagination algorithm. `ReportsPage` wraps it in a Page object; `legacy_utils` is stateless functions. **For task 8**, the `SubscribersScraper` directly imports `obtener_total_paginas` and `navegar_siguiente_pagina` from `legacy_utils`. This should be refactored to use a `PaginationComponent` that wraps the legacy logic for backward compatibility while providing a POM interface.

#### 2. Session Recovery Pattern — ALREADY EXISTS, NOT USED BY SUBSCRIBERS

**auth_flow.py `ScrapingSession.run_with_recovery()` — lines 93-129:**
- Implements retry loop with re-auth on session expiration
- Detects login page via `is_on_login_page(page)`
- Re-authenticates and re-navigates to reports
- Used in `ReportListingFlow` implicitly via try/catch in `report_listing_flow.py`

**SubscribersScraper:**
- Does NOT use `ScrapingSession.run_with_recovery()`
- Has no session recovery mechanism
- If session expires mid-extraction, it fails

**Reuse for Task 8:** `SubscribersScraper.extraer_suscriptores_completos()` should wrap its operations in `ScrapingSession.run_with_recovery()` similar to how `ReportListingFlow` does it implicitly.

#### 3. Selector Centralization — `ReportPageSelectors` EXISTS, `SubscriberSelectors` DOES NOT

**selectors.py lines 130-153 `ReportPageSelectors`:**
```python
@dataclass(frozen=True)
class ReportPageSelectors:
    reports_link: str = 'a[href*="/reports"]'
    campaign_list_container: str = "ul li"
    campaign_row_filter: str = 'a[href*="/report/campaign/"]'
    table_cell: str = "div.am-responsive-table-cell"
    total_elements_span: str = "span.font-color-darkblue-1"
    items_per_page_select: str = "select"
    cell_date_index: int = 2       # Used by CampaignRow
    cell_total_sent_index: int = 4
    cell_opened_index: int = 5
```

**`CampaignRow` uses cell indices from `ReportPageSelectors` — lines 72-81:**
```python
fecha_cell = self._element.locator("div.am-responsive-table-cell").nth(2)
emails_cell = self._element.locator("div.am-responsive-table-cell").nth(4)
abiertos_cell = self._element.locator("div.am-responsive-table-cell").nth(5)
```

**For subscribers:** No `SubscriberSelectors` dataclass exists. Selectors are hardcoded in `suscriptores.py`:
```python
# Line 30: select_filtro = page.locator("#query-filter")
# Line 55: tabla_suscriptores = page.locator('ul').filter(has=page.locator("li", has_text="Correo electrónico"))
# Line 58: suscriptores_elementos = tabla_suscriptores.locator('> li')
# Line 81: datos_suscriptor.nth(0) ... nth(1) ... nth(2) ... nth(3)
```

**Reuse for Task 8:** Create `SubscriberSelectors` in `selectors.py` mirroring `ReportPageSelectors`:
- `filter_select: str = "#query-filter"`
- `subscriber_table_ul: str = 'ul'` (with filter text)
- `subscriber_row_li: str = '> li'`
- `subscriber_field_indices: dict` — field positions (correo=0, lista=1, estado=2, calidad=3)

#### 4. Component Boundary Pattern — `CampaignRow` ISOLATES nth() USAGE

**Architecture rule enforced:** `nth()` encapsulated exclusively in `CampaignRow` (campaign_row.py line 5 comment: "唯一允许使用 nth() 的地方").

**`CampaignRow` structure — lines 26-109:**
```python
def __init__(self, element: Locator, page: Page):
    self._element = element  # Locator passed from ReportsPage loop
    self._page = page

def is_valid_row(self) -> bool:  # Validation before extraction
def extract_data(self) -> list[str]:  # Returns list for Excel
```

**`ReportsPage.get_valid_campaign_rows()` — lines 76-97:**
```python
all_items = self._page.locator("li").filter(has=self._page.locator('a[href*="/report/campaign/"]'))
for i in range(count):
    element = all_items.nth(i)  # Only nth() here
    row = CampaignRow(element, self._page)
    if row.is_valid_row():
        valid_rows.append(row)
```

**For subscribers:** The same pattern should apply. `SubscribersScraper.extraer_suscriptores_tabla` uses `suscriptores_elementos.nth(i).locator('> div')` directly without a component. **Create `SubscriberRowComponent`** to wrap the nth() access:
- Constructor takes a `Locator` row element
- `is_valid_row()` — validates email presence
- `extract_data()` — extracts 4 fields via nth(0..3)
- `get_table_data()` — returns `SubscriberTableData`

#### 5. Page/Component Orchestration — LoginPage SHOWS THE PATTERN

**LoginPage (24 lines) orchestrates 3 components:**
```python
class LoginPage(BasePage):
    def __init__(self, page: Page, base_url: str):
        super().__init__(page, base_url)
        self.cookie_banner = CookieBannerComponent(page)
        self.login_form = LoginFormComponent(page)
        self.session_guard = SessionGuardComponent(page)
```

**For subscribers:** `SubscribersPage` should follow this pattern:
```python
class SubscribersPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page, url="")
        self.session_guard = SessionGuardComponent(page)
        self.filter_selector = FilterSelectorComponent(page)
        self.subscriber_table = SubscriberTableComponent(page)
        self.pagination = PaginationComponent(page)
```

#### 6. Flow Orchestration Pattern — `ReportListingFlow` SHOWS BATCH SAVE

**ReportListingFlow — lines 28-74:**
```python
def execute(self) -> list[list[str]]:
    self._reports_page.optimize_items_per_page()
    total_paginas = self._reports_page.get_total_pages()
    for pagina_actual in range(1, total_paginas + 1):
        campanias_nuevas = self._extract_page(pagina_actual, ...)
        todas_campanias.extend(campanias_nuevas)
        if pendientes_guardar >= self._batch_size:
            self._save_progress(todas_campanias)  # Incremental save
    return todas_campanias
```

**Pattern to reuse for Task 8:** The incremental save + deduplication + page loop pattern should be mirrored in a `SubscriberExtractionFlow` for batch processing subscribers.

#### 7. Table Extraction Pattern — CampaignRow vs SubscribersScraper SYMMETRY

**CampaignRow.extract_data() — lines 51-109:**
```python
# Iterate over campaign data extracting specific indexed fields
campaign_link = self._element.locator('a[href*="/report/campaign/"]').first
fecha_cell = self._element.locator("div.am-responsive-table-cell").nth(2)
emails_cell = self._element.locator("div.am-responsive-table-cell").nth(4)
abiertos_cell = self._element.locator("div.am-responsive-table-cell").nth(5)
no_abierto = str(int(total_enviado) - int(abierto))
```

**SubscribersScraper.extraer_suscriptores_tabla() — lines 42-109:**
```python
suscriptores_elementos = tabla_suscriptores.locator('> li')
for i in range(1, cantidad_suscriptores):  # skips header
    datos_suscriptor = suscriptores_elementos.nth(i).locator('> div')
    correo = datos_suscriptor.nth(0).inner_text()
    lista = datos_suscriptor.nth(1).inner_text()
    estado = datos_suscriptor.nth(2).inner_text()
    calidad = datos_suscriptor.nth(3).inner_text()
```

**Key symmetry:** Both use `locator.nth(i).locator('> div')` pattern with field indices. The **difference** is campaign rows are validated by regex criteria before extraction; subscriber rows skip header (i=1) and extract all.

#### 8. DTO Reuse — SubscriberTableData and SubscriberScrapingData ALREADY EXIST

**In `src/infrastructure/scraping/models/suscriptores.py`:**
- `SubscriberTableData` (lines 34-49): `correo`, `lista`, `estado`, `calidad` — matches table columns
- `SubscriberScrapingData` (lines 5-33): Full model with project, lista, correo, fecha_apertura, pais, aperturas, lista2, estado, calidad
- `CampaignSubscriberReport` (lines 75-129): Already has structure for hard_bounces, no_abiertos

**Existing DTOs to reuse in task 8:** No new DTOs needed — `SubscriberTableData` is already the right shape for `SubscriberRowComponent.extract()` return.

### Anti-Patterns Detected (should NOT be reused)

1. **`wait_for_timeout(2000)` hardcoded** — `suscriptores.py:36, 129`, `reports_page.py:27, 38, 112` — violates AGENTS.md. Use config timeouts instead.

2. **`#query-filter` selector hardcoded in method body** — should be in `SubscriberSelectors` dataclass.

3. **`time.sleep(2)` in `ScrapingSession.run_with_recovery()`** — `auth_flow.py:125` — should use `page.wait_for_timeout()` instead.

4. **`SubscribersScraper` directly calls `legacy_utils`** — `suscriptores.py:14` — bypasses POM abstraction layer. Should use `PaginationComponent` instead.

### Recommended New Components for Task 8

**New in `components/`:**
- `SubscriberRowComponent` — wraps nth() table extraction
- `FilterSelectorComponent` — `#query-filter` select_option + wait states
- `PaginationComponent` — wraps `obtener_total_paginas` + `navegar_siguiente_pagina` from legacy_utils

**New in `pages/`:**
- `SubscribersPage` — orchestrates above components

**New in `flows/`:**
- `SubscriberExtractionFlow` — orchestrates pagination loop + batch save + session recovery

**New in `utils/selectors.py`:**
- `SubscriberSelectors` dataclass (frozen) — centralized selectors for subscriber pages

### Minimum Viable Reuse for Task 8 (without creating new shared components)

Since task 8 should minimize NEW shared components unless there are ≥2 consumers, the following ALREADY EXIST and should be reused:
1. `SessionGuardComponent.is_authenticated()` — for session validation before scraping
2. `ScrapingSession` — for wrapping the extraction with retry
3. `SubscriberTableData` — for typed table row data
4. `CampaignSubscriberReport` — for the report structure

The following should be CREATED in task 8 because they have clear 2+ consumers (hard bounces + no abiertos filters):
- `SubscribersPage` — reusable across both filter types
- `FilterSelectorComponent` — reusable across filters
- `SubscriberSelectors` — reusable across all subscriber scraping

## 2026-04-07 — Task 8: Implementación completada

### Archivos creados

| Archivo | Rol |
|---------|-----|
| `infrastructure/scraping/pages/subscribers_page.py` | `SubscribersPage` — navegación a detalle + acceso a filas |
| `infrastructure/scraping/components/filter_selector.py` | `FilterSelectorComponent` — selector #query-filter |
| `infrastructure/scraping/components/subscriber_row.py` | `SubscriberRowComponent` — encapsula nth() para 4 campos |
| `infrastructure/scraping/flows/subscribers_flow.py` | `SubscribersFlow` — orchestrator de extracción paginada |

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `infrastructure/scraping/utils/selectors.py` | + `SubscriberSelectors` (frozen dataclass) |
| `infrastructure/scraping/endpoints/suscriptores.py` | Refactorizado: ahora delega a componentes POM |
| `infrastructure/scraping/components/__init__.py` | + exports para nuevos componentes |
| `infrastructure/scraping/pages/__init__.py` | + exports para SubscribersPage |
| `infrastructure/scraping/flows/__init__.py` | + exports para SubscribersFlow |

### Decisiones de arquitectura

1. **SubscribersPage.delegate a legacy_utils**: `get_total_pages()` y `navigate_to_next_page()` delegan a `obtener_total_paginas` y `navegar_siguiente_pagina` de legacy_utils. NO se creó PaginationComponent porque la lógica es idéntica a campaigns y mantener un solo lugar evita divergencia.

2. **FilterSelectorComponent existe**: Porque hay 2+ consumidores (SubscribersFlow + SubscribersScraper) y centraliza el selector `#query-filter`.

3. **SubscriberRowComponent encapsula nth()**: Siguiendo la regla de CampaignRow, el único lugar donde se permite nth() en la capa suscriptores.

4. **SubscribersScraper mantiene API pública**: Los métodos `extraer_hard_bounces()`, `extraer_no_abiertos()`, `extraer_suscriptores_completos()` mantienen sus firmas originales. La re-autenticación no fue agregada porque la capa deHybridDataService ya la maneja.

### Invariantes preservadas

- Filter indices: `0=Abiertos`, `1=Hard bounces`, `5=No abiertos`
- Table fields: `[correo, lista, estado, calidad]` (índices 0-3)
- Paginación: mismo algoritmo de campaigns (legacy_utils)
- SubscriberTableData y SubscriberScrapingData DTOs sin cambios de schema

## 2026-04-07 — F1: Restaurar compatibilidad de imports rotos

### Problema detectado

Tests unitarios fallaban en colección por imports faltantes:
1. `tests/unit/test_browser_manager.py` importa `BrowserError` de `src.core.errors.exceptions`
2. `tests/unit/test_logging.py` importa `PerformanceLogger` de `src.shared.logging.legacy_logger`

### Solución aplicada (shims mínimos)

**1. BrowserError alias** (`src/core/errors/exceptions.py`):
```python
BrowserError = BrowserAutomationError  # Alias para compatibilidad
```

**2. Export en __init__.py** (`src/core/errors/__init__.py`):
```python
from .exceptions import (
    ...
    BrowserError,  # Alias para compatibilidad
    ...
)
```

**3. legacy_logger.py shim** (`src/shared/logging/legacy_logger.py`):
```python
from .logger import PerformanceLogger

__all__ = ["PerformanceLogger"]
```

### Verificación

```bash
uv run pytest tests/unit/test_browser_manager.py tests/unit/test_logging.py -q --collect-only
# 42 tests colectados sin errores
```

## 2026-04-07 — F2 Anti-patterns corregidos en POM

**Archivos modificados (cambio mínimo):**

| Archivo | Anti-pattern | Fix |
|---------|-------------|-----|
| `login_form.py:21` | `locator('label[for="keepme-logged"]').click()` | `get_by_role("checkbox", name="Mantener sesión iniciada").check()` |
| `auth_flow.py:71` | `wait_for_timeout(2000)` post-login | Eliminado — `wait_for_load_state("networkidle")` ya garantiza estabilidad |
| `auth_flow.py:78` | `wait_for_timeout(2000)` post-verificación | Eliminado — redundante tras `verify_login()` |
| `auth_flow.py:105` | `wait_for_timeout(2000)` en recovery | Eliminado — `wait_for_load_state("networkidle")` suficiente |
| `auth_flow.py:125` | `time.sleep(2)` en recovery | Eliminado — retry loop es suficiente |
| `base_page.py` | Sin anti-patterns | No requiere cambios |

**Principio aplicado:** Playwright auto-waiting elimina la necesidad de waits fijos.
`wait_for_load_state("networkidle")` ya espera a que la red se estabilice.
`.check()` es preferible a `.click()` para checkboxes — auto-waits + accesibilidad.
