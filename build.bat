@echo off
echo 🚀 Iniciando proceso de compilación de Acumba Automation

REM Verificar que estamos en el directorio correcto
if not exist "app.py" (
    echo ❌ Error: app.py no encontrado. Ejecute desde el directorio raíz del proyecto.
    pause
    exit /b 1
)

REM Activar entorno virtual
echo 📦 Activando entorno virtual...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo ❌ Error: No se encontró entorno virtual en .venv o venv
    pause
    exit /b 1
)

REM Verificar dependencias críticas
echo 🔍 Verificando dependencias críticas...
python -c "import pydantic; print('✅ pydantic:', pydantic.__version__)" || (
    echo ❌ Error: pydantic no está instalado
    echo 💡 Ejecute: pip install -r requirements.txt
    pause
    exit /b 1
)

python -c "import playwright; print('✅ playwright:', playwright.__version__)" || (
    echo ❌ Error: playwright no está instalado
    pause
    exit /b 1
)

python -c "import pandas; print('✅ pandas:', pandas.__version__)" || (
    echo ❌ Error: pandas no está instalado
    pause
    exit /b 1
)

REM Limpiar compilaciones anteriores
echo 🧹 Limpiando compilaciones anteriores...
if exist "build\" rmdir /s /q "build\"
if exist "dist\" rmdir /s /q "dist\"
del /q *.pyc 2>nul

REM Compilar usando el archivo .spec
echo 🔨 Compilando aplicación...
pyinstaller app.spec

REM Verificar que la compilación fue exitosa
if exist "dist\acumba-automation.exe" (
    echo ✅ Compilación exitosa!
    echo 📦 Ejecutable creado en: dist\
    dir dist\

    echo.
    echo 🎉 Proceso completado!
    echo 📦 El ejecutable está listo en la carpeta dist\
) else (
    echo ❌ Error en la compilación
    echo 📋 Revise los logs arriba para más detalles
)

pause