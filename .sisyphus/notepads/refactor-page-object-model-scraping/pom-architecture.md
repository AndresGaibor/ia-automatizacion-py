# POM Architecture Boundaries — Refactor Page Object Model (Scraping)

## Fecha: 2026-04-07

## Objetivo

Definir un mapa concreto de directorios y capacidades para las capas de **Pages**, **Components**, **Actions/Flows**, **DTOs** y **Excel/Export**, garantizando que `Page` y `Locator` nunca se filtren fuera de `infrastructure`.

---

## 1. Principios de Diseño

| Principio | Regla |
|-----------|-------|
| **Locator encapsulation** | Solo los **Components** conocen selectores CSS y `Locator`. Las Pages usan Components. Los Flows usan Pages. |
| **No `Page` fuera de infra** | `playwright.sync_api.Page` y `Locator` solo aparecen en `infrastructure/browser` y `infrastructure/scraping/components`. |
| **DTOs puros** | Los modelos de datos (`dataclass` / Pydantic) no importan nada de Playwright. |
| **Excel separado** | La lógica de Excel nunca vive en Pages ni Components. Es un puerto de salida independiente. |
| **Browser como infra** | `BrowserManager`, `PageWrapper`, session management son infraestructura compartida, NO lógica de página. |
| **Incremental** | Cada Page/Component se migra individualmente. No se crean factories genéricas sin evidencia. |

---

## 2. Mapa de Directorios Objetivo

```
src/
├── core/
│   ├── authentication/           # YA EXISTE
│   │   ├── authentication_service.py
│   │   └── exceptions.py
│   ├── config/                   # YA EXISTE
│   ├── errors/                   # YA EXISTE
│   ├── services/                 # YA EXISTE
│   │   ├── campaign_service.py       # API campaigns
│   │   ├── segment_service.py        # API segments
│   │   └── hybrid_campaigns_service.py
│   └── dto/                        # NUEVO — DTOs puros del scraping
│       ├── campaign_summary.py       # CampaignSummary (fila de reporte)
│       ├── campaign_url.py           # CampaignUrlInfo
│       └── scraping_result.py        # ScrapingResult (contenedor)
│
├── shared/
│   ├── logging/                  # YA EXISTE
│   └── utils/
│       └── legacy_utils.py       # YA EXISTE (data_path, notify, is_on_login_page)
│
├── infrastructure/
│   ├── browser/                  # YA EXISTE — Infraestructura compartida
│   │   ├── browser_manager.py    # BrowserManager, PageWrapper
│   │   └── session_manager.py    # NUEVO — Extraer de autentificacion.py
│   │                             #   - load_session_state()
│   │                             #   - save_session_state()
│   │                             #   - is_session_valid()
│   │
│   ├── scraping/
│   │   ├── base.py               # BaseScraper (retry, screenshots) — YA EXISTE
│   │   │
│   │   ├── components/           # NUEVO — Piezas reutilizables con selectores
│   │   │   ├── login_form.py     # LoginFormComponent
│   │   │   │                     #   - fill_credentials(user, password)
│   │   │   │                     #   - submit()
│   │   │   │                     #   - is_visible() -> bool
│   │   │   │
│   │   │   ├── cookie_banner.py  # CookieBannerComponent
│   │   │   │                     #   - accept() -> bool
│   │   │   │                     #   - is_present() -> bool
│   │   │   │
│   │   │   ├── pagination_bar.py # PaginationBarComponent
│   │   │   │                     #   - get_total_pages() -> int
│   │   │   │                     #   - go_to_next() -> bool
│   │   │   │                     #   - set_items_per_page(count) -> int
│   │   │   │                     #   - current_page() -> int
│   │   │   │
│   │   │   ├── campaign_row.py   # CampaignRowComponent  ← encapsula nth() aquí
│   │   │   │                     #   - get_name() -> str
│   │   │   │                     #   - get_id() -> str
│   │   │   │                     #   - get_date() -> str
│   │   │   │                     #   - get_total_sent() -> int
│   │   │   │                     #   - get_opened() -> int
│   │   │   │                     #   - get_clicks() -> int
│   │   │   │                     #   - is_valid() -> bool   ← heurísticos actuales
│   │   │   │
│   │   │   ├── campaign_list.py  # CampaignListComponent
│   │   │   │                     #   - get_all_rows() -> list[CampaignRowComponent]
│   │   │   │                     #   - wait_for_load()
│   │   │   │
│   │   │   ├── url_tracking_list.py  # UrlTrackingListComponent
│   │   │   │                     #   - get_urls() -> list[CampaignUrlInfo]
│   │   │   │
│   │   │   └── session_guard.py  # SessionGuardComponent
│   │   │                         #   - is_on_login_page() -> bool
│   │   │                         #   - wait_for_authenticated()
│   │   │
│   │   ├── pages/                # NUEVO — Orquestan Components + Flows
│   │   │   ├── base_page.py      # BasePage
│   │   │   │                     #   - page: Page (único punto donde Page vive aquí)
│   │   │   │                     #   - url: str
│   │   │   │                     #   - navigate()
│   │   │   │                     #   - wait_for_load()
│   │   │   │
│   │   │   ├── login_page.py     # LoginPage
│   │   │   │                     #   - Components: LoginFormComponent, CookieBannerComponent
│   │   │   │                     #   - login(user, password) -> bool
│   │   │   │                     #   - is_logged_in() -> bool
│   │   │   │
│   │   │   ├── reports_page.py   # ReportsPage
│   │   │   │                     #   - Components: CampaignListComponent, PaginationBarComponent
│   │   │   │                     #   - navigate_to()
│   │   │   │                     #   - extract_all_campaigns() -> list[CampaignSummary]
│   │   │   │                     #   - extract_campaign_urls(id) -> list[CampaignUrlInfo]
│   │   │   │
│   │   │   └── subscribers_page.py  # SubscribersPage (futuro)
│   │   │                         #   - Components: (por definir)
│   │   │                         #   - get_non_openers(campaign_id) -> list[...]
│   │   │                         #   - get_hard_bounces(campaign_id) -> list[...]
│   │   │
│   │   ├── flows/                # NUEVO — Flows de negocio (orquestan Pages)
│   │   │   ├── auth_flow.py      # AuthFlow
│   │   │   │                     #   - ensure_authenticated(page, config) -> LoginPage
│   │   │   │                     #   - reauthenticate_if_needed(page, config)
│   │   │   │                     #   Encapsula: login + cookie + session verification + save
│   │   │   │
│   │   │   ├── campaign_list_flow.py  # CampaignListFlow
│   │   │   │                     #   - fetch_all_campaigns(reports_page) -> list[CampaignSummary]
│   │   │   │                     #   - enrich_with_urls(reports_page, campaigns) -> list[...]
│   │   │   │                     #   Encapsula: paginación + deduplicación + session retry
│   │   │   │
│   │   │   └── scraping_session.py    # ScrapingSession
│   │   │                         #   - run_with_session_recovery(fn, max_retries=2)
│   │   │                         #   Decorador/context manager para retry automático
│   │   │
│   │   ├── models/               # YA EXISTE (reubicar/refinar)
│   │   │   ├── campanias.py      # ScrapedCampaignData, etc. → mover a core/dto/
│   │   │   ├── listas.py
│   │   │   └── suscriptores.py
│   │   │
│   │   ├── endpoints/            # YA EXISTE (refactorizar post-POM)
│   │   │   ├── campanias.py      # CampaignsScraper → se reescribe sobre Pages
│   │   │   ├── listas.py
│   │   │   ├── suscriptores.py
│   │   │   └── lista_upload.py
│   │   │
│   │   └── utils/
│   │       ├── selectors.py      # NUEVO — Selectores CSS por componente (dataclasses)
│   │       │                     #   Reemplaza los TODO placeholders actuales
│   │       │
│   │       └── navigation.py     # YA EXISTE (refactorizar post-POM)
│   │
│   ├── api/                      # YA EXISTE — API REST de Acumbamail
│   │
│   └── excel/                    # YA EXISTE — Puerto de salida Excel
│       ├── excel_manager.py      # ExcelManager ( YA EXISTE, limpio)
│       ├── excel_utils_legacy.py # Legacy wrappers → eliminar post-migración
│       └── excel_utils_legacy.py # Legacy helpers → eliminar post-migración
│
└── presentation/                 # YA EXISTE — GUI/CLI
    ├── app.py                    # GUI Tkinter
    └── cli/                      # CLI scripts
```

---

## 3. Mapa de Responsabilidades por Capa

### Capa 1: `infrastructure/browser/` — Infraestructura compartida
| Clase | Responsabilidad | NO debe hacer |
|-------|----------------|---------------|
| `BrowserManager` | Lanzar browser, crear contexto, save/restore session | Saber de páginas específicas |
| `PageWrapper` | Wrap de `Page` con error handling + timeouts | Contener selectores de negocio |

### Capa 2: `infrastructure/scraping/components/` — Piezas atómicas
| Componente | Selectores que maneja | Output |
|------------|----------------------|--------|
| `LoginFormComponent` | `get_by_role("textbox", name="Correo electrónico")`, etc. | `bool` |
| `CookieBannerComponent` | Indicadores de popup + botones aceptar | `bool` |
| `PaginationBarComponent` | `span.font-color-darkblue-1`, `select` con options, `ul > li > a` | `int`, `bool` |
| `CampaignRowComponent` | `div.am-responsive-table-cell:nth(N)`, `a[href*="/report/campaign/"]` | `CampaignSummary` |
| `CampaignListComponent` | `li:has(a[href*="/report/campaign/"])` | `list[CampaignRowComponent]` |
| `UrlTrackingListComponent` | `ul li, ol li` con enlaces | `list[CampaignUrlInfo]` |
| `SessionGuardComponent` | URL checks, elementos de login | `bool` |

**Regla crítica:** `CampaignRowComponent` es el **único** lugar donde `nth()` es permitido. Si `nth()` se necesita en otro sitio, se crea un nuevo componente.

### Capa 3: `infrastructure/scraping/pages/` — Orquestación de Components
| Page | Components que usa | Métodos públicos |
|------|-------------------|-----------------|
| `LoginPage` | `LoginFormComponent`, `CookieBannerComponent`, `SessionGuardComponent` | `login()`, `is_logged_in()` |
| `ReportsPage` | `CampaignListComponent`, `PaginationBarComponent`, `SessionGuardComponent` | `navigate_to()`, `extract_all_campaigns()`, `extract_campaign_urls(id)` |
| `SubscribersPage` | *(por definir)* | *(futuro)* |

**Regla crítica:** Las Pages **NO** contienen selectores CSS directamente. Delegan a Components.

### Capa 4: `infrastructure/scraping/flows/` — Flujos de negocio
| Flow | Pages que usa | Responsabilidad |
|------|--------------|-----------------|
| `AuthFlow` | `LoginPage` | Login completo: navigate → cookies → credentials → verify → save session → retry on expire |
| `CampaignListFlow` | `ReportsPage` | Paginación completa + deduplicación global + enrichment de URLs + session recovery |
| `ScrapingSession` | *(cualquier Page)* | Decorador/context manager para `@with_session_retry` genérico |

**Regla crítica:** Los Flows **NO** conocen `Page`, `Locator`, ni selectores. Solo conocen Pages y DTOs.

### Capa 5: `core/dto/` — DTOs puros
| DTO | Campos | Origen |
|-----|--------|--------|
| `CampaignSummary` | `buscar`, `nombre`, `id_campania`, `fecha`, `total_enviado`, `abierto`, `no_abierto`, `url_correo` | Reemplaza `list[str]` actual |
| `CampaignUrlInfo` | `url`, `clicks`, `click_percentage` | Reemplaza `ScrapedCampaignUrl` simplificado |
| `ScrapingResult` | `campaigns: list[CampaignSummary]`, `errors: list[str]`, `scraped_at` | Contenedor de output |

**Regla crítica:** DTOs no importan nada de `playwright`, `openpyxl`, ni `infrastructure`.

### Capa 6: `infrastructure/excel/` — Export (puerto de salida)
| Clase | Responsabilidad |
|-------|----------------|
| `ExcelManager` | Crear workbook, sheets, headers, datos, save — YA EXISTE |
| `CampaignReportExporter` | NUEVO — Traduce `ScrapingResult` → llamadas a `ExcelManager` |

**Regla crítica:** Excel **NO** conoce Pages, Components, ni Playwright. Solo recibe DTOs.

---

## 4. Flujo de Dependencias (unidireccional)

```
presentation (CLI/GUI)
    ↓ importa
infrastructure/scraping/flows/
    ↓ importa
infrastructure/scraping/pages/
    ↓ importa
infrastructure/scraping/components/
    ↓ importa
infrastructure/browser/  +  core/dto/

core/dto/              ← sin dependencias externas
infrastructure/excel/  ← solo importa core/dto
infrastructure/api/    ← independiente
```

**Dirección prohibida:** Ninguna capa superior importa `Page`, `Locator`, o selectores CSS directamente.

---

## 5. Migración de Código Existente

| Código actual | Destino POM | Estado |
|--------------|-------------|--------|
| `autentificacion.py::login()` | `flows/auth_flow.py` + `components/login_form.py` + `components/cookie_banner.py` | Refactor |
| `autentificacion.py::manejar_popup_cookies()` | `components/cookie_banner.py` | Refactor |
| `autentificacion.py::verificar_login_exitoso()` | `components/session_guard.py` | Refactor |
| `utils.py::navegar_a_reportes()` | `pages/reports_page.py::navigate_to()` | Refactor |
| `utils.py::obtener_total_paginas()` | `components/pagination_bar.py::get_total_pages()` | Refactor |
| `utils.py::navegar_siguiente_pagina()` | `components/pagination_bar.py::go_to_next()` | Refactor |
| `listar_campanias.py::extraer_datos_campania_de_listitem()` | `components/campaign_row.py` | Refactor |
| `listar_campanias.py::extraer_campanias_de_pagina()` | `components/campaign_list.py` | Refactor |
| `listar_campanias.py::procesar_todas_las_paginas()` | `flows/campaign_list_flow.py::fetch_all_campaigns()` | Refactor |
| `listar_campanias.py::extraer_urls_de_campanias()` | `flows/campaign_list_flow.py::enrich_with_urls()` | Refactor |
| `listar_campanias.py::with_session_retry` | `flows/scraping_session.py` | Refactor |
| `listar_campanias.py::guardar_datos_en_excel()` | `excel/campaign_report_exporter.py` | Refactor |
| `demo.py::get_campaign_urls_with_fallback()` | `pages/reports_page.py::extract_campaign_urls()` | Refactor |
| `excel_utils.py` | `excel/excel_utils_legacy.py` → migrar a `ExcelManager` | Legacy → nuevo |

---

## 6. Contrato de la Fase 1

- **Preservar comportamiento exacto:** mismos inputs, mismos outputs Excel.
- **No agregar features:** solo reorganizar código existente en la arquitectura POM.
- **Selectores CSS:** migrar de CSS strings a Components con selectores centralizados.
- **`nth()`**: encapsular exclusivamente en `CampaignRowComponent`.
- **Deduplicación:** preservar lógica de `ids_vistos` (por página) + `ids_globales` (entre páginas).
- **Session retry:** preservar `max_retries=2` con re-auth + navigate-to-reports.

---

## 7. Gotchas y Decisiones

### G-001: `list[str]` → DTO tipado
El output actual es `list[list[str]]`. La migración lo reemplaza por `list[CampaignSummary]` con campos tipados. El exporter de Excel traduce DTO → filas.

### G-002: `Busqueda.xlsx` es input Y output (BUG I-010)
La función `guardar_datos_en_excel` sobrescribe el archivo de búsqueda. En la nueva arquitectura, `CampaignReportExporter` recibe un `output_path` explícito, separado del input.

### G-003: `get_campaign_urls_with_fallback` en `demo.py`
Acoplamiento cruzado. Se mueve a `ReportsPage.extract_campaign_urls()` o `UrlTrackingListComponent`.

### G-004: `time.sleep` / `wait_for_timeout` (BUG I-002)
Los Components usan auto-waiting de Playwright. Los Flows coordinan delays solo cuando son estrictamente necesarios (entre campañas para rate limiting).

### G-005: Selectores `div.am-responsive-table-cell` con `nth()`
Riesgo I-001. Se encapsulan en `CampaignRowComponent` donde el `nth()` es explícito y documentado. Si Acumbamail cambia el orden, solo se modifica este componente.
