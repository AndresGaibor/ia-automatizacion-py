# Refactor Page Object Model Scraping Foundation

## TL;DR
> **Summary**: Refactorizar la automatización Playwright actual hacia una base Page Object Model completa para scraping, usando naming técnico en inglés y conservando el comportamiento actual de `listar_campanias.py` como flujo fuente. La migración debe separar pages, components, actions/flows, DTOs y exportación Excel sin expandir funcionalidad.
> **Deliverables**:
> - Base POM reusable para login, navegación compartida, reports y subscribers
> - `listar_campanias` migrado a orquestación limpia sobre services/actions
> - DTOs y boundary de Excel separados de Playwright
> - Smoke/integration tests post-refactor para los flujos migrados
> **Effort**: XL
> **Parallel**: YES - 3 waves
> **Critical Path**: Characterization + boundaries → POM base/auth/nav → reports migration → subscribers migration → verification

## Context
### Original Request
El usuario pidió un plan para refactorizar la automatización a **Page Object Model**, indicando que `listar_campanias` debería convertirse en una página de reports/informes y que quiere una estructura más ordenada para pages, actions y todo lo asociado a POM.

### Interview Summary
- Naming decidido: **inglés técnico** para POM (`ReportsPage`, `LoginPage`, `CampaignRow`, etc.).
- Scope decidido: **base completa de scraping**; incluye login, navegación compartida, reports, subscribers, componentes reutilizables y cimientos para futuros scrapers.
- Test strategy decidida: **tests-after**.

### Metis Review (gaps addressed)
- No expandir funcionalidad durante el refactor.
- Migrar un flujo a la vez, manteniendo `listar_campanias.py` como workflow fuente inicial.
- Evitar perfeccionismo de framework: sin jerarquías genéricas o factories si no se justifican.
- Definir criterios de done por flujo y por capa.

## Work Objectives
### Core Objective
Transformar la automatización Playwright actual en una arquitectura POM reutilizable y mantenible, donde Playwright quede encapsulado en infraestructura y los scripts/servicios consuman DTOs y actions de alto nivel.

### Deliverables
- Estructura POM para Acumbamail bajo `src/infrastructure/scraping/acumbamail/`
- Boundary de exportación Excel separado de Playwright
- `listar_campanias.py` refactorizado a orquestación limpia
- Capa reusable para login, navegación, reports, campaign rows, subscribers, pagination y filters
- Tests smoke/integration post-refactor para los caminos migrados
- Limpieza controlada de código legacy sin borrar más de lo necesario en la primera ola

### Definition of Done (verifiable conditions with commands)
- `uv run python -m py_compile src/listar_campanias.py` y nuevos módulos POM compilan sin errores.
- `uv run pytest -m 'integration and not destructive'` pasa para la parte no destructiva afectada.
- `uv run pytest tests/integration/test_scraping_suscriptores.py` pasa tras adaptar los puntos impactados.
- Existe un flujo smoke de login → reports → extracción de campañas usando la nueva capa POM.
- `listar_campanias.py` no contiene lógica Playwright de detalle de DOM más allá de bootstrap/orquestación.

### Must Have
- Naming de clases POM en inglés técnico.
- Playwright confinado a infraestructura.
- DTOs explícitos entre scraping y exportación.
- Components para piezas compartidas (pagination, filters, rows/nav) donde haya reutilización real.
- Preservar comportamiento actual: columnas Excel, cálculo de `No abierto`, sesión persistente, paginación y deduplicación.

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- NO agregar nuevas features de scraping.
- NO rediseñar GUI, empaquetado PyInstaller, API layer ni flujos no relacionados.
- NO usar `nth()` como primera opción si puede reemplazarse por locators más semánticos; si se mantiene, debe quedar encapsulado y documentado por tests.
- NO dejar `Page`, `Locator` o imports de Playwright saliendo hacia `core` o `presentation`.
- NO mezclar Excel/pandas dentro de pages o actions POM.
- NO hacer un “big bang rewrite”; cada fase debe dejar un estado ejecutable.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: **tests-after** con pytest existente (`tests/pytest.ini:1-46`)
- QA policy: Every task has agent-executed scenarios
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`

## Execution Strategy
### Parallel Execution Waves
> Target: 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks for max parallelism.

Wave 1: characterization + architecture boundaries + POM base + DTO/export foundation  
Wave 2: login/shared nav/reports migration + tests for migrated path  
Wave 3: subscribers migration + legacy cleanup + regression stabilization

### Dependency Matrix (full, all tasks)
- 1 blocks 4,5,6,7,8,9,10
- 2 blocks 5,6,8,9,10
- 3 blocks 4,8,9,10
- 4 blocks 5,6,7,8,9,10
- 5 blocks 6,7,8,9,10
- 6 blocks 8,9,10
- 7 blocks 9,10
- 8 blocks 9,10
- 9 blocks 10

### Agent Dispatch Summary (wave → task count → categories)
- Wave 1 → 4 tasks → deep / quick / writing
- Wave 2 → 3 tasks → deep / unspecified-high / quick
- Wave 3 → 3 tasks → deep / unspecified-high / quick

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Characterize current scraping workflow

  **What to do**: Congelar el comportamiento actual del flujo fuente `listar_campanias.py`: login, navegación a reports, extracción por fila, deduplicación entre páginas, cálculo de `No abierto` y escritura en Excel. Documentar inputs/outputs y registrar decisiones sobre qué se preserva exactamente en phase 1.
  **Must NOT do**: No introducir POM todavía ni reescribir selectores en masa.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: requiere entender un flujo legacy completo sin romperlo.
  - Skills: [`playwright`] - para priorizar locators/web-first y modelar el refactor.
  - Omitted: [`brainstorming`] - ya se completó la fase de diseño.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: [4,5,6,7,8,9,10] | Blocked By: []

  **References**:
  - Pattern: `src/listar_campanias.py:121-206` - extracción actual de campaign row y cálculo de `No abierto`.
  - Pattern: `src/listar_campanias.py:219-312` - filtrado de filas válidas y deduplicación local.
  - Pattern: `src/listar_campanias.py:376-502` - flujo fuente end-to-end actual.
  - Pattern: `src/utils.py:230-391` - navegación a reports y paginación actual.

  **Acceptance Criteria**:
  - [ ] Existe un documento/resumen interno del flujo actual con entradas, salidas y invariantes de compatibilidad.
  - [ ] Queda definido que `listar_campanias.py` es el primer entrypoint migrado y referencia funcional.

  **QA Scenarios**:
  ```
  Scenario: Captura del flujo actual
    Tool: Bash
    Steps: Ejecutar `uv run python -m py_compile src/listar_campanias.py` y registrar referencias del flujo en evidencia.
    Expected: El archivo actual compila y el inventario del flujo fuente queda trazable.
    Evidence: .sisyphus/evidence/task-1-characterize-workflow.md

  Scenario: Invariantes de Excel y métricas preservadas
    Tool: Bash
    Steps: Revisar columnas objetivo y cálculo actual desde referencias del código.
    Expected: Se confirma que phase 1 preserva `Buscar, Nombre, ID Campaña, Fecha, Total enviado, Abierto, No abierto` y el cálculo `sent-opened`.
    Evidence: .sisyphus/evidence/task-1-characterize-workflow-check.md
  ```

  **Commit**: YES | Message: `docs(plan): characterize current scraping workflow` | Files: `.sisyphus/evidence/task-1-characterize-workflow.md`

- [ ] 2. Define target POM architecture boundaries

  **What to do**: Crear la estructura objetivo alineada al repo: `src/infrastructure/scraping/acumbamail/pages/`, `components/`, `flows/` o `actions/`, `src/core/scraping/`, `src/infrastructure/export/`. Fijar qué vive en cada capa y qué está prohibido fuera de ella.
  **Must NOT do**: No crear abstracciones genéricas sin uso real; no mover GUI/API.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: define límites estructurales duraderos.
  - Skills: [`playwright`] - para mantener separación correcta entre pages/components/actions.
  - Omitted: [`feature-arch`] - el foco es automatización Playwright Python, no React.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [5,6,8,9,10] | Blocked By: []

  **References**:
  - Pattern: `src/infrastructure/browser/browser_manager.py:14-174` - infraestructura reusable ya existente.
  - Pattern: `src/infrastructure/scraping/models/campanias.py:138-217` - modelos de scraping existentes que pueden inspirar DTOs.
  - External: `https://playwright.dev/python/docs/pom` - recomendación oficial de POM.

  **Acceptance Criteria**:
  - [ ] Existe un mapa de capas con responsabilidades y prohibiciones explícitas.
  - [ ] Se define qué será page, component, action/flow, DTO y excel writer.

  **QA Scenarios**:
  ```
  Scenario: Validación de límites por capa
    Tool: Bash
    Steps: Revisar la propuesta y comprobar que Playwright no salga de infraestructura y Excel no entre en pages/actions.
    Expected: Cada responsabilidad queda asignada a una sola capa.
    Evidence: .sisyphus/evidence/task-2-pom-boundaries.md

  Scenario: Anti-scope creep
    Tool: Bash
    Steps: Comparar la arquitectura propuesta contra alcance aprobado.
    Expected: No incluye GUI, PyInstaller, API ni features nuevas.
    Evidence: .sisyphus/evidence/task-2-pom-boundaries-scope.md
  ```

  **Commit**: YES | Message: `docs(plan): define pom architecture boundaries` | Files: `.sisyphus/evidence/task-2-pom-boundaries.md`

- [ ] 3. Lock verification matrix for tests-after migration

  **What to do**: Traducir el test strategy a una matriz concreta: unit-like checks para DTO/export, integration para flujos scraping impactados, smoke e2e para login → reports → extracción. Definir comandos exactos y qué evidencia producir.
  **Must NOT do**: No ampliar la suite con cobertura irrelevante ni visual testing.

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: trabajo de especificación verificable sobre suite existente.
  - Skills: [] - no requiere skill adicional.
  - Omitted: [`playwright`] - ya aplicado en decisiones estructurales.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [4,8,9,10] | Blocked By: []

  **References**:
  - Test: `tests/pytest.ini:1-46` - markers y ejecución base.
  - Test: `tests/integration/test_scraping_suscriptores.py:18-215` - patrón real de scraping actual.
  - Test: `tests/integration/test_scraping_campanias.py:20-219` - cobertura actual aún es skeleton/mock-heavy.

  **Acceptance Criteria**:
  - [ ] Cada fase del refactor tiene comandos de verificación asociados.
  - [ ] Se define al menos un smoke test agente-ejecutable para el flujo migrado.

  **QA Scenarios**:
  ```
  Scenario: Matriz de verificación completa
    Tool: Bash
    Steps: Comprobar que la matriz incluye compile, integration y smoke para cada ola.
    Expected: Ninguna ola queda sin validación concreta.
    Evidence: .sisyphus/evidence/task-3-verification-matrix.md

  Scenario: Compatibilidad con pytest markers existentes
    Tool: Bash
    Steps: Verificar que los comandos propuestos usan markers y rutas ya presentes en el repo.
    Expected: La estrategia de pruebas es ejecutable con la configuración actual.
    Evidence: .sisyphus/evidence/task-3-verification-matrix-commands.md
  ```

  **Commit**: YES | Message: `docs(plan): lock verification matrix for pom migration` | Files: `.sisyphus/evidence/task-3-verification-matrix.md`

- [ ] 4. Build shared primitives and DTO/export foundation

  **What to do**: Crear los cimientos reutilizables: `BasePage`, wait/session helpers reutilizables, DTOs para campaign/subscriber/report rows y un `excel_writer` o boundary equivalente que reciba DTOs. Reusar `BrowserManager` donde sea viable en vez de duplicar bootstrap.
  **Must NOT do**: No migrar aún todo el flujo de reports; no duplicar timeouts/config/session state.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: toca contratos base y reusable infra.
  - Skills: [`playwright`] - para diseñar base page/component correctamente.
  - Omitted: [`supabase-postgres-best-practices`] - no aplica.

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: [5,6,7,8,9,10] | Blocked By: [1,3]

  **References**:
  - Pattern: `src/infrastructure/browser/browser_manager.py:42-147` - timeouts, context y session persistence.
  - Pattern: `src/utils.py:142-158` - contexto/browser legacy a absorber o adaptar.
  - Pattern: `src/listar_campanias.py:315-373` - boundary Excel actual a separar.
  - API/Type: `src/infrastructure/scraping/models/campanias.py:138-217` - shape de stats útil como referencia de models/DTOs.

  **Acceptance Criteria**:
  - [ ] Existen clases base y DTOs sin dependencia circular con presentation.
  - [ ] La exportación Excel acepta DTOs y no depende de `Page` ni `Locator`.
  - [ ] No se duplican timeouts/session helpers ya existentes.

  **QA Scenarios**:
  ```
  Scenario: Base POM compila
    Tool: Bash
    Steps: Ejecutar `uv run python -m py_compile` sobre los nuevos módulos base y DTO/export.
    Expected: Todos compilan sin errores.
    Evidence: .sisyphus/evidence/task-4-shared-primitives.txt

  Scenario: Boundary limpio entre scraping y export
    Tool: Bash
    Steps: Revisar imports de los nuevos módulos.
    Expected: No hay imports de Playwright dentro del excel writer ni imports de pandas/openpyxl dentro de pages/components.
    Evidence: .sisyphus/evidence/task-4-shared-primitives-boundary.txt
  ```

  **Commit**: YES | Message: `refactor(scraping): add pom base dto and export boundaries` | Files: `src/infrastructure/scraping/acumbamail/**`, `src/core/scraping/**`, `src/infrastructure/export/**`

- [ ] 5. Migrate authentication and shared navigation to POM

  **What to do**: Extraer `LoginPage` y shared navigation (`ReportsPage`/`NavigationComponent`) desde `autentificacion.py` y `utils.py`. La nueva capa debe manejar login, sesión persistente, cookies y entrada a reports sin que el script orquestador conozca selectores.
  **Must NOT do**: No cambiar reglas de autenticación ni heurísticas de verificación de sesión salvo encapsularlas.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: login y sesión son frágiles y críticos.
  - Skills: [`playwright`] - para selectors/accessibility-first y auto-waiting.
  - Omitted: [`browser-use`] - no es tarea de navegación manual sino implementación local.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [6,7,8,9,10] | Blocked By: [1,2,4]

  **References**:
  - Pattern: `src/autentificacion.py:313-453` - login actual, cookies, verificación y save session.
  - Pattern: `src/utils.py:230-238` - navegación a reports actual.
  - Pattern: `src/infrastructure/browser/browser_manager.py:88-147` - create_context y save_session reutilizables.

  **Acceptance Criteria**:
  - [ ] `LoginPage` y shared navigation encapsulan locators y waits del flujo actual.
  - [ ] La persistencia de sesión (`datos_sesion.json`) sigue funcionando.
  - [ ] El entrypoint ya no interactúa con selectores de login/reports.

  **QA Scenarios**:
  ```
  Scenario: Login exitoso con nueva capa POM
    Tool: Bash
    Steps: Ejecutar el smoke del flujo autenticado usando la nueva capa hasta entrar a reports.
    Expected: La sesión se valida y se puede navegar a reports sin usar selectores legacy desde el entrypoint.
    Evidence: .sisyphus/evidence/task-5-auth-nav-smoke.txt

  Scenario: Recuperación ante sesión existente o expirada
    Tool: Bash
    Steps: Ejecutar el flujo con storage_state presente y verificar comportamiento de reuso/relogin.
    Expected: Se conserva la lógica funcional actual de verificación de sesión.
    Evidence: .sisyphus/evidence/task-5-auth-nav-recovery.txt
  ```

  **Commit**: YES | Message: `refactor(auth): migrate login and shared navigation to pom` | Files: `src/infrastructure/scraping/acumbamail/pages/login_page.py`, `src/infrastructure/scraping/acumbamail/components/**`, `src/core/**`

- [ ] 6. Migrate reports listing flow to ReportsPage plus CampaignRow component

  **What to do**: Mover la lógica de listados de campañas, detección de filas válidas, extracción de métricas, paginación y deduplicación hacia `ReportsPage`, `CampaignRow` y una action/flow específica. `listar_campanias.py` debe quedar como bootstrap + call a service/action + export.
  **Must NOT do**: No alterar columnas de salida, no cambiar el cálculo `No abierto`, no introducir estadística nueva.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: es el corazón del refactor y del workflow fuente.
  - Skills: [`playwright`] - para encapsular locators, strictness y componentes.
  - Omitted: [`react-expert`] - no aplica.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: [8,9,10] | Blocked By: [1,2,4,5]

  **References**:
  - Pattern: `src/listar_campanias.py:121-206` - row extraction actual.
  - Pattern: `src/listar_campanias.py:219-312` - criterio de filas válidas y dedup local.
  - Pattern: `src/listar_campanias.py:376-443` - paginación y dedup global.
  - Pattern: `src/utils.py:240-391` - total pages + next page.

  **Acceptance Criteria**:
  - [ ] `ReportsPage` encapsula paginación y acceso a filas.
  - [ ] `CampaignRow` expone datos de fila sin filtrar `Locator` fuera del componente.
  - [ ] `listar_campanias.py` no contiene lógica DOM de campaign rows.
  - [ ] El output para Excel conserva estructura y valores.

  **QA Scenarios**:
  ```
  Scenario: Extracción completa de campañas con POM
    Tool: Bash
    Steps: Ejecutar el flujo refactorizado de listar campañas hasta producir la colección exportable.
    Expected: Se obtienen campañas sin duplicados, con fecha, total enviado, abierto y no abierto consistentes.
    Evidence: .sisyphus/evidence/task-6-reports-flow.txt

  Scenario: Paginación robusta
    Tool: Bash
    Steps: Ejecutar el flujo sobre una cuenta con múltiples páginas o simular el camino de `obtener_total_paginas` y `navigate_to_page`.
    Expected: La navegación entre páginas no rompe deduplicación ni pierde filas.
    Evidence: .sisyphus/evidence/task-6-reports-pagination.txt
  ```

  **Commit**: YES | Message: `refactor(reports): migrate campaigns listing to pom` | Files: `src/listar_campanias.py`, `src/infrastructure/scraping/acumbamail/pages/reports_page.py`, `src/infrastructure/scraping/acumbamail/components/campaign_row.py`

- [ ] 7. Move Excel output to dedicated writer and simplify entrypoint

  **What to do**: Reemplazar `guardar_datos_en_excel()` como detalle local por un writer dedicado que reciba DTOs o filas serializadas desde core. Dejar `listar_campanias.py` limpio: setup → service/action → writer → notify.
  **Must NOT do**: No cambiar nombre/ubicación del archivo objetivo ni formato final esperado.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: es separación concreta de responsabilidades con alcance bien definido.
  - Skills: [] - suficiente con la arquitectura ya definida.
  - Omitted: [`xlsx`] - el deliverable principal no es un spreadsheet nuevo sino un boundary de código.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: [9,10] | Blocked By: [4,5]

  **References**:
  - Pattern: `src/listar_campanias.py:315-373` - writer legacy actual.
  - Pattern: `src/excel_utils.py` - helpers reutilizables existentes.

  **Acceptance Criteria**:
  - [ ] La escritura Excel sale de `listar_campanias.py`.
  - [ ] El writer usa helpers existentes cuando conviene, sin duplicarlos.
  - [ ] El entrypoint queda reducido a orquestación.

  **QA Scenarios**:
  ```
  Scenario: Writer produce salida compatible
    Tool: Bash
    Steps: Ejecutar el writer con datos de campañas refactorizados.
    Expected: El archivo mantiene encabezados, orden y ancho de columnas equivalente.
    Evidence: .sisyphus/evidence/task-7-excel-writer.txt

  Scenario: Entry point sin lógica de export embebida
    Tool: Bash
    Steps: Revisar `src/listar_campanias.py` y sus imports.
    Expected: El entrypoint delega escritura a un módulo dedicado.
    Evidence: .sisyphus/evidence/task-7-excel-writer-boundary.txt
  ```

  **Commit**: YES | Message: `refactor(export): extract campaigns excel writer` | Files: `src/infrastructure/export/**`, `src/listar_campanias.py`

- [ ] 8. Introduce subscribers POM and reusable filter/pagination components

  **What to do**: Aplicar el mismo patrón a subscribers: `SubscribersPage`, `FiltersComponent`, `PaginationComponent`, actions/flows para extracción de no abiertos/hard bounces y detalle de suscriptores. Reusar componentes comunes si ya existen de verdad.
  **Must NOT do**: No construir una abstracción genérica de tabla si solo tiene un caso; no tocar endpoints API.

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: amplía la base completa de scraping con reuse real.
  - Skills: [`playwright`] - selectors y componentes reutilizables.
  - Omitted: [`web-scraper-assistant`] - ya hay contexto local suficiente; no se está investigando un sitio nuevo.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [9,10] | Blocked By: [2,3,4,6]

  **References**:
  - Test: `tests/integration/test_scraping_suscriptores.py:61-189` - operaciones actuales de filtros, detalle y extracción.
  - Pattern: `src/utils.py:363-391` - navegación reusable hacia páginas siguientes.
  - Pattern: `src/infrastructure/scraping/models/campanias.py:11-95` - modelos existentes para non-openers/hard bounces.

  **Acceptance Criteria**:
  - [ ] Existe `SubscribersPage` con filtros/paginación encapsulados.
  - [ ] Las extracciones de suscriptores usan actions/flows sobre POM, no DOM procedural directo en scripts.
  - [ ] Solo se extraen componentes comunes cuando hay al menos dos consumidores reales.

  **QA Scenarios**:
  ```
  Scenario: Flujo de detalle de suscriptores con POM
    Tool: Bash
    Steps: Ejecutar pruebas de integración impactadas o smoke equivalente para navegar a detalle de suscriptores y aplicar filtro.
    Expected: Se puede entrar al detalle, seleccionar filtro y extraer filas usando la nueva capa.
    Evidence: .sisyphus/evidence/task-8-subscribers-flow.txt

  Scenario: Reutilización real de componentes comunes
    Tool: Bash
    Steps: Revisar imports y usos de pagination/filters components.
    Expected: Los componentes compartidos tienen más de un consumidor o permanecen específicos si no hay reuse real.
    Evidence: .sisyphus/evidence/task-8-subscribers-components.txt
  ```

  **Commit**: YES | Message: `refactor(subscribers): add pom pages and shared components` | Files: `src/infrastructure/scraping/acumbamail/pages/subscribers_page.py`, `src/infrastructure/scraping/acumbamail/components/**`

- [ ] 9. Add tests-after coverage for migrated POM flows

  **What to do**: Actualizar o crear tests smoke/integration para los caminos migrados: login/shared nav, reports listing y subscribers. Cubrir session reuse, empty states y al menos un caso de paginación/filtro. Mantener uso de pytest markers existentes.
  **Must NOT do**: No intentar cobertura total del sistema ni snapshot tests irrelevantes.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: validación integrada de una migración transversal.
  - Skills: [`playwright`] - diseño de smoke/integration útil y robusto.
  - Omitted: [`brainstorming`] - la estrategia ya está decidida.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [10] | Blocked By: [3,5,6,7,8]

  **References**:
  - Test: `tests/pytest.ini:10-43` - markers y timeout.
  - Test: `tests/integration/test_scraping_suscriptores.py:18-215` - estilo y fixtures existentes.
  - Test: `tests/integration/test_scraping_campanias.py:20-219` - hueco actual a fortalecer.

  **Acceptance Criteria**:
  - [ ] Hay cobertura para login/shared nav, reports y subscribers migrados.
  - [ ] Los comandos de verificación definidos en la matriz son ejecutables.
  - [ ] Los tests nuevos/actualizados no dependen de detalles internos del POM.

  **QA Scenarios**:
  ```
  Scenario: Suite de migración pasa
    Tool: Bash
    Steps: Ejecutar `uv run pytest -m 'integration and not destructive'` y los archivos impactados de scraping.
    Expected: La cobertura post-refactor pasa para los flujos migrados.
    Evidence: .sisyphus/evidence/task-9-tests-after.txt

  Scenario: Empty/error states cubiertos
    Tool: Bash
    Steps: Ejecutar tests que validen sesión expirada, filtros sin resultados o páginas vacías.
    Expected: La capa POM falla de forma controlada sin romper orquestación.
    Evidence: .sisyphus/evidence/task-9-tests-after-edge.txt
  ```

  **Commit**: YES | Message: `test(scraping): add post-refactor pom coverage` | Files: `tests/**`

- [ ] 10. Cleanup legacy paths and enforce final boundaries

  **What to do**: Eliminar uso activo del código procedural reemplazado, simplificar imports y dejar comentarios/deuda explícita solo donde sea necesaria. Mantener rollback posible mediante commits atómicos; no borrar más de lo migrado realmente.
  **Must NOT do**: No hacer cleanup global del repo ni mover archivos no relacionados solo por estética.

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: limpieza final con límites claros.
  - Skills: [] - no requiere skill extra.
  - Omitted: [`documentation-engineer`] - solo aplica documentación mínima de uso si surge del refactor.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: [] | Blocked By: [1,2,3,4,5,6,7,8,9]

  **References**:
  - Pattern: `src/listar_campanias.py:446-502` - entrypoint a dejar limpio.
  - Pattern: `src/autentificacion.py:313-453` - source para eliminar consumo directo desde presentation una vez migrado.
  - Pattern: `src/utils.py:230-391` - helpers legacy a reducir o redirigir.

  **Acceptance Criteria**:
  - [ ] No quedan rutas activas del flujo migrado usando DOM procedural legacy desde entrypoints.
  - [ ] Las responsabilidades finales por capa se cumplen en imports y uso real.
  - [ ] La deuda no migrada queda explicitada y delimitada.

  **QA Scenarios**:
  ```
  Scenario: Boundary final del flujo migrado
    Tool: Bash
    Steps: Revisar imports y ejecutar compile del árbol afectado.
    Expected: No hay imports de Playwright fuera de infraestructura para el flujo migrado.
    Evidence: .sisyphus/evidence/task-10-cleanup-boundary.txt

  Scenario: Rollback-friendly cleanup
    Tool: Bash
    Steps: Validar que la limpieza corresponde solo a código reemplazado por el nuevo flujo.
    Expected: No se eliminaron piezas fuera de alcance.
    Evidence: .sisyphus/evidence/task-10-cleanup-scope.txt
  ```

  **Commit**: YES | Message: `chore(scraping): remove obsolete monolithic paths` | Files: `src/listar_campanias.py`, `src/utils.py`, `src/autentificacion.py`, módulos legacy relacionados

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright if UI)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Commit 1: characterize current behavior and architecture boundaries
- Commit 2: add shared POM primitives, DTOs and export boundary
- Commit 3: migrate auth/shared navigation
- Commit 4: migrate reports flow and simplify entrypoint
- Commit 5: migrate subscribers flow
- Commit 6: add tests-after coverage
- Commit 7: cleanup obsolete monolithic paths

## Success Criteria
- `listar_campanias.py` queda reducido a bootstrap/orquestación.
- Login, reports y subscribers usan POM + actions/flows en infraestructura/core.
- Playwright no sale de infraestructura en el flujo migrado.
- Excel/export no toca `Page` ni `Locator`.
- Los smoke/integration tests definidos pasan y cubren los caminos refactorizados.
- El refactor deja una base reusable para futuros scrapers sin expandir funcionalidad actual.
