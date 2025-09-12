## Compilacion (incluyendo playwright)
```bash
pyinstaller --onefile --collect-all playwright app.py
```

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

1. Crear archivo `config.yaml` en la raíz del proyecto:
```yaml
user: "tu-usuario"
password: "tu-contraseña"
url: "https://url-del-servicio"
url_base: "https://url-base"
headless: false

# Configuración de velocidad de internet/carga
# Opciones: "rapido", "normal", "lento", "muy_lento"
velocidad_internet: "normal"
```

### Configuración de Velocidad de Internet

Simplemente cambia el valor de `velocidad_internet` según tu conexión:

- **`"rapido"`**: Para conexiones de fibra óptica o muy rápidas
- **`"normal"`**: Para conexiones estándar de banda ancha (por defecto)
- **`"lento"`**: Para conexiones lentas o inestables
- **`"muy_lento"`**: Para conexiones muy lentas o con alta latencia

**Ejemplos:**

```yaml
# Para internet rápido
velocidad_internet: "rapido"

# Para internet normal (recomendado)
velocidad_internet: "normal"

# Para internet lento
velocidad_internet: "lento"

# Para internet muy lento
velocidad_internet: "muy_lento"
```

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

El script generará un archivo Excel con dos hojas:
- **Hoja1**: Resumen general de los informes
- **Hoja2**: Detalle de suscriptores y seguimiento de URLs

## Estructura del proyecto

```
automation/
├── src/
│   └── demo.py
├── data/
│   datos_sesion.json
├── config.yaml
├── requirements.txt
└── README.md
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
