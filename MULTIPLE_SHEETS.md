# Funcionalidad de Selección Múltiple de Hojas

## 🎯 Nuevo Feature Implementado

Se ha implementado la capacidad de **seleccionar múltiples hojas** al momento de crear listas de suscriptores. Cada hoja seleccionada creará una lista de suscriptores separada e independiente.

## 📋 Hojas Disponibles

El archivo `data/Lista_envio.xlsx` contiene las siguientes hojas:
- Prueba20
- Prueba22

## 🖱️ Interfaz Gráfica (GUI)

Cuando ejecutes `python src/crear_lista.py`, aparecerá una ventana con:

- **Lista de hojas disponibles**
- **Selección múltiple habilitada**
- **Instrucciones**: "Selecciona las hojas a usar (mantén Ctrl/Cmd para seleccionar múltiples)"

### Uso:
1. Mantén presionado `Ctrl` (Windows/Linux) o `Cmd` (Mac)
2. Haz clic en cada hoja que quieras seleccionar
3. Haz clic en "Aceptar"

## 💻 Interfaz de Consola (CLI)

Si no hay GUI disponible, podrás seleccionar hojas usando texto:

### Formatos válidos:
- `1,2` - Selecciona hojas 1 y 2
- `1-2` - Selecciona hojas 1 y 2 (rango)
- `1,2,3` - Selecciona hojas 1, 2 y 3
- `1-3` - Selecciona hojas 1, 2 y 3 (rango)
- `1,3-5,7` - Selecciona hojas 1, 3, 4, 5 y 7 (combinado)

### Ejemplos para nuestro archivo:
- `1` - Solo hoja "Prueba20"
- `2` - Solo hoja "Prueba22"
- `1,2` - Ambas hojas
- `1-2` - Ambas hojas (rango)

## ⚙️ Procesamiento

El sistema procesará cada hoja seleccionada secuencialmente:

1. **Por cada hoja**:
   - Carga los datos de esa hoja específica
   - Navega a la sección de listas
   - Crea una nueva lista con el nombre de la hoja
   - Sube los datos de esa hoja únicamente
   - Configura los campos correspondientes
   - Confirma la importación

2. **Reporte final**:
   - Muestra cuántas listas se crearon exitosamente
   - Muestra cuáles fallaron (si las hay)
   - Notificación final con resumen

## 📊 Ejemplo de Salida

```
📋 Se crearán 2 listas de suscriptores:
  1. Prueba20
  2. Prueba22

🔄 Procesando hoja 1/2: Prueba20
📝 Creando lista: Prueba20
✅ Lista 'Prueba20' creada exitosamente

🔄 Procesando hoja 2/2: Prueba22
📝 Creando lista: Prueba22
✅ Lista 'Prueba22' creada exitosamente

📊 Resumen del procesamiento:
✅ Listas creadas exitosamente: 2
   - Prueba20
   - Prueba22
```

## 🚀 Cómo Usar

### Modo GUI (Recomendado):
```bash
cd /Users/andresgaibor/code/python/acumba-automation
python src/crear_lista.py
```

### Modo programático:
```python
from src.crear_lista import main

# Crear listas de múltiples hojas
main(multiple=True)

# Crear lista de una hoja específica
main(nombre_hoja="Prueba20", multiple=False)
```

## 🔧 Características Técnicas

- ✅ **Selección múltiple**: GUI con Ctrl/Cmd + click
- ✅ **Entrada flexible**: CLI con rangos y listas  
- ✅ **Procesamiento independiente**: Cada hoja = Una lista separada
- ✅ **Manejo de errores**: Continúa si una hoja falla
- ✅ **Reporte detallado**: Éxitos vs fallos
- ✅ **Limpieza automática**: Archivos temporales eliminados
- ✅ **Notificaciones**: Alertas del progreso y resultados