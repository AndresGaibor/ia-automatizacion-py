"""
Wrapper de compatibilidad - redirige a shared/utils/legacy_utils.py.

Este archivo existe solo para mantener compatibilidad con imports antiguos.
El código fuente real está en src/shared/utils/legacy_utils.py.
"""

import os
import sys
from pathlib import Path

# Configurar package para imports consistentes y PyInstaller compatibility
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "src"

# Forzar ruta de navegadores de Playwright antes de importar la librería
# Solo forzar ruta local de navegadores en builds PyInstaller (frozen).
def _early_project_root() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if getattr(sys, "frozen", False):
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(_early_project_root(), "ms-playwright"))
    os.makedirs(os.environ["PLAYWRIGHT_BROWSERS_PATH"], exist_ok=True)

# Re-exportar todo desde legacy_utils
from .shared.utils.legacy_utils import (
    # Funciones principales
    project_root,
    config_path,
    data_path,
    load_config,
    save_config,
    storage_state_path,
    ensure_playwright_browsers_path,
    crear_contexto_navegador,
    configurar_navegador,
    notify,
    ejecutando_desde_terminal,
    get_timeouts,
    # Funciones de carga
    cargar_id_campanias_a_buscar,
    cargar_campanias_a_buscar,
    cargar_terminos_busqueda,
    # Funciones deprecated pero aún en uso
    navegar_a_reportes,
    obtener_total_paginas,
    navegar_siguiente_pagina,
    click_element,
    is_on_login_page,
    validate_session,
)

# Constantes
REAL_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_6) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

__all__ = [
    "project_root",
    "config_path",
    "data_path",
    "load_config",
    "save_config",
    "storage_state_path",
    "ensure_playwright_browsers_path",
    "crear_contexto_navegador",
    "configurar_navegador",
    "notify",
    "ejecutando_desde_terminal",
    "get_timeouts",
    "cargar_id_campanias_a_buscar",
    "cargar_campanias_a_buscar",
    "cargar_terminos_busqueda",
    "navegar_a_reportes",
    "obtener_total_paginas",
    "navegar_siguiente_pagina",
    "click_element",
    "is_on_login_page",
    "validate_session",
    "REAL_UA",
]
