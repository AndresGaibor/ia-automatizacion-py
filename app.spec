# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import sys
import os

# Agregar el directorio src al path de Python
src_path = os.path.join(os.path.dirname(os.path.abspath(SPEC)), 'src')
sys.path.insert(0, src_path)

# Recopilar módulos
datas = []
binaries = []
hiddenimports = []

# Recopilar Playwright
tmp_ret = collect_all('playwright')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Recopilar Pydantic
tmp_ret = collect_all('pydantic')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Recopilar otros módulos críticos
for module in ['httpx', 'httpcore', 'pandas', 'openpyxl', 'email_validator']:
    try:
        tmp_ret = collect_all(module)
        datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
    except:
        pass

# Módulos adicionales necesarios
additional_hiddenimports = [
    # Core Python modules
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',

    # Pydantic core
    'pydantic_core',
    'pydantic_core._pydantic_core',
    'email_validator',

    # HTTP stack
    'h11',
    'anyio',
    'sniffio',
    'certifi',
    'charset_normalizer',
    'idna',
    'urllib3',

    # Concurrency
    'threading',
    'concurrent.futures',

    # Project modules
    'src',
    'src.utils',
    'src.logger',
    'src.api',
    'src.api.models.suscriptores',
    'src.api.models.campanias',
    'src.api.models.base',
    'src.api.endpoints.suscriptores',
    'src.excel_helper',
    'src.crear_lista_mejorado',
    'src.demo',
    'src.listar_campanias',
    'src.autentificacion',
]

hiddenimports.extend(additional_hiddenimports)

# Archivos de datos
project_datas = []
# Incluir archivos de configuración si existen
if os.path.exists('config.yaml'):
    project_datas.append(('config.yaml', '.'))
if os.path.exists('data'):
    project_datas.append(('data', 'data'))
if os.path.exists('src'):
    project_datas.append(('src', 'src'))

datas.extend(project_datas)

a = Analysis(
    ['app.py'],
    pathex=['.', 'src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir módulos pesados innecesarios
        'matplotlib',
        'scipy',
        'IPython',
        'notebook',
        'jupyter',
        'pytest',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='acumba-automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
