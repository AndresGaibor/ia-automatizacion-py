# Flujo de Creación de Lista en Acumbamail (Validado con BrowserMCP)

## 📋 Resumen Ejecutivo

Este documento detalla el flujo completo de creación de listas de suscriptores en Acumbamail usando web scraping, validado con BrowserMCP y modernizado con selectores Playwright 2024-2025.

## 🔍 Flujo Validado con BrowserMCP

### 1. Navegación a Listas
- **URL**: `https://acumbamail.com/app/lists/`
- **Selector**: `page.get_by_role("link", name="Listas").first.click()`

### 2. Creación de Nueva Lista
- **Botón**: "Nueva Lista" (parte superior derecha)
- **Selector**: `page.get_by_role("link", name="Nueva Lista").click()`
- **Formulario Modal**:
  - Nombre de la lista: `page.get_by_label("Nombre de la lista")`
  - Email remitente: `page.get_by_label("Email remitente por defecto")`
  - Idioma: `page.get_by_label("Idioma de la lista")`
  - Botón Crear: `page.get_by_role("button", name="Crear").click()`

### 3. Mensaje de Éxito
- **Texto**: "¡Lista creada correctamente! Has creado una lista, pero aún no tiene suscriptores."

### 4. Navegación a Subida de Suscriptores
- **Botón**: "Añadir suscriptores"
- **URL**: `https://acumbamail.com/app/list/{id}/import/`
- **Selector**: `page.get_by_role("link", name="Añadir suscriptores").click()`

### 5. Selección de Método de Importación
- **Opción**: "Archivo CSV/Excel"
- **Selector**: `page.get_by_label("Archivo CSV/Excel").check()`

### 6. Subida de Archivo
- **Input de archivo**: `page.set_input_files('input[type="file"]', archivo_csv)`
- **Opciones avanzadas**:
  - Separador CSV: `page.get_by_label("Separador de los campos de tu CSV")`
  - Carácter de agrupación: `page.get_by_label("Carácter de agrupación")`
  - Actualizar suscriptores existentes: `page.get_by_label("Actualizar los datos de los suscriptores existentes")`

### 7. Mapeo de Columnas
- **Contenedores**: `page.locator("div.col").filter(has_text=f"Columna {index}")`
- **Selectores de campo**: `page.locator("select").select_option(label="Crear nueva...")`
- **Popups de creación**: `page.locator(f"#add-field-popup-{index}")`

### 8. Finalización
- **Botón**: "Siguiente"
- **Selector**: `page.get_by_role("link", name="Siguiente").click()`
- **Mensaje de éxito**: `expect(page.get_by_text("Tus suscriptores se han importado con éxito")).to_be_visible()`

## 🚀 Mejoras Implementadas

### Selectores Modernos Playwright
- ✅ **Role-based locators**: `page.get_by_role()`, `page.get_by_label()`
- ✅ **Auto-waiting**: Eliminación de `wait_for_load_state()` manual
- ✅ **Assertions con expect**: `expect(element).to_be_visible()`
- ✅ **Patrones 2024-2025**: Following modern Playwright best practices

### Manejo de Errores Robusto
- ✅ **Wrapper seguro**: `safe_interaction()` con manejo de PWTimeoutError
- ✅ **Logging estructurado**: Con emojis y contexto claro
- ✅ **Caminos alternativos**: Múltiples estrategias para encontrar elementos
- ✅ **Timeouts configurables**: Uso de timeouts por defecto de Playwright

### Importaciones Corregidas
- ✅ **Imports absolutos**: `from src.module import function`
- ✅ **Tipos correctos**: Importación de `expect` desde playwright.sync_api
- ✅ **Dependencias válidas**: ExcelHelper y logging legacy

## 📄 Selectores Validados

### Botones y Links
```python
# Crear lista
page.get_by_role("link", name="Nueva Lista").click()
page.get_by_role("button", name="Crear").click()

# Subida de suscriptores
page.get_by_role("link", name="Añadir suscriptores").click()
page.get_by_label("Archivo CSV/Excel").check()

# Finalización
page.get_by_role("link", name="Siguiente").click()
```

### Campos de Formulario
```python
# Datos de lista
page.get_by_label("Nombre de la lista").fill(nombre_lista)
page.get_by_label("Email remitente por defecto")  # Ya tiene valor
page.get_by_label("Idioma de la lista").select_option("Español")

# Opciones de importación
page.get_by_label("Separador de los campos de tu CSV").fill(";")
page.get_by_label("Actualizar los datos de los suscriptores existentes").check()
```

### Manejo de Archivos
```python
# Subida de archivo
page.set_input_files('input[type="file"]', archivo_csv)
```

### Assertions
```python
# Verificación de éxito
expect(page.get_by_text("¡Lista creada correctamente!")).to_be_visible()
expect(page.get_by_text("Tus suscriptores se han importado con éxito")).to_be_visible()
```

## 🎯 Mejores Prácticas Aplicadas

### 1. Auto-waiting sobre Manual Waiting
```python
# ❌ Legacy
page.wait_for_load_state("networkidle")
btn.wait_for(state="visible", timeout=30000)

# ✅ Moderno
page.get_by_role("button", name="Crear").click()  # Auto-waiting incluido
```

### 2. Role-based sobre CSS Selectors
```python
# ❌ Legacy
page.locator('a:has-text("Nueva Lista")').filter(has_text="Nueva Lista").first

# ✅ Moderno
page.get_by_role("link", name="Nueva Lista")
```

### 3. Expect sobre wait_for
```python
# ❌ Legacy
page.get_by_text("Success").wait_for(timeout=30000)

# ✅ Moderno
expect(page.get_by_text("Success")).to_be_visible()
```

## 🔧 Configuración de Timeout

Playwright maneja timeouts automáticamente:
- **Timeout por defecto**: 30 segundos para la mayoría de operaciones
- **Timeouts específicos**: Solo configurar cuando sea necesario
- **Auto-retry**: `expect()` incluye reintentos automáticos con backoff

## 🐛 Troubleshooting Común

### Elementos no encontrados
1. **Verificar visibilidad**: Usar `is_visible()` antes de interactuar
2. **Múltiples estrategias**: Intentar diferentes selectores (role, text, label)
3. **Esperar dinámica**: Usar `page.wait_for_timeout()` solo cuando sea estrictamente necesario

### Timeouts frecuentes
1. **Reducir timeouts**: Solo usar valores específicos cuando sea necesario
2. **Auto-waiting**: Confiar en el auto-waiting de Playwright
3. **Condiciones de red**: Usar `wait_for_load_state()` solo para cambios de página

### Errores de importación
1. **Imports absolutos**: Usar `from src.module import function`
2. **Verificar existencia**: Confirmar que los módulos existan en la estructura del proyecto
3. **Tipado correcto**: Importar tipos específicos desde `playwright.sync_api`

## 📊 Validación con Context7

Se utilizó Context7 para obtener documentación actualizada de Playwright:
- **Librería**: `/microsoft/playwright-python`
- **Tópicos**: Locators, file upload, auto-waiting, assertions
- **Patrones**: Best practices 2024-2025, modern locator strategies

## 🔄 Flujo Completo (Pseudo-código)

```python
# 1. Navegación
page.get_by_role("link", name="Listas").first.click()

# 2. Crear lista
page.get_by_role("link", name="Nueva Lista").click()
page.get_by_label("Nombre de la lista").fill("Mi Lista")
page.get_by_role("button", name="Crear").click()

# 3. Verificar creación
expect(page.get_by_text("¡Lista creada correctamente!")).to_be_visible()
page.get_by_role("link", name="Añadir suscriptores").click()

# 4. Subir archivo
page.get_by_label("Archivo CSV/Excel").check()
page.set_input_files('input[type="file"]', "archivo.csv")

# 5. Mapear columnas
for columna in columnas:
    contenedor = page.locator("div.col").filter(has_text=f"Columna {columna.index}")
    contenedor.locator("select").select_option(label="Crear nueva...")

    popup = page.locator(f"#add-field-popup-{columna.index}")
    popup.get_by_label("Nombre del campo").fill(columna.name)
    popup.get_by_role("button", name="Añadir").click()

# 6. Finalizar
page.get_by_role("link", name="Siguiente").click()
expect(page.get_by_text("importado con éxito")).to_be_visible()
```

---

**Última actualización**: 2025-10-12
**Versión**: 1.0
**Estado**: Validado y Modernizado ✅