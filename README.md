# Acumba Automation

Automatización para obtener reportes de campañas de email marketing en Acumbamail.

## Requisitos previos

- Python 3.11+ (máximo 3.13)
- uv (gestor de paquetes de Python)

## Instalación

```bash
# Clonar e instalar dependencias
uv sync

# Instalar navegadores de Playwright (obligatorio)
uv run playwright install
```

## Configuración

Editar `config.yaml` en la raíz del proyecto:

```yaml
url: https://acumbamail.com/app/newsletter/
url_base: https://acumbamail.com
user: tu-usuario@email.com
password: tu-contraseña
headless: false

timeouts:
  default: 30000      # ms
  element: 15000
  navigation: 60000
  upload: 120000

api:
  api_key: tu-api-key

lista:
  sender_email: email@empresa.com
  company: Empresa
  address: Dirección
  city: Ciudad
  country: País
  phone: +34 XXX XXX XXX
```

**Timeouts:** Los valores van en milisegundos (30000 = 30s). Aumentar si la conexión es lenta.

## Uso

### GUI (recomendado)

```bash
uv run python app.py
```

### CLI - Módulos (ejecutar como módulos, NO como scripts)

```bash
uv run python -m src.demo              # Extracción de suscriptores
uv run python -m src.listar_campanias  # Listar campañas
uv run python -m src.obtener_listas    # Obtener listas
uv run python -m src.descargar_suscriptores  # Descargar suscriptores
```

**Error común:** NO ejecutar `python src/demo.py` — usar siempre `-m src.demo`.

### Archivos de datos

- `data/Busqueda.xlsx` — Columna "Buscar" con 'x' para marcar campañas a procesar
- `data/Lista_envio.xlsx` — Emails para upload
- `data/suscriptores/` — Output de extracción: `(campaña)-(envío)_(extracción).xlsx`

## Estructura del proyecto

```
src/
├── app.py                    # GUI principal (tkinter)
├── demo.py                   # Extracción CLI de suscriptores
├── autentificacion.py        # Login (legacy)
├── config_validator.py       # Validador de config
├── config_window.py          # Ventana de configuración GUI
├── crear_lista_scraping.py   # Creación de listas (scraping)
├── descargar_listas.py       # Descargar listas
├── descargar_suscriptores.py # Descargar suscriptores
├── excel_helper.py           # Helpers de Excel
├── field_scraper.py          # Scraper de campos
├── hybrid_service.py         # Servicio híbrido API+scraping
├── listar_campanias.py       # Listar campañas
├── logger.py                 # Sistema de logging legacy
├── mapeo_segmentos/         # Mapeo de segmentos
├── obtener_listas.py         # Obtener listas
├── structured_logger.py      # Logging estructurado
├── tipo_campo.py             # Definiciones de tipos de campo
├── utils.py                  # Utilidades compartidas (legacy)
│
├── core/                     # Lógica central (POM refactorizado)
│   ├── authentication/       # Autenticación
│   ├── config/               # Configuración
│   ├── dto/                  # Data Transfer Objects
│   ├── errors/               # Manejo de errores
│   └── services/            # Servicios de negocio
│
├── infrastructure/           # Integración externa
│   ├── api/                  # Cliente API Acumbamail
│   ├── browser/              # Playwright y sesión
│   ├── excel/                # Lectura/escritura Excel
│   └── scraping/             # Scraping con POM
│       ├── base.py            # BaseScraper
│       ├── components/        # Componentes reutilizables
│       ├── endpoints/         # Endpoints de páginas
│       ├── flows/             # Flujos de navegación
│       ├── models/            # Modelos de datos
│       ├── pages/             # Page Objects (por página)
│       ├── selectors/         # Selectores centralizados
│       └── utils/             # Utilidades de scraping
│
├── presentation/             # Capa de presentación (GUI)
│   ├── gui/                  # Componentes GUI
│   ├── progress_window.py    # Ventana de progreso
│   └── work_runner.py         # Ejecutor de trabajo
│
├── shared/                   # Utilidades compartidas
│   ├── logging/              # Logging centralizado
│   └── utils/                # Utilidades (legacy)
│
└── scrapping_deprecated/     # Scraper antiguo (no usar)
```

## Testing

```bash
# Tests seguros (sin data destructiva)
uv run pytest -m 'integration and not destructive'

# Por tipo
uv run pytest -m api        # Solo API
uv run pytest -m scraping   # Solo scraping

# Todos (incluye tests destructivos con auto-cleanup)
uv run pytest tests/integration/

# Unit tests
uv run pytest tests/unit/
```

Los tests usan prefijos únicos `TEST_YYYYMMDD_HHMMSS_` y hacen auto-cleanup.

## Build (crear ejecutable)

```bash
uv run pyinstaller app.spec
```

**Nota:** `app.spec` incluye Playwright, Pydantic y Pandas. Primero instalar navegadores si no están:
```bash
uv run playwright install
```

## Legacy y migración

**Archivos en migración:**
- `src/utils.py` → `src/shared/utils/legacy_utils.py`
- `src/logger.py` → `src/shared/logging/` (POM)
- `src/autentificacion.py` → `src/core/authentication/` (en progreso)

**Scraper antiguo:** `src/scrapping_deprecated/` — no usar, referencía para migración.

**Selección moderna (POM):**
- Selectores en `src/infrastructure/scraping/selectors/`
- Pages en `src/infrastructure/scraping/pages/`
- Components en `src/infrastructure/scraping/components/`

**Prioridad de selectores:**
1. `page.get_by_role("button", name="Texto")` — Rol (primero)
2. `page.get_by_text("Texto")` — Texto
3. `page.get_by_label("Label")` — Label
4. `page.locator("css")` — CSS (último recurso)

## Solución de problemas

1. Verificar conexión a internet
2. Confirmar credenciales en `config.yaml`
3. Si hay timeouts: aumentar valores en `timeouts` de `config.yaml`
4. Si aparece captcha: resolver manualmente y presionar Enter

## Referencias

- Playwright: `DOCS/playwright-python-best-practices.md`
- Testing: `tests/README.md`
- API: `DOCS/acumbamail-api-docs.md`
- Guía general: `CLAUDE.md`