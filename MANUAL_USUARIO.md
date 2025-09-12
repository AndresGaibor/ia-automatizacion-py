# Manual de Usuario - Automatización Acumbamail

## 📋 Índice
1. [¿Qué es esta aplicación?](#qué-es-esta-aplicación)
2. [Opción 1: Usar la versión compilada (RECOMENDADO)](#opción-1-usar-la-versión-compilada-recomendado)
3. [Opción 2: Instalar desde código fuente](#opción-2-instalar-desde-código-fuente)
4. [Configuración inicial](#configuración-inicial)
5. [Cómo usar la aplicación](#cómo-usar-la-aplicación)
6. [Resolución de problemas](#resolución-de-problemas)
7. [Preguntas frecuentes](#preguntas-frecuentes)

---

## ¿Qué es esta aplicación?

Esta aplicación automatiza tareas en **Acumbamail** para:
- 📧 Extraer reportes de campañas de email marketing
- 📊 Generar informes en Excel con datos de apertura, clics y suscriptores
- 📋 Crear listas de suscriptores masivamente
- ⚡ Ahorrar horas de trabajo manual

---

## Opción 1: Usar la versión compilada (RECOMENDADO)

### 🎯 **Para usuarios no técnicos - La forma más fácil**

#### Paso 1: Descargar la aplicación
1. Ve a: https://github.com/AndresGaibor/ia-automatizacion-py/releases
2. Busca la **versión más reciente** (v2.1.0 o superior)
3. Descarga el archivo **`app.exe`** (Windows) o **`app`** (Mac/Linux)
4. Guarda el archivo en una carpeta de tu preferencia (ej: `Documentos/AcumbamailBot`)

#### Paso 2: Preparar archivos de configuración
1. En la misma carpeta donde descargaste `app.exe`, crea:
   - Una carpeta llamada **`data`**
   - Un archivo llamado **`config.yaml`** (usa el Bloc de notas)

#### Paso 3: Configurar el archivo config.yaml
Abre `config.yaml` con el Bloc de notas y copia esto:

```yaml
acumbamail:
  login_url: "https://acumbamail.com/apiv2/login/"
  usuario: "tu_email@ejemplo.com"
  contraseña: "tu_contraseña"
  
configuracion:
  velocidad_internet: "media"  # opciones: rapida, media, lenta
  tiempo_espera_maximo: 30
```

⚠️ **Importante**: Cambia `tu_email@ejemplo.com` y `tu_contraseña` por tus credenciales reales de Acumbamail.

#### Paso 4: Preparar archivos de datos
Dentro de la carpeta **`data`**, necesitas:

**Para extraer reportes:**
- `Busqueda.xlsx` - Excel con los términos de búsqueda

**Para crear listas:**
- `Lista_envio.xlsx` - Excel con las listas de emails

#### Paso 5: Ejecutar la aplicación
1. **Doble clic** en `app.exe` (Windows) o `app` (Mac/Linux)
2. Se abrirá una ventana con botones para cada función
3. ¡Listo para usar!

---

## Opción 2: Instalar desde código fuente

### 🛠️ **Para usuarios técnicos o si necesitas personalizar**

#### Opción 2A: Descargar como ZIP

1. **Descargar:**
   - Ve a: https://github.com/AndresGaibor/ia-automatizacion-py
   - Clic en el botón verde **"Code"**
   - Selecciona **"Download ZIP"**
   - Extrae el archivo ZIP en tu computadora

#### Opción 2B: Clonar con Git

```bash
# Si tienes Git instalado
git clone https://github.com/AndresGaibor/ia-automatizacion-py.git
cd ia-automatizacion-py
```

#### Paso 1: Instalar Python
- **Windows**: Descarga desde https://python.org (versión 3.8 o superior)
- **Mac**: `brew install python3` o desde python.org
- **Linux**: `sudo apt install python3 python3-pip python3-venv`

#### Paso 2: Crear entorno virtual
Abre una terminal/consola en la carpeta del proyecto:

**Windows:**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Paso 3: Instalar dependencias
```bash
pip install -r requirements.txt
playwright install
```

#### Paso 4: Ejecutar la aplicación
```bash
# Interfaz gráfica
python app.py

# O desde línea de comandos
python -m src.demo
python -m src.listar_campanias
```

---

## Configuración inicial

### 📁 Estructura de archivos necesaria

```
tu_carpeta/
├── app.exe (o app)              # La aplicación
├── config.yaml                 # Tu configuración
├── data/                       # Carpeta de datos
│   ├── Busqueda.xlsx           # Para búsquedas de campañas
│   ├── Lista_envio.xlsx        # Para crear listas
│   └── automation_YYYYMMDD.log # Logs (se crean automáticamente)
└── ms-playwright/              # Se crea automáticamente
```

### ⚙️ Configuración de velocidad de internet

En `config.yaml`, ajusta según tu conexión:

```yaml
configuracion:
  velocidad_internet: "rapida"    # Internet rápido (fibra óptica)
  # velocidad_internet: "media"   # Internet normal (ADSL/cable)
  # velocidad_internet: "lenta"   # Internet lento o inestable
```

### 📊 Preparar archivos Excel

#### Para extraer reportes (`data/Busqueda.xlsx`):
| Buscar | Nombre | Tipo | Fecha envío | Listas | Emails | Abiertos | Clics |
|--------|--------|------|-------------|--------|--------|----------|-------|
| newsletter | Newsletter Enero | email | 2024-01-15 | Lista1 | 1000 | 250 | 45 |

#### Para crear listas (`data/Lista_envio.xlsx`):
| Email | Nombre | Apellido |
|-------|--------|----------|
| juan@ejemplo.com | Juan | Pérez |
| maria@ejemplo.com | María | González |

---

## Cómo usar la aplicación

### 🖥️ Interfaz Gráfica (GUI)

1. **Ejecuta** `app.exe` (doble clic)
2. **Selecciona** la función que necesitas:
   - **"Extraer Reportes"**: Para obtener datos de campañas
   - **"Listar Campañas"**: Para ver todas las campañas
   - **"Crear Listas"**: Para subir listas de suscriptores

3. **Sigue** las instrucciones en pantalla
4. **Los resultados** se guardan en la carpeta `data/`

### 💻 Línea de Comandos (CLI)

Si instalaste desde código fuente:

```bash
# Activar entorno virtual (si no está activo)
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# Extraer reportes de campañas
python -m src.demo

# Listar todas las campañas
python -m src.listar_campanias

# Crear listas de suscriptores
python -m src.crear_lista
```

### 📈 Selección múltiple de hojas Excel

**En la interfaz gráfica:**
- Mantén presionado `Ctrl` (Windows) o `Cmd` (Mac) y clic en varias hojas

**En línea de comandos:**
- Rangos: `1-5` (hojas 1 a 5)
- Lista: `1,3,7` (hojas 1, 3 y 7)
- Combinado: `1-3,5,8-10`

---

## Resolución de problemas

### ❌ Problemas comunes

#### "No se puede conectar a Acumbamail"
- ✅ Verifica tus credenciales en `config.yaml`
- ✅ Revisa tu conexión a internet
- ✅ Cambia `velocidad_internet` a `"lenta"` si tienes problemas de conexión

#### "Error: No se encuentra el archivo Excel"
- ✅ Asegúrate de que `data/Busqueda.xlsx` existe
- ✅ Verifica que el archivo no esté abierto en Excel
- ✅ Revisa que las columnas tengan los nombres correctos

#### "La aplicación se cierra inesperadamente"
- ✅ Ejecuta desde terminal para ver errores:
  ```bash
  # Windows
  cd carpeta_de_la_aplicacion
  app.exe
  
  # Mac/Linux
  cd carpeta_de_la_aplicacion
  ./app
  ```

#### "Timeout al cargar la página"
- ✅ Cambia la configuración de velocidad:
  ```yaml
  configuracion:
    velocidad_internet: "lenta"
    tiempo_espera_maximo: 60  # Aumentar tiempo de espera
  ```

### 🔍 Ver logs detallados

Los logs se guardan automáticamente en `data/automation_YYYYMMDD.log`

Para monitorear en tiempo real:
```bash
# Si instalaste desde código fuente
python monitor_logs.py
```

### 🆘 Obtener ayuda

1. **Revisa los logs** en `data/automation_*.log`
2. **Ejecuta en modo debug**:
   ```bash
   python debug_script.py  # Si instalaste desde código fuente
   ```
3. **Reporta problemas** en: https://github.com/AndresGaibor/ia-automatizacion-py/issues

---

## Preguntas frecuentes

### ❓ ¿Necesito mantener el navegador abierto?
**No**. La aplicación controla su propio navegador automáticamente.

### ❓ ¿Puedo usar la aplicación mientras hago otras cosas?
**Sí**, pero evita usar Acumbamail manualmente mientras la automatización está corriendo.

### ❓ ¿Qué pasa si se interrumpe el proceso?
La aplicación guarda el progreso y puedes reanudar desde donde se quedó.

### ❓ ¿Es seguro introducir mis credenciales?
**Sí**. Las credenciales se almacenan localmente en tu computadora y solo se usan para automatizar el login.

### ❓ ¿Cuánto tiempo toma procesar las campañas?
Depende de:
- Cantidad de campañas: ~30 segundos por campaña
- Velocidad de internet: Configura según tu conexión
- Número de páginas de resultados

### ❓ ¿Puedo procesar múltiples archivos Excel a la vez?
**Sí**. Usa la selección múltiple de hojas o coloca varios archivos en `data/`.

### ❓ ¿Funciona en Mac y Linux?
**Sí**. La aplicación es compatible con Windows, Mac y Linux.

---

## 🎉 ¡Listo para automatizar!

Con este manual tienes todo lo necesario para usar la aplicación de automatización de Acumbamail. Si tienes dudas adicionales, revisa los logs o reporta el problema en GitHub.

**¡Que disfrutes ahorrando tiempo con la automatización! 🚀**