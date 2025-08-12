setlocal
cd /d "%~dp0"

REM Crear venv si no existe
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv || python -m venv .venv
)

REM ACTIVAR: usar CALL para que el .bat continúe
call .venv\Scripts\activate

REM Usar el python del venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install

python ".\src\principal.py"

echo.
pause