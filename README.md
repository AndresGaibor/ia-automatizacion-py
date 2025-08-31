## Compilacion (incluyendo playwright)
```bash
pyinstaller --onefile --collect-all playwright app.py
```

# Acumba Automation

Automatización para obtener reportes de campañas de email marketing.

## Requisitos previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clonar el repositorio:
```bash
git clone <url-repositorio>
cd acumba-automation
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
archivo_busqueda: "ruta/al/archivo.xlsx"
archivo_informes: "ruta/donde/guardar/informes.xlsx"
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
acumba-automation/
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

## Contribuir

1. Hacer fork del repositorio
2. Crear rama para nueva funcionalidad
3. Implementar cambios
4. Hacer push a la rama
5. Crear Pull Request
