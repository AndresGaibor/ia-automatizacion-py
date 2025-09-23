## Compilación (Crear Ejecutable)

### Método Recomendado (Nuevo)
Usar el script de compilación automático que incluye todas las dependencias:

**Linux/macOS:**
```bash
./build.sh
```

**Windows:**
```batch
build.bat
```

### Método Manual (Avanzado)
Si necesitas compilación personalizada:

```bash
# Usando el archivo .spec mejorado
pyinstaller app.spec

# O comando directo (menos confiable)
pyinstaller --onefile --collect-all playwright --collect-all pydantic app.py
```

### Verificación Pre-Compilación
Antes de compilar, asegúrate de que todas las dependencias estén instaladas:

```bash
pip install -r requirements.txt
```

**Nota:** El archivo `app.spec` incluye configuraciones optimizadas para evitar errores como "No module named 'pydantic'" y otros problemas de dependencias.

# Automation

Automatización para obtener reportes de campañas de email marketing.

## Requisitos previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clonar el repositorio:
```bash
git clone <url-repositorio>
cd automation
```

2. Crear un entorno virtual:
```bash
python -m venv .venv
```

3. Activar el entorno virtual:
```bash
# En macOS/Linux:
source .venv/bin/activate

# En Windows:
.venv\Scripts\activate
```

4. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Configuración

1. El archivo `config.yaml` ya está configurado en la raíz del proyecto:
```yaml
url: https://acumbamail.com/app/newsletter/
url_base: https://acumbamail.com
user: tu-usuario@email.com
password: tu-contraseña
headless: false

# Configuración de timeouts específicos (en segundos)
timeouts:
  navigation: 60        # Navegación entre páginas
  page_load: 30         # Carga completa de páginas
  element_wait: 15      # Espera de elementos en la página
  elements: 20          # Espera de elementos específicos
  context: 180          # Operaciones largas como login
  long_operations: 120  # Operaciones muy largas como importación
  file_upload: 120      # Subida de archivos
  tables: 30            # Carga de tablas de datos
  pagination: 45        # Navegación entre páginas de resultados
```

### Configuración de Timeouts

Los timeouts están optimizados para balance entre velocidad y estabilidad:

- **`navigation`**: Tiempo máximo para navegar entre páginas
- **`page_load`**: Tiempo de espera para carga completa de páginas
- **`elements`**: Tiempo de espera para localizar elementos específicos
- **`long_operations`**: Tiempo para operaciones largas como login o importación
- **`tables`**: Tiempo específico para carga de tablas de datos con muchos registros

**Ajuste según tu conexión:**
- **Internet rápido**: Mantener valores por defecto
- **Internet lento**: Aumentar valores en 50-100%
- **Internet muy lento**: Duplicar valores

2. Preparar archivo Excel de búsqueda:
- Crear archivo Excel con una columna llamada "Informes"
- Agregar los nombres de los informes a buscar

## Uso

1. Activar el entorno virtual (si no está activado):
```bash
source .venv/bin/activate  # macOS/Linux
```

2. Ejecutar el script:
```bash
python src/demo.py
```

3. Si aparece un captcha:
   - Resolverlo manualmente en la ventana del navegador
   - Presionar Enter en la terminal para continuar

## Resultados

### Archivos Generados

Los informes se guardan en la carpeta `data/suscriptores/` con el siguiente formato de nombre:

**Formato**: `(nombre campaña)-(fecha envío YYYYMMDDHHMM)_(fecha extracción YYYYMMDDHHMM).xlsx`

**Ejemplo**: `Newsletter Marketing-202509120140_202512091530.xlsx`

### Estructura del Archivo Excel

Cada archivo contiene múltiples hojas con información detallada:

- **General**: Resumen general de las campañas procesadas
- **Abiertos**: Detalle de suscriptores que abrieron el email
- **No abiertos**: Detalle de suscriptores que NO abrieron el email  
- **Clics**: Detalle de suscriptores que hicieron clic
- **Hard bounces**: Emails que rebotaron permanentemente
- **Soft bounces**: Emails que rebotaron temporalmente

## Estructura del proyecto

```
acumba-automation/
├── src/
│   ├── demo.py              # Script principal de extracción
│   ├── autentificacion.py   # Manejo de login
│   ├── crear_lista.py       # Creación de listas de suscriptores
│   ├── listar_campanias.py  # Listado de campañas
│   ├── utils.py             # Utilidades compartidas
│   ├── logger.py            # Sistema de logging
│   └── tipo_campo.py        # Definiciones de tipos de campo
├── data/
│   ├── suscriptores/        # Carpeta donde se guardan los informes
│   ├── Busqueda.xlsx        # Archivo con términos de búsqueda
│   ├── Lista_envio.xlsx     # Listas de emails para upload
│   ├── datos_sesion.json    # Sesión persistente del navegador
│   └── automation_YYYYMMDD.log  # Logs diarios del proceso
├── config.yaml             # Configuración principal
├── requirements.txt         # Dependencias de Python
├── app.py                  # Interfaz gráfica (GUI)
├── CLAUDE.md               # Instrucciones para Claude Code
├── MANUAL_USUARIO.md       # Manual detallado para usuarios
└── README.md               # Este archivo
```

## Solución de problemas

Si encuentras errores:
1. Verifica la conexión a internet
2. Confirma que las credenciales en `config.yaml` sean correctas
3. Asegúrate de que el archivo de búsqueda existe y tiene el formato correcto
4. **Si la aplicación se queda "colgada" o aparecen timeouts:**
   - Cambia `velocidad_internet` a `"lento"` o `"muy_lento"` en tu `config.yaml`
   - Si tienes internet rápido pero el sitio es lento, usa `"lento"`

### Errores comunes de timeout:
- **TimeoutError en navegación**: Cambia a `velocidad_internet: "lento"`
- **Elementos no encontrados**: Cambia a `velocidad_internet: "muy_lento"`
- **Operaciones que se cuelgan**: Cambia a `velocidad_internet: "muy_lento"`

## Contribuir

1. Hacer fork del repositorio
2. Crear rama para nueva funcionalidad
3. Implementar cambios
4. Hacer push a la rama
5. Crear Pull Request
