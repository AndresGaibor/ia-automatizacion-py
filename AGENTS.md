# AGENTS.md

Guía para agentes AI trabajando con este repositorio (Python automation tool para Acumbamail).

## Comandos Esenciales

**CRÍTICO:** Este proyecto usa `uv` para gestión de dependencias:
```bash
uv run python app.py
```

### Setup
```bash
# Instalar dependencias y crear venv
uv sync

# Instalar navegadores de Playwright (obligatorio)
uv run playwright install
```

### Ejecutar
```bash
# GUI
uv run python app.py

# CLI - Módulos se ejecutan SOLO como módulos (-m), NO como scripts directos
uv run python -m src.demo              # Extracción suscriptores
uv run python -m src.listar_campanias  # Listar campañas
```

**ERROR COMÚN:** NO ejecutar `python src/demo.py` - usa `python -m src.demo`

### Testing
```bash
# Tests seguros (sin data destructiva)
uv run pytest -m 'integration and not destructive'

# Por tipo
uv run pytest -m api        # Solo API
uv run pytest -m scraping   # Solo scraping

# Todos (incluye tests destructivos - auto-cleanup)
uv run pytest tests/integration/
```

**Test Safety:** Todos usan prefijos únicos `TEST_YYYYMMDD_HHMMSS_`, auto-cleanup, rate limiting.

### Build
```bash
# Usa app.spec (incluye Playwright, Pydantic, Pandas)
uv run pyinstaller app.spec
```

### Agregar Dependencias
```bash
# Dependencia de producción
uv add nombre-paquete

# Dependencia de desarrollo
uv add --dev nombre-paquete

# Actualizar dependencias
uv sync
```

## Arquitectura Modular

**Estructura post-refactor:**
```
src/
├── core/              # Lógica central (auth, config, servicios)
├── shared/            # Utilidades compartidas (logging, utils, retry)
├── infrastructure/    # Integración externa (API, scraping)
├── presentation/      # GUI y CLI
├── legacy/            # Código antiguo en migración
└── [scripts raíz]     # demo.py, listar_campanias.py (transición)
```

**Migración en progreso:** `src/utils.py` → `src/shared/utils/legacy_utils.py`

## Playwright: Selectores Modernos

**PRIORIDAD OBLIGATORIA:**
1. `page.get_by_role("button", name="Texto")` - Rol (PRIMERO)
2. `page.get_by_text("Texto")` - Texto
3. `page.get_by_label("Label")` - Label
4. `page.locator("css")` - CSS (ÚLTIMO RECURSO)

**Auto-waiting:** NO usar `time.sleep()`. Playwright espera automáticamente.

**Configuración:**
- Timeouts: Usa `utils.get_timeouts()` desde `config.yaml`, NO hardcodeados
- Sesión: `storage_state_path()` para persistencia en `data/datos_sesion.json`
- Browsers: `ms-playwright/` directory para builds portables

**Ver:** `DOCS/playwright-python-best-practices.md` para guía completa.

## Logging y Performance

**Sistema automático:** `src/shared/logging/logger.py` (PerformanceLogger)
- Timing automático de operaciones (login, navegación, extracción)
- Logs diarios en `data/automation_YYYYMMDD.log`
- Identificación de bottlenecks
- Emojis para categorización visual

**Debugging hang-ups:** Ver `CLAUDE.md` para herramientas de debug y análisis de logs.

## Configuración

**config.yaml** - Estructura:
```yaml
url: https://acumbamail.com/app/newsletter/
user: email@example.com
password: "contraseña"
headless: false

timeouts:
  navigation: 60000   # ms
  element: 15000
  upload: 120000
  default: 30000

api:
  api_key: "tu-api-key"
  
lista:
  sender_email: email@example.com
  company: "Empresa"
  # ...más campos
```

**Data files:**
- `data/Busqueda.xlsx` - Columna "Buscar" con 'x' para marcar
- `data/Lista_envio.xlsx` - Emails para upload
- `data/suscriptores/` - Output: `(campaña)-(envío)_(extracción).xlsx`

## Gotchas

**Threading:** GUI (main) vs automation (worker). Comunicación solo con `root.after()`

**PyInstaller:** Requiere `collect_all` para Playwright, Pydantic, Pandas (ver `app.spec`)

**Timeouts config:** Valores en MILISEGUNDOS en config.yaml (30000 = 30s), pero algunos helpers esperan segundos - verificar función específica

**Test markers:** Ver `tests/pytest.ini` para markers completos (integration, destructive, slow, api, scraping)

**Module imports:** CLI scripts deben ejecutarse como módulos: `python -m src.demo`, NO `python src/demo.py`

## Referencias

**Documentación completa:** Ver `CLAUDE.md` para workflows detallados y guías extensas
**Playwright:** Ver `DOCS/playwright-python-best-practices.md` para patrones modernos de selectores
**Testing:** Ver `tests/README.md` para guía completa de tests de integración
**API:** Ver `DOCS/acumbamail-api-docs.md` para endpoints y ejemplos