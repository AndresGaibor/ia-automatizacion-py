"""
Ejecuta operaciones en worker threads con manejo automático de UI.
Reemplaza el boilerplate repetitivo de threading en app.py.
"""
import threading
import tkinter as tk
from typing import Callable, Optional

from src.shared.utils.legacy_utils import notify
from src.shared.logging.logger import get_logger

logger = get_logger()


def start_worker(
    btn: tk.Button,
    root: tk.Tk,
    target: Callable[[], None],
    on_success: Optional[str] = None,
    on_error: Optional[Callable[[Exception], str]] = None,
    finally_hook: Optional[Callable[[], None]] = None,
):
    """Inicia un worker thread con lock de UI y restauración automática.

    Args:
        btn: Botón que se deshabilita durante la ejecución
        root: Ventana principal (para cursor y root.after)
        target: Función a ejecutar en el thread
        on_success: Mensaje de éxito (None = no notificar)
        on_error: Callable que recibe la excepción y retorna mensaje de error
        finally_hook: Callable opcional para cleanup adicional
    """
    btn.config(state=tk.DISABLED)
    root.config(cursor="watch")

    def wrapper():
        try:
            target()
            if on_success:
                root.after(0, lambda: notify("Completado", on_success or "", "info"))
        except Exception as e:
            error_msg = on_error(e) if on_error else str(e)
            logger.error(f"Error en worker: {error_msg}", exc_info=True)
            root.after(0, lambda: notify("Error", error_msg, "error"))
        finally:
            root.after(0, lambda: btn.config(state=tk.NORMAL))
            root.after(0, lambda: root.config(cursor=""))
            if finally_hook:
                root.after(0, finally_hook)

    threading.Thread(target=wrapper, daemon=True).start()
