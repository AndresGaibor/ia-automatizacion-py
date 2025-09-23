#!/bin/bash

echo "🚀 Iniciando proceso de compilación de Acumba Automation"

# Verificar que estamos en el directorio correcto
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py no encontrado. Ejecute desde el directorio raíz del proyecto."
    exit 1
fi

# Activar entorno virtual
echo "📦 Activando entorno virtual..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "❌ Error: No se encontró entorno virtual en .venv o venv"
    exit 1
fi

# Verificar que las dependencias estén instaladas
echo "🔍 Verificando dependencias críticas..."
python -c "import pydantic; print('✅ pydantic:', pydantic.__version__)" || {
    echo "❌ Error: pydantic no está instalado"
    echo "💡 Ejecute: pip install -r requirements.txt"
    exit 1
}

python -c "import playwright; print('✅ playwright:', playwright.__version__)" || {
    echo "❌ Error: playwright no está instalado"
    exit 1
}

python -c "import pandas; print('✅ pandas:', pandas.__version__)" || {
    echo "❌ Error: pandas no está instalado"
    exit 1
}

# Limpiar compilaciones anteriores
echo "🧹 Limpiando compilaciones anteriores..."
rm -rf build/
rm -rf dist/
rm -f *.pyc
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Compilar usando el archivo .spec
echo "🔨 Compilando aplicación..."
pyinstaller app.spec

# Verificar que la compilación fue exitosa
if [ -f "dist/acumba-automation" ] || [ -f "dist/acumba-automation.exe" ]; then
    echo "✅ Compilación exitosa!"
    echo "📦 Ejecutable creado en: dist/"
    ls -la dist/

    # Opcional: probar el ejecutable
    echo ""
    echo "🧪 ¿Desea probar el ejecutable? (y/n)"
    read -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔍 Probando ejecutable..."
        if [ -f "dist/acumba-automation" ]; then
            ./dist/acumba-automation --help 2>&1 | head -10
        else
            ./dist/acumba-automation.exe --help 2>&1 | head -10
        fi
    fi
else
    echo "❌ Error en la compilación"
    echo "📋 Revise los logs arriba para más detalles"
    exit 1
fi

echo ""
echo "🎉 Proceso completado!"
echo "📦 El ejecutable está listo en la carpeta dist/"