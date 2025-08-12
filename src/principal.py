import subprocess
import sys
import os

# Directorio base donde está el venv (este script asume que venv está en la raíz del proyecto)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
venv_dir = os.path.join(BASE_DIR, ".venv")

# Ruta correcta según sistema operativo
if os.name == "nt":  # Windows
    python_path = os.path.join(venv_dir, "Scripts", "python.exe")
else:  # Linux / macOS
    python_path = os.path.join(venv_dir, "bin", "python")

# Verificamos que exista
if not os.path.exists(python_path):
    print(f"❌ No se encontró el intérprete en: {python_path}")
    sys.exit(1)

# Ejecutar scripts
subprocess.run([python_path, os.path.join(BASE_DIR, "src", "listar_campanias.py")])
print("\nCierre el excel de busqueda antes de continuar")
respuesta = input("\nPresiona Enter para extraer la información (o 'c' para cancelar): ").strip().lower()

if respuesta == "c":
    print("Proceso cancelado.")
    exit()  # o sys.exit() si prefieres
else:
	print("Extrayendo informacion...")
	subprocess.run([python_path, os.path.join(BASE_DIR, "src", "demo.py")])