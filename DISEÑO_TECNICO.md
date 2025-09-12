# Diseño Técnico - Automatización Acumbamail (v2.2.0)

> **Objetivo:** Documento técnico completo que describe la arquitectura, flujo de datos, módulos y funcionamiento de la aplicación de automatización para Acumbamail que permite extraer reportes de campañas y gestionar listas de suscriptores.

---

## 1. Resumen Ejecutivo

La aplicación es un **bot de automatización web** especializado en Acumbamail que utiliza **Playwright** para automatizar tareas de email marketing. Proporciona interfaces GUI y CLI para:

- **Extracción de reportes de campañas**: Busca campañas específicas y genera informes Excel con métricas
- **Gestión de listas de suscriptores**: Importa masivamente suscriptores desde archivos Excel
- **Listado de campañas**: Obtiene catálogos completos de campañas existentes

La solución prioriza:
- **Observabilidad**: Sistema de logging con monitoreo de rendimiento y tiempos
- **Robustez**: Configuración adaptativa de timeouts según velocidad de internet
- **Usabilidad**: Interfaces GUI intuitivas con threading para no bloquear la experiencia
- **Escalabilidad**: Procesamiento por lotes con selección múltiple de hojas Excel
- **Portabilidad**: Ejecutables standalone y código fuente multiplataforma

---

## 2. Alcance

**En alcance (v2.2.0)**
- Automatización completa del flujo de login en Acumbamail
- Extracción de datos de campañas con paginación automática
- Importación masiva de suscriptores con validación
- Generación de reportes Excel estructurados con nomenclatura mejorada
- Sistema de logging con análisis de rendimiento
- Configuración adaptativa de timeouts desde config.yaml
- Interfaces GUI y CLI
- Compilación a ejecutables standalone
- **NUEVO v2.2.0**: Sistema de nomenclatura de archivos con datos de campaña
- **NUEVO v2.2.0**: Organización en carpeta específica (data/suscriptores/)
- **NUEVO v2.2.0**: Parsing robusto de fechas incluyendo formato DD/MM/YY HH:MM

**Fuera de alcance**
- Bypass de CAPTCHA o sistemas anti-bot
- Modificación de campañas existentes
- Integración con APIs oficiales de Acumbamail
- Análisis estadístico avanzado de datos

---

## 3. Requisitos

### 3.1 Funcionales
- **F1**: Autenticación automática en Acumbamail con persistencia de sesión
- **F2**: Búsqueda de campañas por términos específicos configurables
- **F3**: Extracción de métricas: emails enviados, abiertos, clics, listas objetivo
- **F4**: Importación de suscriptores desde múltiples hojas Excel
- **F5**: Generación de informes Excel con datos estructurados
- **F6**: Listado completo de campañas con metadatos
- **F7**: Interfaz GUI con progreso visual y threading
- **F8**: CLI para automatización e integración

### 3.2 No Funcionales
- **NF1**: **Rendimiento**: Procesamiento adaptativo según velocidad de internet
- **NF2**: **Observabilidad**: Logging detallado con timings y análisis de cuellos de botella
- **NF3**: **Robustez**: Reintentos automáticos y manejo de errores
- **NF4**: **Usabilidad**: GUI responsiva sin bloqueos durante operaciones largas
- **NF5**: **Portabilidad**: Ejecutables para Windows/Mac/Linux
- **NF6**: **Seguridad**: Configuración externa de credenciales, sin hardcoding

### 3.3 Restricciones
- Python 3.8+ requerido
- Playwright para automatización web
- Dependencias específicas: pandas, openpyxl, pyyaml, tkinter

---

## 4. Arquitectura de Alto Nivel

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GUI (tkinter) │────┤  Core Business  │────┤ Browser Engine  │
│   CLI (módulos) │    │    Logic        │    │  (Playwright)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Configuration  │    │   Performance   │    │  Data Storage   │
│  (config.yaml)  │    │    Logging      │    │   (Excel/JSON)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

**Capas principales:**
- **Presentation**: GUI (app.py) y CLI (módulos src/)
- **Business Logic**: Lógica específica de automatización de Acumbamail
- **Browser Automation**: Interacciones web con Playwright
- **Data Layer**: Manejo de archivos Excel, configuración y logs
- **Infrastructure**: Sistema de logging, configuración y utilidades

---

## 5. Flujo de Datos End-to-End

### 5.1 Flujo de Extracción de Reportes

```
[IMAGEN DEL FLUJO: DIAGRAMA DE FLUJO MOSTRANDO CONFIG→LOGIN→BUSQUEDA→EXTRACCION→EXCEL]

1. **Inicialización**:
   - Carga configuración desde config.yaml
   - Carga términos de búsqueda desde data/Busqueda.xlsx
   - Inicializa sistema de logging con performance monitoring

2. **Autenticación**:
   - Verificar sesión persistente (data/datos_sesion.json)
   - Si no existe o expiró: login automático con credenciales
   - Persistir nueva sesión para siguientes ejecuciones

3. **Navegación y Búsqueda**:
   - Navegar a sección de campañas
   - Iterar sobre términos de búsqueda configurados
   - Aplicar filtros y ejecutar búsquedas

4. **Extracción de Datos**:
   - Paginar automáticamente resultados
   - Extraer métricas por campaña: nombre, tipo, fecha, listas, emails, abiertos, clics
   - Validar y estructurar datos

5. **Generación de Informes**:
   - Crear archivo Excel con estructura predefinida
   - Incluir timestamp y metadatos de ejecución
   - Guardar en data/informes_YYYYMMDD_HHMMSS.xlsx
```

### 5.2 Flujo de Importación de Suscriptores

```
[IMAGEN DEL PROCESO: SELECCION HOJA→CONVERSION CSV→UPLOAD→VALIDACION]

1. **Selección de Datos**:
   - GUI: Selección múltiple de hojas con Ctrl/Cmd+clic
   - CLI: Rangos (1-5) o listas (1,3,7) de hojas
   - Validación de estructura: columnas Email, Nombre, Apellido

2. **Procesamiento por Lotes**:
   - Conversión temporal a CSV para cada hoja
   - Upload secuencial con manejo de errores independiente
   - Limpieza automática de archivos temporales

3. **Validación y Feedback**:
   - Verificación de formato de emails
   - Conteo de registros procesados vs. rechazados
   - Notificaciones de éxito/error por lote
```

---

## 6. Estructura de Módulos y Archivos

```
acumba-automation/
├── app.py                          # GUI principal con tkinter
├── config.yaml                     # Configuración de credenciales y timeouts
├── requirements.txt                 # Dependencias Python
├── MANUAL_USUARIO.md               # Manual para usuarios no técnicos
├── DISEÑO_TECNICO.md               # Este documento
├── CLAUDE.md                       # Instrucciones para Claude Code
│
├── src/                            # Módulos core del sistema
│   ├── __init__.py
│   ├── demo.py                     # Extracción de reportes de campañas
│   ├── listar_campanias.py         # Listado completo de campañas
│   ├── crear_lista.py              # Importación de suscriptores
│   ├── autentificacion.py          # Manejo de login y sesiones
│   ├── utils.py                    # Utilidades compartidas y configuración
│   ├── logger.py                   # Sistema de logging y performance
│   └── tipo_campo.py               # Definiciones de tipos de campo
│
├── data/                           # Directorio de datos
│   ├── Busqueda.xlsx              # Términos de búsqueda configurables
│   ├── Lista_envio.xlsx           # Listas de suscriptores para importar
│   ├── datos_sesion.json          # Sesión persistente de Playwright
│   ├── automation_YYYYMMDD.log    # Logs diarios con performance
│   └── informes_*.xlsx            # Reportes generados
│
├── ms-playwright/                  # Binarios de Playwright (auto-generado)
└── dist/                          # Ejecutables compilados (PyInstaller)
```

---

## 7. Modelado de Datos

### 7.1 Estructura de Configuración (config.yaml)

```yaml
# Credenciales y URLs base
url: https://acumbamail.com/app/newsletter/
url_base: https://acumbamail.com
user: usuario@ejemplo.com
password: contraseña_segura
headless: false  # true para ejecución sin interfaz

# Configuración adaptativa de timeouts por velocidad de internet
timeouts:
  navigation: 60        # Navegación entre páginas
  page_load: 30         # Carga completa de páginas  
  element_wait: 15      # Espera de elementos
  elements: 20          # Elementos específicos
  context: 180          # Operaciones largas (login)
  long_operations: 120  # Operaciones muy largas
  file_upload: 120      # Subida de archivos
  tables: 30            # Carga de tablas
  pagination: 45        # Navegación paginación
```

### 7.2 Estructura de Datos de Búsqueda

**Archivo:** `data/Busqueda.xlsx`

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| Buscar | string | Término de búsqueda | "newsletter" |
| Nombre | string | Nombre descriptivo | "Newsletter Enero" |
| Tipo | string | Tipo de campaña | "email" |
| Fecha envío | date | Fecha de envío | "2024-01-15" |
| Listas | string | Listas objetivo | "Lista Premium" |
| Emails | integer | Total emails enviados | 1500 |
| Abiertos | integer | Emails abiertos | 450 |
| Clics | integer | Clics registrados | 89 |

### 7.3 Estructura de Suscriptores

**Archivo:** `data/Lista_envio.xlsx` (Múltiples hojas soportadas)

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| Email | string | Sí | Dirección email válida |
| Nombre | string | Opcional | Nombre del suscriptor |
| Apellido | string | Opcional | Apellido del suscriptor |

### 7.4 Logs de Performance

**Estructura del log diario:** `data/automation_YYYYMMDD.log`

```
2024-01-15 10:30:45,123 - INFO - [RUN_ABC123] ⚙️ CONFIG: Configuración cargada correctamente
2024-01-15 10:30:46,234 - INFO - [RUN_ABC123] 🌐 BROWSER: Navegador iniciado en modo no-headless
2024-01-15 10:30:47,345 - INFO - [RUN_ABC123] 🔐 AUTH: Login exitoso para usuario@ejemplo.com
2024-01-15 10:30:48,456 - INFO - [RUN_ABC123] 📍 CHECKPOINT: Navegación a sección campañas - 1.2s
2024-01-15 10:30:50,567 - INFO - [RUN_ABC123] 🔍 SEARCH: Búsqueda 'newsletter' - 15 resultados - 2.1s
```

---

## 8. Sistema de Logging y Performance

### 8.1 Arquitectura de Logging

```python
class PerformanceLogger:
    """Sistema centralizado de logging con análisis de rendimiento"""
    
    def __init__(self):
        self.timers = {}           # Timers activos para operaciones
        self.operation_times = {}  # Historial de tiempos por operación
        self.heartbeat_active = False
        
    def start_timer(self, operation_name: str, context: str = ""):
        """Inicia timer para una operación específica"""
        
    def end_timer(self, operation_name: str, context: str = ""):
        """Finaliza timer y registra tiempo de operación"""
        
    def log_checkpoint(self, checkpoint_name: str, context: str = ""):
        """Registra punto de control para seguimiento de progreso"""
        
    def print_performance_report(self):
        """Genera reporte de rendimiento con operaciones más lentas/rápidas"""
```

### 8.2 Categorías de Logs

- **⚙️ CONFIG**: Carga y validación de configuración
- **🌐 BROWSER**: Operaciones del navegador (inicio, navegación, cierre)
- **🔐 AUTH**: Procesos de autenticación y gestión de sesiones
- **📍 CHECKPOINT**: Puntos de control para seguimiento de progreso
- **🔍 SEARCH**: Operaciones de búsqueda y filtrado
- **📊 DATA**: Extracción y procesamiento de datos
- **📁 FILE**: Operaciones de archivos (carga, escritura, conversión)
- **⏱️ TIMER**: Mediciones de tiempo de operaciones específicas
- **❌ ERROR**: Errores y excepciones con contexto
- **💓 HEARTBEAT**: Señales de vida durante operaciones largas

### 8.3 Configuración Adaptativa de Timeouts

Basada en tres perfiles de velocidad de internet:

```python
TIMEOUT_CONFIGS = {
    "rapida": {
        "navigation": 30,
        "page_load": 15,
        "element_wait": 8,
        # ...
    },
    "media": {
        "navigation": 60,
        "page_load": 30,  
        "element_wait": 15,
        # ...
    },
    "lenta": {
        "navigation": 120,
        "page_load": 60,
        "element_wait": 30,
        # ...
    }
}
```

---

## 9. Automatización Web con Playwright

### 9.1 Configuración del Navegador

```python
async def configurar_navegador(headless: bool = False, user_agent: str = None):
    """Configura contexto de navegador optimizado para Acumbamail"""
    browser = await playwright.chromium.launch(headless=headless)
    
    context = await browser.new_context(
        user_agent=user_agent or "Mozilla/5.0 ... Acumbamail-Bot/2.1.0",
        viewport={"width": 1920, "height": 1080},
        storage_state=storage_state_path(),  # Persistencia de sesión
        extra_http_headers={
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        }
    )
    return browser, context
```

### 9.2 Patrones de Interacción Web

**Espera Inteligente de Elementos:**
```python
async def wait_for_element_smart(page, selector: str, timeout: int = 30000):
    """Espera elemento con múltiples estrategias de fallback"""
    try:
        # Estrategia 1: Esperar visibilidad
        return await page.wait_for_selector(selector, state="visible", timeout=timeout)
    except:
        # Estrategia 2: Esperar existencia en DOM
        return await page.wait_for_selector(selector, timeout=timeout)
```

**Navegación Robusta:**
```python
async def navigate_with_retry(page, url: str, max_retries: int = 3):
    """Navegación con reintentos y verificación de carga completa"""
    for attempt in range(max_retries):
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_load_state("domcontentloaded")
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(2 ** attempt)  # Backoff exponencial
    return False
```

### 9.3 Selectores y Estrategias de Localización

[IMAGEN DE LA INTERFAZ DE ACUMBAMAIL - MARCAR ELEMENTOS CLAVE CON RECTÁNGULOS DE COLORES]

**Elementos críticos identificados:**
- **Login Form**: `input[name="username"]`, `input[name="password"]`
- **Dashboard Navigation**: `.menu-item[href*="newsletter"]`
- **Campaign Search**: `input[type="search"]`, `.search-button`
- **Results Table**: `.campaign-table tbody tr`
- **Pagination**: `.pagination .page-link`
- **Subscriber Upload**: `input[type="file"]`, `.upload-button`

---

## 10. Interfaces de Usuario

### 10.1 Interfaz Gráfica (GUI)

**Arquitectura de Threading:**
```python
class AutomationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    def run_automation_thread(self, automation_func, *args):
        """Ejecuta automatización en thread separado para no bloquear GUI"""
        future = self.executor.submit(automation_func, *args)
        self.monitor_thread_progress(future)
```

**Componentes GUI principales:**
- **Ventana principal**: Botones para cada función principal
- **Barras de progreso**: Indicadores visuales durante procesamiento
- **Selector de hojas**: Diálogo con scroll y selección múltiple
- **Logs en tiempo real**: Ventana opcional para seguimiento detallado

[IMAGEN DE LA GUI PRINCIPAL - CAPTURA DE PANTALLA CON BOTONES PRINCIPALES MARCADOS]

### 10.2 Interfaz de Línea de Comandos (CLI)

**Módulos ejecutables:**
```bash
# Extracción de reportes
python -m src.demo

# Listado de campañas  
python -m src.listar_campanias

# Importación de suscriptores
python -m src.crear_lista
```

**Selección múltiple en CLI:**
- Rangos: `1-5` (hojas 1 a 5)
- Listas: `1,3,7` (hojas específicas)
- Combinado: `1-3,5,8-10`

---

## 11. Gestión de Datos y Archivos

### 11.1 Procesamiento de Excel

```python
def process_excel_sheets(file_path: str, selected_sheets: List[str]) -> List[Dict]:
    """Procesa múltiples hojas Excel de forma independiente"""
    results = []
    
    for sheet_name in selected_sheets:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            validated_data = validate_subscriber_data(df)
            results.append({
                'sheet': sheet_name,
                'data': validated_data,
                'status': 'success'
            })
        except Exception as e:
            results.append({
                'sheet': sheet_name, 
                'error': str(e),
                'status': 'failed'
            })
    
    return results
```

### 11.2 Generación de Reportes

**Sistema de nomenclatura mejorado (v2.2.0):**

Los archivos de salida siguen el formato: `(nombre_campaña)-(fecha_envío)_(fecha_extracción).xlsx`

```python
def crear_archivo_excel(general, informe_detallado, nombre_campania="", fecha_envio=""):
    """Genera reporte Excel con nomenclatura mejorada"""
    
    # Generar nombre de archivo con información de campaña
    ahora = datetime.now()
    fecha_extraccion = ahora.strftime("%Y%m%d%H%M")
    
    if nombre_campania and fecha_envio:
        # Limpiar nombre de campaña de caracteres problemáticos
        nombre_limpio = re.sub(r'[<>:"/\\|?*]', '_', nombre_campania)
        nombre_archivo = f"{nombre_limpio}-{fecha_envio}_{fecha_extraccion}.xlsx"
        # Guardar en carpeta específica
        nombre_archivo = data_path(f"suscriptores/{nombre_archivo}")
    
    # Estructura del archivo Excel con múltiples hojas:
    hojas_datos = [
        ("General", general),
        ("Abiertos", abiertos), 
        ("No abiertos", no_abiertos),
        ("Clics", clics),
        ("Hard bounces", hard_bounces),
        ("Soft bounces", soft_bounces)
    ]
```

**Parsing de fechas robusto:**

```python
# Formatos soportados (v2.2.0)
date_formats = [
    "%d/%m/%y %H:%M",  # DD/MM/YY HH:MM (nuevo)
    "%d/%m/%Y %H:%M",  # DD/MM/YYYY HH:MM
    "%d-%m-%Y %H:%M",  # DD-MM-YYYY HH:MM
    "%Y-%m-%d %H:%M",  # YYYY-MM-DD HH:MM
    "%d/%m/%Y",        # DD/MM/YYYY
    "%d-%m-%Y",        # DD-MM-YYYY
    "%Y-%m-%d",        # YYYY-MM-DD
    "%d/%m/%y"         # DD/MM/YY (nuevo)
]
```

### 11.3 Persistencia de Sesión

```python
def storage_state_path() -> str:
    """Retorna ruta para persistencia de sesión de Playwright"""
    return os.path.join("data", "datos_sesion.json")

async def save_session_state(context):
    """Guarda estado de sesión para reutilización"""
    storage_state = await context.storage_state()
    with open(storage_state_path(), 'w') as f:
        json.dump(storage_state, f, indent=2)
```

---

## 12. Configuración y Parametrización

### 12.1 Sistema de Configuración Jerárquica

```python
def load_configuration() -> Dict:
    """Carga configuración con precedencia: ENV > config.yaml > defaults"""
    
    # 1. Configuración por defecto
    config = DEFAULT_CONFIG.copy()
    
    # 2. Sobrescribir con config.yaml si existe
    if os.path.exists('config.yaml'):
        with open('config.yaml') as f:
            file_config = yaml.safe_load(f)
            config.update(file_config)
    
    # 3. Sobrescribir con variables de entorno
    env_config = load_env_overrides()
    config.update(env_config)
    
    return validate_configuration(config)
```

### 12.2 Configuración de Performance

**Adaptación automática basada en velocidad de internet:**
```python
def get_timeout_config(internet_speed: str = "media") -> Dict[str, int]:
    """Retorna configuración de timeouts optimizada según velocidad"""
    
    base_config = TIMEOUT_CONFIGS.get(internet_speed, TIMEOUT_CONFIGS["media"])
    
    # Ajustes dinámicos basados en histórico de performance
    if has_performance_history():
        base_config = adjust_timeouts_from_history(base_config)
    
    return base_config
```

---

## 13. Manejo de Errores y Resiliencia

### 13.1 Estrategias de Retry

```python
async def retry_with_backoff(
    operation: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
):
    """Ejecuta operación con reintentos y backoff exponencial"""
    
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"❌ ERROR: Operación falló después de {max_retries} intentos: {e}")
                raise
            
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(f"⚠️ RETRY: Intento {attempt + 1} falló, reintentando en {delay}s: {e}")
            await asyncio.sleep(delay)
```

### 13.2 Manejo de Errores por Categoría

```python
class AutomationError(Exception):
    """Base para errores de automatización"""
    pass

class AuthenticationError(AutomationError):
    """Error durante proceso de autenticación"""
    pass

class NavigationError(AutomationError):
    """Error durante navegación web"""
    pass

class DataExtractionError(AutomationError):
    """Error durante extracción de datos"""
    pass

class FileProcessingError(AutomationError):
    """Error durante procesamiento de archivos"""
    pass
```

### 13.3 Recuperación Automática

```python
async def robust_automation_wrapper(automation_func, *args, **kwargs):
    """Wrapper que proporciona recuperación automática para operaciones"""
    
    try:
        return await automation_func(*args, **kwargs)
    except AuthenticationError:
        logger.info("🔄 RECOVERY: Reautenticando después de error de sesión")
        await reauthenticate()
        return await automation_func(*args, **kwargs)
    except NavigationError:
        logger.info("🔄 RECOVERY: Reiniciando navegador después de error de navegación")
        await restart_browser()
        return await automation_func(*args, **kwargs)
```

---

## 14. Compilación y Distribución

### 14.1 PyInstaller para Ejecutables Standalone

```python
# build_script.py
import PyInstaller.__main__
import os
import shutil

def build_executable():
    """Compila aplicación a ejecutable standalone"""
    
    PyInstaller.__main__.run([
        '--onefile',
        '--collect-all', 'playwright',
        '--collect-data', 'tkinter', 
        '--add-data', 'config.yaml;.',
        '--add-data', 'data;data',
        '--name', 'acumbamail-automation',
        'app.py'
    ])
    
    # Copiar archivos necesarios
    copy_required_files()
    
def copy_required_files():
    """Copia archivos de configuración y datos necesarios"""
    files_to_copy = [
        'config.yaml',
        'MANUAL_USUARIO.md',
        'requirements.txt'
    ]
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy2(file, 'dist/')
```

### 14.2 Distribución Cross-Platform

**Targets soportados:**
- Windows: `app.exe`
- macOS: `app` (Intel/Apple Silicon)
- Linux: `app` (x64)

**Preparación del paquete de distribución:**
```bash
dist/
├── acumbamail-automation(.exe)  # Ejecutable principal
├── config.yaml.template        # Plantilla de configuración
├── MANUAL_USUARIO.md           # Manual de usuario
├── data/                       # Carpeta de datos vacía
│   ├── Busqueda.xlsx.template
│   └── Lista_envio.xlsx.template
└── README_DISTRIBUCION.md      # Instrucciones de instalación
```

---

## 15. Métricas y Monitoreo

### 15.1 Métricas de Performance Automatizadas

```python
class PerformanceMetrics:
    """Recolector automático de métricas de rendimiento"""
    
    def __init__(self):
        self.metrics = {
            'operation_times': defaultdict(list),
            'success_rates': defaultdict(int),
            'error_counts': defaultdict(int),
            'throughput': defaultdict(list)
        }
    
    def record_operation_time(self, operation: str, time_seconds: float):
        """Registra tiempo de operación para análisis posterior"""
        self.metrics['operation_times'][operation].append(time_seconds)
    
    def generate_performance_report(self) -> Dict:
        """Genera reporte de performance con estadísticas"""
        report = {}
        
        for operation, times in self.metrics['operation_times'].items():
            report[operation] = {
                'count': len(times),
                'avg_time': np.mean(times),
                'min_time': np.min(times),
                'max_time': np.max(times),
                'p95_time': np.percentile(times, 95)
            }
        
        return report
```

### 15.2 Health Checks Automatizados

```python
async def system_health_check() -> Dict[str, bool]:
    """Verifica salud del sistema completo"""
    
    health_status = {}
    
    # Check 1: Configuración válida
    try:
        config = load_configuration()
        health_status['configuration'] = True
    except Exception:
        health_status['configuration'] = False
    
    # Check 2: Archivos de datos accesibles
    health_status['data_files'] = check_data_files_accessible()
    
    # Check 3: Conectividad a Acumbamail
    health_status['acumbamail_connectivity'] = await check_acumbamail_connectivity()
    
    # Check 4: Playwright funcionando
    health_status['playwright'] = await check_playwright_working()
    
    return health_status
```

---

## 16. Seguridad y Cumplimiento

### 16.1 Manejo Seguro de Credenciales

```python
def load_credentials_secure():
    """Carga credenciales con múltiples fuentes seguras"""
    
    # Prioridad 1: Variables de entorno
    user = os.getenv('ACUMBAMAIL_USER')
    password = os.getenv('ACUMBAMAIL_PASSWORD')
    
    if user and password:
        return user, password
    
    # Prioridad 2: Archivo de configuración (advertencia de seguridad)
    config = load_configuration()
    if config.get('user') and config.get('password'):
        logger.warning("⚠️ SECURITY: Credenciales cargadas desde archivo de configuración")
        return config['user'], config['password']
    
    raise ValueError("No se encontraron credenciales válidas")
```

### 16.2 Logs Sin Información Sensible

```python
class SensitiveDataFilter(logging.Filter):
    """Filtro para redactar información sensible de los logs"""
    
    SENSITIVE_PATTERNS = [
        r'password["\s]*[:=]["\s]*([^"\s]+)',
        r'token["\s]*[:=]["\s]*([^"\s]+)',
        r'api[_-]?key["\s]*[:=]["\s]*([^"\s]+)',
    ]
    
    def filter(self, record):
        for pattern in self.SENSITIVE_PATTERNS:
            record.msg = re.sub(pattern, r'\1: **REDACTED**', record.msg)
        return True
```

### 16.3 Cumplimiento y Términos de Servicio

**Consideraciones implementadas:**
- **Rate Limiting**: Delays entre requests para no saturar servidor
- **User-Agent Identification**: Identificación clara como bot automatizado
- **Sesión Persistence**: Minimizar logins repetitivos
- **Error Handling**: Comportamiento respetuoso ante errores del servidor
- **Data Minimization**: Solo extrae datos necesarios para funcionalidad

---

## 17. Testing y Validación

### 17.1 Estrategia de Testing

```python
# tests/test_authentication.py
@pytest.mark.asyncio
async def test_login_successful():
    """Prueba login exitoso con credenciales válidas"""
    auth = AuthenticationManager(test_config)
    result = await auth.login()
    assert result.success == True
    assert result.session_valid == True

# tests/test_data_extraction.py  
def test_campaign_data_parsing():
    """Prueba parsing de datos de campaña desde HTML mock"""
    html_content = load_test_html('campaign_sample.html')
    parser = CampaignDataParser()
    data = parser.extract_campaign_data(html_content)
    
    assert len(data) > 0
    assert 'campaign_name' in data[0]
    assert 'emails_sent' in data[0]

# tests/test_excel_processing.py
def test_multi_sheet_processing():
    """Prueba procesamiento de múltiples hojas Excel"""
    processor = ExcelProcessor()
    results = processor.process_sheets(
        'test_data/sample_list.xlsx', 
        ['Sheet1', 'Sheet2']
    )
    
    assert len(results) == 2
    assert all(r['status'] == 'success' for r in results)
```

### 17.2 Tests de Integración

```python
@pytest.mark.integration
async def test_end_to_end_campaign_extraction():
    """Test completo de extracción de campañas"""
    
    # Setup: Preparar datos de prueba
    setup_test_environment()
    
    # Execute: Ejecutar flujo completo
    extractor = CampaignExtractor(test_config)
    results = await extractor.extract_campaigns(['test_term'])
    
    # Verify: Validar resultados
    assert len(results) > 0
    assert os.path.exists(results.excel_output_path)
    
    # Cleanup
    cleanup_test_environment()
```

---

## 18. Roadmap y Futuras Mejoras

### 18.1 Versión 2.2.0 (Planificada)

**Mejoras de Performance:**
- Cache inteligente de resultados de búsqueda
- Procesamiento paralelo de múltiples campañas
- Compresión de archivos de log con rotación automática

**Nuevas Funcionalidades:**
- API REST opcional para integración externa
- Dashboard web de monitoreo en tiempo real
- Exportación a formatos adicionales (PDF, JSON, Parquet)

**Mejoras de UX:**
- Wizard de configuración inicial
- Validación de credenciales antes de ejecución
- Preview de datos antes de procesamiento

### 18.2 Versión 2.3.0 (Exploratoria)

**Integraciones Avanzadas:**
- Conectores para plataformas de BI (Power BI, Tableau)
- Integración con servicios de almacenamiento cloud
- Webhooks para notificaciones automáticas

**Analytics Avanzados:**
- Análisis de tendencias en métricas de campañas
- Detección de anomalías en performance
- Reportes comparativos automáticos

---

## 19. Troubleshooting y Diagnóstico

### 19.1 Problemas Comunes y Soluciones

| Problema | Síntomas | Causa Probable | Solución |
|----------|----------|----------------|----------|
| **Login falla** | Error de autenticación | Credenciales incorrectas o sesión expirada | Verificar config.yaml, borrar datos_sesion.json |
| **Timeouts frecuentes** | Operaciones se cuelgan | Internet lento o configuración inadecuada | Cambiar velocidad_internet a "lenta" |
| **Elementos no encontrados** | Errores de selector | Cambios en interfaz de Acumbamail | [IMAGEN DE LA INTERFAZ ACTUAL PARA VERIFICAR SELECTORES] |
| **Archivo Excel corrupto** | Error al abrir resultados | Interrupción durante escritura | Verificar logs, reejecutar extracción |
| **Memoria insuficiente** | Aplicación se cierra | Procesamiento de datasets grandes | Procesar en lotes más pequeños |

### 19.2 Herramientas de Diagnóstico

**Scripts de debugging incluidos:**
```bash
# Monitoreo de logs en tiempo real
python monitor_logs.py

# Ejecución con debugging extendido  
python debug_script.py

# Verificación de salud del sistema
python -c "from src.utils import system_health_check; print(system_health_check())"
```

**Logs de diagnóstico:**
- `💓 HEARTBEAT`: Confirma que el proceso está activo
- `📍 CHECKPOINT`: Últimos puntos exitosos antes de fallas
- `⏱️ TIMER`: Ayuda a identificar operaciones lentas
- `❌ ERROR`: Detalles de excepciones con contexto

---

## 20. Glosario Técnico

- **Playwright**: Framework de automatización web para múltiples navegadores
- **Storage State**: Persistencia de sesión de navegador (cookies, localStorage, etc.)
- **Headless**: Modo de navegador sin interfaz gráfica para mejor rendimiento
- **Threading**: Ejecución asíncrona para mantener GUI responsiva
- **Backoff Exponencial**: Estrategia de retry con delays crecientes
- **Performance Logger**: Sistema de monitoreo de tiempos de operación
- **Run ID**: Identificador único por ejecución para correlación de logs
- **Timeout Adaptativo**: Configuración de timeouts basada en velocidad de internet
- **DOM Selector**: Expresión CSS/XPath para localizar elementos web
- **Checkpoint**: Punto de control registrado para seguimiento de progreso

---

## 21. Anexos

### 21.1 Configuración de Desarrollo

```bash
# Setup del entorno de desarrollo
git clone https://github.com/AndresGaibor/ia-automatizacion-py.git
cd ia-automatizacion-py

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
playwright install

# Ejecutar tests
python -m pytest tests/ -v

# Linting y formateo
ruff check .
ruff format .
```

### 21.2 Variables de Entorno Soportadas

```bash
# Credenciales (recomendado para producción)
export ACUMBAMAIL_USER="usuario@ejemplo.com"
export ACUMBAMAIL_PASSWORD="contraseña_segura"

# Configuración de logging
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
export LOG_TO_FILE="true"

# Configuración de performance  
export INTERNET_SPEED="media"  # rapida, media, lenta
export MAX_RETRIES="3"
export HEADLESS_MODE="false"
```

### 21.3 Estructura de Directorios Post-Instalación

```
directorio_usuario/
├── acumbamail-automation(.exe)    # Ejecutable principal
├── config.yaml                   # Configuración personalizada
├── data/                         # Datos de trabajo
│   ├── Busqueda.xlsx            # Términos de búsqueda
│   ├── Lista_envio.xlsx         # Suscriptores para importar
│   ├── datos_sesion.json        # Sesión persistente
│   ├── automation_20240115.log  # Logs diarios
│   └── informes_20240115_143022.xlsx  # Reportes generados
├── ms-playwright/                # Navegadores (auto-descarga)
└── logs/                        # Logs históricos (opcional)
```

---

**Fin del documento técnico v2.1.0**

> Este documento proporciona la base técnica completa para comprender, mantener y extender la aplicación de automatización de Acumbamail. Para preguntas específicas de implementación, consultar el código fuente documentado en cada módulo.

---

## Preguntas para el Desarrollador

Antes de finalizar este diseño técnico, tengo algunas preguntas para asegurar completitud:

1. **¿Existen selectores específicos de elementos críticos** en la interfaz de Acumbamail que debería documentar más detalladamente?

2. **¿Hay configuraciones adicionales de timeouts o performance** que se ajusten automáticamente según el rendimiento histórico?

3. **¿Necesitas que documente algún flujo específico** como el manejo de CAPTCHAs o situaciones de error particulares?

4. **¿Quieres que agregue diagramas de secuencia** para operaciones específicas como la extracción de campañas paso a paso?

5. **¿Hay consideraciones específicas de deployment** para diferentes sistemas operativos que debería incluir?

## Recomendaciones Adicionales

Basándome en la estructura actual, sugiero:

1. **Documentar casos de prueba específicos** para validar que los selectores siguen funcionando después de cambios en Acumbamail

2. **Implementar un sistema de versionado de configuración** que permita migrar configuraciones cuando cambien formatos

3. **Considerar un modo "dry-run"** que simule operaciones sin ejecutarlas realmente, útil para testing

4. **Agregar métricas de success rate** por tipo de operación para monitorear degradación de performance

¿Te gustaría que expanda alguna de estas secciones o agregue información adicional sobre algún aspecto específico?