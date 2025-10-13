# Plan de Corrección: crear_lista_scraping.py

## Resumen Ejecutivo

Este plan detalla la corrección y modernización del módulo `src/crear_lista_scraping.py` siguiendo las mejores prácticas de Playwright 2024-2025, utilizando BrowserMCP para validación del flujo, y resolviendo problemas de imports y arquitectura.

---

## Problemas Identificados

### 1. **Imports Incorrectos** (Líneas 13-18)
```python
# ❌ INCORRECTO - Imports relativos incorrectos
from .utils import load_config, data_path, storage_state_path, notify, configurar_navegador, crear_contexto_navegador
from .autentificacion import login
from .infrastructure.scraping.endpoints.lista_upload import ListUploader
from .infrastructure.scraping.models.listas import ...
from .shared.logging.logger import get_logger
from .excel_helper import ExcelHelper
```

**Problemas:**
- El archivo está en `src/crear_lista_scraping.py` (raíz de src)
- Los imports relativos con `.` no funcionarán correctamente
- Falta el módulo `ExcelHelper` (no existe en el proyecto)
- Mezcla de imports legacy y refactorizados

### 2. **Selectores Legacy en lista_upload.py**
```python
# ❌ Selectores CSS legacy
page.locator('a:has-text("Nueva Lista")').filter(has_text="Nueva Lista").first
page.locator('input#name')
page.locator('a#add-subscribers-link')
page.locator('input#id_csv')

# ❌ Mezcla con selectores modernos
page.get_by_role("button", name="Crear")
page.get_by_label("Archivo CSV/Excel")
```

### 3. **Esperas Manuales y Timeouts**
```python
# ❌ Esperas manuales innecesarias
page.goto(url_base, wait_until="domcontentloaded", timeout=30000)
page.wait_for_load_state("networkidle")
btn_nueva_lista.wait_for(state="visible", timeout=30000)
```

### 4. **Flujo No Validado**
- No hay evidencia de testing con BrowserMCP
- No se ha validado el flujo completo de creación de lista
- Falta validación de elementos en la interfaz web de Acumbamail

---

## Fase 1: Análisis y Mapeo del Flujo con BrowserMCP

### Objetivo
Validar el flujo real de creación de lista en Acumbamail para identificar los selectores correctos y el orden de operaciones.

### Tareas

#### 1.1 Preparación del Entorno
```bash
# Activar entorno virtual (fish shell)
fish -c "source .venv/bin/activate.fish; python --version"

# Verificar instalación de Playwright
fish -c "source .venv/bin/activate.fish; playwright --version"

# Iniciar BrowserMCP
npx @browsermcp/mcp@latest
```

#### 1.2 Navegación y Autenticación
- [ ] Navegar a la URL base de Acumbamail
- [ ] Capturar snapshot de la página de login
- [ ] Identificar elementos de autenticación
- [ ] Realizar login manualmente con BrowserMCP
- [ ] Guardar estado de sesión

#### 1.3 Mapeo del Flujo de Creación de Lista
- [ ] Navegar a sección "Listas"
- [ ] Capturar snapshot y identificar selector para "Listas"
- [ ] Click en "Nueva Lista"
- [ ] Capturar snapshot del formulario de creación
- [ ] Identificar selectores para:
  - Campo "Nombre de lista"
  - Botón "Crear"
- [ ] Crear lista de prueba

#### 1.4 Mapeo del Flujo de Subida de Archivo
- [ ] Click en "Agregar suscriptores"
- [ ] Capturar snapshot de opciones de subida
- [ ] Identificar selectores para:
  - Radio button "Archivo CSV/Excel"
  - Input de archivo
  - Botón "Añadir"
- [ ] Subir archivo CSV de prueba

#### 1.5 Mapeo del Flujo de Mapeo de Columnas
- [ ] Capturar snapshot de la pantalla de mapeo
- [ ] Identificar selectores para:
  - Contenedores de columnas (`div.col`)
  - Selectores de tipo de campo
  - Popups de creación de campos
  - Botones "Añadir" de campos
  - Botón "Siguiente"
- [ ] Realizar mapeo manual de una columna

#### 1.6 Documentación de Selectores
Crear documento con:
- Screenshots de cada pantalla
- Selectores identificados (role-based preferidos)
- Orden de operaciones validado
- Tiempos de espera observados
- Mensajes de error/éxito

### Entregables Fase 1
- ✅ Documento `DOCS/flujo_crear_lista_acumbamail.md` con selectores validados
- ✅ Screenshots en `DOCS/screenshots/crear_lista/`
- ✅ Lista de selectores modernos (role-based) identificados
- ✅ Validación del flujo completo end-to-end

---

## Fase 2: Refactorización de Imports y Dependencias

### Objetivo
Corregir todos los imports y resolver dependencias faltantes siguiendo la arquitectura limpia del proyecto.

### Tareas

#### 2.1 Análisis de Dependencias
```bash
# Buscar dónde están definidas las funciones
grep -r "def load_config" src/
grep -r "def data_path" src/
grep -r "def configurar_navegador" src/
grep -r "def crear_contexto_navegador" src/
grep -r "class ExcelHelper" src/
```

#### 2.2 Corrección de Imports
**Antes:**
```python
from .utils import load_config, data_path, storage_state_path, notify, configurar_navegador, crear_contexto_navegador
from .autentificacion import login
from .infrastructure.scraping.endpoints.lista_upload import ListUploader
from .infrastructure.scraping.models.listas import ...
from .shared.logging.logger import get_logger
from .excel_helper import ExcelHelper
```

**Después (corregido):**
```python
from src.utils import load_config, data_path, storage_state_path, notify, configurar_navegador, crear_contexto_navegador
from src.autentificacion import login
from src.infrastructure.scraping.endpoints.lista_upload import ListUploader
from src.infrastructure.scraping.models.listas import (
    ListUploadConfig,
    ListUploadColumn,
    ListUploadProgress
)
from src.shared.logging.logger import get_logger
```

#### 2.3 Resolver ExcelHelper
**Opción 1: Usar pandas directamente**
```python
# Reemplazar ExcelHelper.obtener_hojas(archivo)
# Por:
import pandas as pd

def listar_hojas(archivo: str) -> list[str]:
    """Devuelve la lista de hojas del archivo Excel"""
    try:
        with pd.ExcelFile(archivo, engine="openpyxl") as xls:
            return xls.sheet_names
    except Exception as e:
        logger.error(f"Error leyendo hojas: {e}")
        return []
```

**Opción 2: Crear ExcelHelper si no existe**
```python
# src/shared/utils/excel_helper.py
import pandas as pd
from typing import List

class ExcelHelper:
    @staticmethod
    def obtener_hojas(archivo: str) -> List[str]:
        """Obtiene la lista de hojas del archivo Excel"""
        try:
            with pd.ExcelFile(archivo, engine="openpyxl") as xls:
                return xls.sheet_names
        except Exception:
            return []
```

### Entregables Fase 2
- ✅ Archivo `src/crear_lista_scraping.py` con imports corregidos
- ✅ Módulo `ExcelHelper` creado/corregido
- ✅ Código ejecutable sin errores de import

---

## Fase 3: Migración a Selectores Modernos Playwright

### Objetivo
Migrar todos los selectores CSS/XPath legacy a selectores modernos role-based siguiendo las mejores prácticas 2024-2025.

### Referencia: Prioridad de Selectores
1. **Role-based locators** (prioridad máxima)
2. **Text-based locators**
3. **Label-based locators**
4. **Test ID locators**
5. **CSS/XPath** (último recurso)

### Tareas

#### 3.1 Migración en lista_upload.py

##### inicializar_navegacion_lista()
**Antes:**
```python
page.get_by_role("link", name="Listas").first.click()
page.wait_for_load_state("domcontentloaded")
```

**Después:**
```python
# ✅ Ya usa role-based, solo mejorar waiting
page.get_by_role("link", name="Listas").first.click()
# Auto-waiting de Playwright - no necesita wait_for_load_state
```

##### crear_lista()
**Antes:**
```python
btn_nueva_lista = page.locator('a:has-text("Nueva Lista")').filter(has_text="Nueva Lista").first
btn_nueva_lista.wait_for(state="visible", timeout=30000)
btn_nueva_lista.click()
page.wait_for_load_state("networkidle")

input_nombre_lista = page.locator('input#name')
input_nombre_lista.fill(nombre_lista)

btn_crear_lista = page.get_by_role("button", name="Crear")
btn_crear_lista.click()
page.wait_for_load_state("networkidle")
```

**Después (según selectores identificados en Fase 1):**
```python
# ✅ Usar role-based para botón Nueva Lista
page.get_by_role("link", name="Nueva Lista").click()

# ✅ Usar label o role para input de nombre
# Opción A: Si tiene label asociado
page.get_by_label("Nombre de la lista").fill(nombre_lista)
# Opción B: Si no tiene label (usar lo identificado en Fase 1)
page.get_by_placeholder("Nombre de la lista").fill(nombre_lista)

# ✅ Ya usa role-based para botón Crear
page.get_by_role("button", name="Crear").click()
# Auto-waiting - no necesita wait_for_load_state
```

##### subir_archivo()
**Antes:**
```python
btn_agregar_suscriptores = page.locator('a#add-subscribers-link')
btn_agregar_suscriptores.click()
page.wait_for_load_state("networkidle")

page.get_by_label("Archivo CSV/Excel").check()

input_archivo = page.locator('input#id_csv')
input_archivo.set_input_files(archivo_csv)

btn_aniadir = page.get_by_role("link", name="Añadir")
btn_aniadir.click()
page.wait_for_load_state("networkidle")
```

**Después:**
```python
# ✅ Migrar a role-based
page.get_by_role("link", name="Agregar suscriptores").click()

# ✅ Ya usa label - correcto
page.get_by_label("Archivo CSV/Excel").check()

# ✅ Usar label o test-id para input de archivo
# El input de archivo generalmente no tiene label visible
# Usar selector directo pero semántico
page.locator('input[type="file"]').set_input_files(archivo_csv)

# ✅ Migrar link a button si es botón
page.get_by_role("button", name="Añadir").click()
# Si es link, mantener:
# page.get_by_role("link", name="Añadir").click()
```

##### mapear_columnas()
**Antes:**
```python
contenedor = page.locator("div.col", has_text=f"Columna {columna.index}")
selector = contenedor.locator("select")
selector.select_option(label="Crear nueva...")

contenedor_popup = page.locator(f"#add-field-popup-{columna.index}")
input_nombre = contenedor_popup.locator(f"#popup-field-name-{columna.index}")
input_nombre.fill(columna.name)

selector_tipo = contenedor_popup.locator("select")
selector_tipo.select_option(label=columna.field_type)

btn_aniadir = contenedor_popup.get_by_role("button", name="Añadir")
btn_aniadir.click()
```

**Después (optimizado):**
```python
# ✅ Mantener locator por contexto, pero simplificar
contenedor = page.locator("div.col").filter(has_text=f"Columna {columna.index}")

# ✅ Usar get_by_role para select si es posible
# Opción A: Si tiene label o aria-label
select_campo = contenedor.get_by_role("combobox", name="Campo")
select_campo.select_option(label="Crear nueva...")

# Opción B: Si no tiene role claro
contenedor.locator("select").select_option(label="Crear nueva...")

# ✅ Popup: usar getByLabel si tiene label
popup = page.locator(f"#add-field-popup-{columna.index}")
popup.get_by_label("Nombre del campo").fill(columna.name)

# ✅ Select de tipo
popup.get_by_label("Tipo de campo").select_option(label=columna.field_type)

# ✅ Ya usa role-based - correcto
popup.get_by_role("button", name="Añadir").click()
```

##### finalizar_subida()
**Antes:**
```python
btn_siguiente = page.get_by_role("link", name="Siguiente")
btn_siguiente.click()

page.get_by_text("Tus suscriptores se han importado con éxito").wait_for(timeout=30000)
```

**Después:**
```python
# ✅ Ya usa role-based
page.get_by_role("link", name="Siguiente").click()

# ✅ Usar expect con auto-retry
from playwright.sync_api import expect
expect(page.get_by_text("Tus suscriptores se han importado con éxito")).to_be_visible()
```

#### 3.2 Migración en crear_lista_scraping.py

##### main()
**Antes:**
```python
page.goto(url_base, wait_until="domcontentloaded", timeout=30000)
page.goto(url, wait_until="domcontentloaded", timeout=60000)
```

**Después:**
```python
# ✅ Usar wait_until más eficiente
page.goto(url_base, wait_until="domcontentloaded")  # Timeout default es suficiente
page.goto(url, wait_until="domcontentloaded")
# O mejor aún, dejar que Playwright maneje el waiting
page.goto(url)
```

### Entregables Fase 3
- ✅ Archivo `src/infrastructure/scraping/endpoints/lista_upload.py` con selectores modernos
- ✅ Archivo `src/crear_lista_scraping.py` actualizado
- ✅ Todos los selectores documentados en `DOCS/selectores_modernos.md`
- ✅ Código siguiendo guía de mejores prácticas de `DOCS/playwright-python-best-practices.md`

---

## Fase 4: Eliminación de Esperas Manuales

### Objetivo
Eliminar esperas manuales innecesarias (`time.sleep`, `wait_for_load_state`) y aprovechar el auto-waiting de Playwright.

### Principios de Auto-waiting
Playwright automáticamente espera a que los elementos estén:
- **Visible** (visible en viewport)
- **Enabled** (no disabled)
- **Stable** (no animando)
- **Receives events** (no cubierto por otro elemento)

### Tareas

#### 4.1 Auditoría de Esperas
```bash
# Buscar todas las esperas manuales
grep -n "wait_for" src/infrastructure/scraping/endpoints/lista_upload.py
grep -n "wait_for" src/crear_lista_scraping.py
```

#### 4.2 Reemplazo de Esperas

**Patrón Legacy:**
```python
# ❌ INCORRECTO
element = page.locator("button")
element.wait_for(state="visible", timeout=30000)
element.click()
page.wait_for_load_state("networkidle")
```

**Patrón Moderno:**
```python
# ✅ CORRECTO - Auto-waiting
page.get_by_role("button", name="Submit").click()
# Playwright automáticamente espera a que esté visible, enabled, stable
```

**Casos especiales donde SÍ se necesita espera:**
```python
# ✅ Esperar a que elemento desaparezca
page.get_by_text("Loading...").wait_for(state="hidden")

# ✅ Esperar respuesta de red
with page.expect_response("**/api/upload") as response_info:
    page.get_by_role("button", name="Upload").click()
response = response_info.value

# ✅ Esperar navegación
with page.expect_navigation():
    page.get_by_role("link", name="Next Page").click()
```

#### 4.3 Implementación de Assertions
```python
from playwright.sync_api import expect

# ✅ Assertions con auto-retry (mejor que wait_for)
expect(page.get_by_text("Success")).to_be_visible()
expect(page.get_by_role("button", name="Submit")).to_be_enabled()
expect(page).to_have_url(re.compile(r".*/dashboard"))
```

### Entregables Fase 4
- ✅ Código sin esperas manuales innecesarias
- ✅ Uso de assertions con `expect()` donde corresponda
- ✅ Documentación de casos especiales que requieren esperas

---

## Fase 5: Manejo de Errores y Robustez

### Objetivo
Implementar manejo robusto de errores siguiendo patrones modernos de Playwright.

### Tareas

#### 5.1 Implementar Try-Catch Específicos
```python
from playwright.sync_api import TimeoutError, Error

def safe_interaction(page, action_description: str, action_callable):
    """Wrapper para interacciones seguras"""
    try:
        return action_callable(), True
    except TimeoutError:
        logger.warning(f"Timeout en: {action_description}")
        return None, False
    except Error as e:
        logger.error(f"Error de Playwright en {action_description}: {e}")
        return None, False
    except Exception as e:
        logger.error(f"Error inesperado en {action_description}: {e}")
        return None, False
```

#### 5.2 Lógica Condicional Robusta
```python
# ✅ Verificar existencia antes de interactuar
if page.get_by_text("Cookie banner").is_visible():
    page.get_by_role("button", name="Accept").click()

# ✅ Múltiples caminos alternativos
try:
    page.get_by_role("button", name="Submit").click(timeout=5000)
except TimeoutError:
    # Camino alternativo
    page.get_by_role("button", name="Enviar").click()
```

#### 5.3 Mejora de Logging
```python
# ✅ Logging estructurado con contexto
logger.info(f"🔄 Iniciando mapeo de columna {idx}/{total}")
logger.debug(f"   📍 Selector: {selector_info}")
logger.success(f"✅ Columna mapeada: {columna.name}")
logger.warning(f"⚠️  Advertencia: {warning_message}")
logger.error(f"❌ Error: {error_message}")
```

### Entregables Fase 5
- ✅ Manejo robusto de errores en todos los métodos
- ✅ Logging mejorado con contexto y estructura
- ✅ Caminos alternativos para casos edge

---

## Fase 6: Testing y Validación

### Objetivo
Validar el flujo completo con datos reales y automatizar pruebas.

### Tareas

#### 6.1 Testing Manual con BrowserMCP
- [ ] Ejecutar flujo completo con archivo Excel de prueba
- [ ] Validar cada etapa:
  - Navegación a Listas
  - Creación de lista
  - Subida de archivo
  - Mapeo de columnas
  - Finalización
- [ ] Capturar screenshots de éxito/error
- [ ] Documentar tiempo total de ejecución

#### 6.2 Testing Automatizado
```python
# tests/integration/test_crear_lista_scraping.py
import pytest
from src.crear_lista_scraping import main
from src.infrastructure.scraping.endpoints.lista_upload import ListUploader

@pytest.mark.integration
@pytest.mark.scraping
def test_crear_lista_flujo_completo():
    """Test del flujo completo de creación de lista"""
    # Setup: crear archivo Excel de prueba
    # Execute: llamar a main()
    # Assert: verificar que se creó la lista
    pass

@pytest.mark.integration
@pytest.mark.scraping
def test_mapeo_columnas():
    """Test del mapeo de columnas"""
    pass
```

#### 6.3 Validación con Pyrefly
```bash
# CRÍTICO: Ejecutar después de cada cambio
fish -c "source .venv/bin/activate.fish; pyrefly check ."
```

#### 6.4 Linting y Formato
```bash
fish -c "source .venv/bin/activate.fish; ruff check src/crear_lista_scraping.py src/infrastructure/scraping/endpoints/lista_upload.py"
fish -c "source .venv/bin/activate.fish; ruff format src/crear_lista_scraping.py src/infrastructure/scraping/endpoints/lista_upload.py"
```

### Entregables Fase 6
- ✅ Flujo validado con BrowserMCP
- ✅ Tests de integración implementados
- ✅ Código validado con Pyrefly sin errores
- ✅ Código formateado con Ruff

---

## Fase 7: Documentación

### Objetivo
Documentar el módulo, flujo y mejoras realizadas.

### Tareas

#### 7.1 Documentación de Código
```python
"""
Módulo para crear listas de suscriptores usando scraping (web automation)

Este módulo implementa el flujo completo de creación de lista en Acumbamail:
1. Navegación a la sección de listas
2. Creación de nueva lista
3. Subida de archivo CSV/Excel
4. Mapeo automático de columnas a campos personalizados
5. Finalización e importación de suscriptores

Uso:
    # Modo interactivo (con diálogo de selección)
    python -m src.crear_lista_scraping

    # Modo automático (primera hoja)
    python -m src.crear_lista_scraping --auto

    # Desde código
    from src.crear_lista_scraping import main
    main(nombre_hoja="Contactos", archivo_excel="data/Listas.xlsx")

Requisitos:
    - Playwright instalado: playwright install
    - Archivo Excel con formato válido en data/Listas.xlsx
    - Sesión autenticada en Acumbamail (se gestiona automáticamente)

Mejores Prácticas:
    - Usa selectores role-based de Playwright (2024-2025)
    - Aprovecha auto-waiting (sin esperas manuales innecesarias)
    - Manejo robusto de errores con logging estructurado
    - Validado con BrowserMCP
"""
```

#### 7.2 Crear Guía de Uso
```markdown
# DOCS/guia_crear_lista_scraping.md

## Guía de Uso: crear_lista_scraping.py

### Descripción
Módulo para crear listas de suscriptores en Acumbamail mediante web scraping.

### Requisitos Previos
1. Playwright instalado: `playwright install`
2. Archivo Excel en `data/Listas.xlsx` con estructura:
   - Primera fila: nombres de columnas
   - Filas siguientes: datos de suscriptores
   - Columnas típicas: Email, Nombre, Apellido, Teléfono, etc.

### Uso
...
```

#### 7.3 Actualizar CLAUDE.md
Agregar sección sobre crear_lista_scraping.py en el archivo principal del proyecto.

### Entregables Fase 7
- ✅ Docstrings completos en todos los módulos
- ✅ Guía de uso en `DOCS/guia_crear_lista_scraping.md`
- ✅ CLAUDE.md actualizado
- ✅ README del proyecto actualizado

---

## Cronograma Estimado

| Fase | Descripción | Tiempo Estimado | Prioridad |
|------|-------------|-----------------|-----------|
| 1 | Análisis con BrowserMCP | 2-3 horas | 🔴 CRÍTICA |
| 2 | Refactorización de imports | 30-45 min | 🔴 CRÍTICA |
| 3 | Migración a selectores modernos | 2-3 horas | 🟡 ALTA |
| 4 | Eliminación de esperas manuales | 1-2 horas | 🟡 ALTA |
| 5 | Manejo de errores | 1-2 horas | 🟢 MEDIA |
| 6 | Testing y validación | 2-3 horas | 🔴 CRÍTICA |
| 7 | Documentación | 1-2 horas | 🟢 MEDIA |
| **TOTAL** | | **10-16 horas** | |

---

## Checklist de Calidad

### Pre-commit
- [ ] Código ejecutable sin errores de import
- [ ] Pyrefly check sin errores: `pyrefly check .`
- [ ] Ruff check sin warnings: `ruff check .`
- [ ] Código formateado: `ruff format .`

### Testing
- [ ] Flujo completo validado con BrowserMCP
- [ ] Tests de integración pasando
- [ ] Test manual exitoso con archivo real
- [ ] Tiempo de ejecución documentado

### Documentación
- [ ] Docstrings completos en todos los métodos
- [ ] Guía de uso creada
- [ ] CLAUDE.md actualizado
- [ ] Selectores documentados en `DOCS/selectores_modernos.md`

### Mejores Prácticas Playwright
- [ ] Selectores role-based donde sea posible
- [ ] Sin esperas manuales innecesarias
- [ ] Uso de `expect()` para assertions
- [ ] Manejo robusto de errores
- [ ] Logging estructurado

---

## Referencias

### Documentación del Proyecto
- `CLAUDE.md` - Instrucciones del proyecto
- `DOCS/playwright-python-best-practices.md` - Guía de mejores prácticas
- `AGENTS.md` - Pautas para agentes de desarrollo

### Documentación Externa (con Context7)
- **IMPORTANTE: Siempre usar Context7 como fuente primaria de documentación**:
  - Antes de buscar documentación externa, usar Context7 para obtener documentación actualizada
  - Proporciona ejemplos de código y mejores prácticas actualizadas
  - Más eficiente y confiable que buscar en la web

  **Ejemplos de uso con Context7:**
  ```python
  # Para obtener documentación de Playwright
  from context7 import resolve_library_id, get_library_docs

  # Resolver ID de biblioteca
  playwright_id = resolve_library_id("playwright")

  # Obtener documentación específica
  docs = get_library_docs(playwright_id, topic="locators", tokens=5000)
  ```

- [Playwright Python Docs](https://playwright.dev/python/)
- [Playwright Best Practices](https://playwright.dev/python/docs/best-practices)
- [Modern Locators Guide](https://playwright.dev/python/docs/locators)


### Archivos Clave del Proyecto
- `src/crear_lista_scraping.py` - Módulo principal
- `src/infrastructure/scraping/endpoints/lista_upload.py` - Lógica de scraping
- `src/infrastructure/scraping/models/listas.py` - Modelos de datos
- `src/utils.py` - Utilidades compartidas
- `src/autentificacion.py` - Autenticación

---

## Notas Finales

### Principios Guía
1. **Validar primero con BrowserMCP** - No asumir, verificar
2. **Selectores modernos (role-based)** - Siguiendo estándares 2024-2025
3. **Auto-waiting de Playwright** - Confiar en el framework
4. **Testing riguroso** - Validar con Pyrefly después de cada cambio
5. **Documentación clara** - Facilitar mantenimiento futuro

### Riesgos y Mitigaciones
- **Riesgo:** Selectores incorrectos → **Mitigación:** Validar con BrowserMCP en Fase 1
- **Riesgo:** Cambios en UI de Acumbamail → **Mitigación:** Documentar selectores, facilitar actualización
- **Riesgo:** Errores de import → **Mitigación:** Fase 2 dedicada a corregir arquitectura
- **Riesgo:** Performance lento → **Mitigación:** Eliminar esperas innecesarias en Fase 4

### Contacto y Soporte
Para dudas o problemas durante la implementación:
- **USAR CONTEXT7 como fuente primaria de documentación**: siempre resolver ID de biblioteca con Context7 antes de buscar documentación externa
- Revisar `CLAUDE.md` para contexto del proyecto
- Consultar `DOCS/playwright-python-best-practices.md` para patrones
- Usar BrowserMCP para debugging de selectores
- Ejecutar `pyrefly check .` antes de commit

**Uso de Context7 durante el desarrollo:**
```python
# Para obtener documentación actualizada durante el desarrollo
from context7 import resolve_library_id, get_library_docs

# Obtener documentación de Playwright para selectores modernos
playwright_id = resolve_library_id("playwright")
locators_docs = get_library_docs(playwright_id, topic="locators")

# Obtener mejores prácticas
best_practices = get_library_docs(playwright_id, topic="best-practices")
```

---

**Última actualización:** 2025-10-12
**Versión del plan:** 1.0
**Estado:** Pendiente de ejecución
