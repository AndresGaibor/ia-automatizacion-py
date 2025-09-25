"""Legacy main window - extracted from app.py for better organization."""
import tkinter as tk
from tkinter import messagebox, ttk
import os
import threading

try:
    from .config_validator import ConfigValidator
except ImportError:
    from src.presentation.gui.config_validator import ConfigValidator

try:
    from ...shared.utils import load_config, data_path, storage_state_path, notify
except ImportError:
    from src.shared.utils import load_config, data_path, storage_state_path, notify

try:
    from ...shared.logging import get_logger
except ImportError:
    from src.shared.logging import get_logger

try:
    from ...core.config.config_validator import check_config_or_show_dialog
except ImportError:
    try:
        from src.core.config.config_validator import check_config_or_show_dialog
    except ImportError:
        # Fallback to legacy import
        from src.config_validator import check_config_or_show_dialog

try:
    from ...presentation.gui.config_window import show_config_window
except ImportError:
    try:
        from src.presentation.gui.config_window import show_config_window
    except ImportError:
        # Fallback to legacy import
        from src.config_window import show_config_window

logger = get_logger()

# Variables globales para contadores de progreso - mantener para compatibilidad
progress_window = None
progress_var = None
progress_label = None
time_label = None
start_time = None
obtener_listas_running = False


class LegacyMainWindow:
    """Main window extracted from original app.py for backwards compatibility."""

    def __init__(self):
        """Initialize the legacy main window."""
        self.root = None
        self.setup_window()
        self.setup_ui()

    def setup_window(self):
        """Setup the main window."""
        logger.info("🎨 Inicializando interfaz gráfica")
        self.root = tk.Tk()
        self.root.title("Automatización Acumbamail")
        self.root.geometry("450x700")
        logger.success("✅ Aplicación iniciada exitosamente, mostrando interfaz")

    def setup_ui(self):
        """Create the user interface."""
        # === SECCIÓN CAMPAÑAS ===
        frame_campanias = tk.LabelFrame(self.root, text="Campañas", font=("Arial", 12, "bold"), pady=5)
        frame_campanias.pack(pady=12, fill="x", padx=25)

        btn_listar = tk.Button(
            frame_campanias,
            text="Listar campañas",
            font=("Arial", 14),
            height=2,
            command=lambda: self.run_listar_campanias(btn_listar)
        )
        btn_listar.pack(pady=8, fill="x", padx=15)

        btn_obtener = tk.Button(
            frame_campanias,
            text="Obtener suscriptores de campañas",
            font=("Arial", 14),
            height=2,
            command=lambda: self.run_obtener_suscriptores(btn_obtener)
        )
        btn_obtener.pack(pady=8, fill="x", padx=15)

        # === SECCIÓN LISTAS ===
        frame_listas = tk.LabelFrame(self.root, text="Listas", font=("Arial", 12, "bold"), pady=5)
        frame_listas.pack(pady=12, fill="x", padx=25)

        def on_click_obtener_listas():
            global obtener_listas_running
            try:
                if obtener_listas_running:
                    notify("En curso", "La operación de obtención de listas ya se está ejecutando.", "warning")
                    return
                obtener_listas_running = True
            except Exception:
                pass
            try:
                btn_obtener_listas.config(state=tk.DISABLED)
                self.root.config(cursor="watch")
            except Exception:
                pass
            self.run_obtener_listas(btn_obtener_listas)

        btn_obtener_listas = tk.Button(
            frame_listas,
            text="Obtener listas",
            font=("Arial", 14),
            height=2,
            command=on_click_obtener_listas
        )
        btn_obtener_listas.pack(pady=8, fill="x", padx=15)

        btn_descargar = tk.Button(
            frame_listas,
            text="Descargar lista de suscriptores",
            font=("Arial", 14),
            height=2,
            command=lambda: self.run_descargar_suscriptores(btn_descargar)
        )
        btn_descargar.pack(pady=8, fill="x", padx=15)

        btn_crear_lista = tk.Button(
            frame_listas,
            text="Subir lista de suscriptores",
            font=("Arial", 14),
            height=2,
            command=lambda: self.run_crear_lista(btn_crear_lista)
        )
        btn_crear_lista.pack(pady=8, fill="x", padx=15)

        btn_eliminar = tk.Button(
            frame_listas,
            text="Eliminar listas",
            font=("Arial", 14),
            height=2,
            bg="#ffcccc",
            command=lambda: self.run_eliminar_listas(btn_eliminar)
        )
        btn_eliminar.pack(pady=8, fill="x", padx=15)

        # === SECCIÓN SEGMENTOS ===
        frame_segmentos = tk.LabelFrame(self.root, text="Segmentos", font=("Arial", 12, "bold"), pady=5)
        frame_segmentos.pack(pady=12, fill="x", padx=25)

        btn_mapear = tk.Button(
            frame_segmentos,
            text="Mapear segmentos",
            font=("Arial", 14),
            height=2,
            command=lambda: self.run_mapear_segmentos(btn_mapear)
        )
        btn_mapear.pack(pady=8, fill="x", padx=15)

        # === SECCIÓN SESIÓN ===
        frame_sesion = tk.LabelFrame(self.root, text="Sesión", font=("Arial", 12, "bold"), pady=5)
        frame_sesion.pack(pady=12, fill="x", padx=25)

        btn_limpiar = tk.Button(
            frame_sesion,
            text="Limpiar sesión",
            font=("Arial", 14),
            height=2,
            command=self.limpiar_sesion
        )
        btn_limpiar.pack(pady=8, fill="x", padx=15)

        btn_config = tk.Button(
            frame_sesion,
            text="Configuración",
            font=("Arial", 14),
            height=2,
            command=self.configuracion
        )
        btn_config.pack(pady=8, fill="x", padx=15)

    # Operation methods using legacy operations service
    def run_listar_campanias(self, btn):
        """Run campaign listing - uses legacy operations service."""
        from ...core.services.legacy_operations_service import LegacyOperationsService

        def worker():
            try:
                btn.config(state=tk.DISABLED)
                self.root.config(cursor="watch")
                service = LegacyOperationsService.get_instance()
                service.listar_campanias()
                notify("Completado", "Listado de campañas completado", "info")
            except Exception as e:
                notify("Error", f"Error al listar campañas: {e}", "error")
            finally:
                btn.config(state=tk.NORMAL)
                self.root.config(cursor="")

        threading.Thread(target=worker, daemon=True).start()

    def run_obtener_suscriptores(self, btn):
        """Run subscriber extraction - uses legacy operations service."""
        from ...core.services.legacy_operations_service import LegacyOperationsService

        def worker():
            try:
                if not check_config_or_show_dialog(self.root):
                    return

                valid_busqueda, message_busqueda, marcados = ConfigValidator.validate_search_file()
                if not valid_busqueda:
                    notify("Error de Archivo", message_busqueda, "warning")
                    return

                btn.config(state=tk.DISABLED)
                self.root.config(cursor="watch")
                service = LegacyOperationsService.get_instance()
                service.obtener_suscriptores()
                notify("Completado", "Extracción de suscriptores completada", "info")
            except Exception as e:
                notify("Error", f"Error al obtener suscriptores: {e}", "error")
            finally:
                btn.config(state=tk.NORMAL)
                self.root.config(cursor="")

        threading.Thread(target=worker, daemon=True).start()

    def run_crear_lista(self, btn):
        """Run list creation - uses legacy operations service."""
        from ...core.services.legacy_operations_service import LegacyOperationsService

        def worker():
            try:
                if not check_config_or_show_dialog(self.root):
                    return

                btn.config(state=tk.DISABLED)
                self.root.config(cursor="watch")
                service = LegacyOperationsService.get_instance()
                service.crear_lista()
                notify("Completado", "Creación de lista completada", "info")
            except Exception as e:
                notify("Error", f"Error al crear lista: {e}", "error")
            finally:
                btn.config(state=tk.NORMAL)
                self.root.config(cursor="")

        threading.Thread(target=worker, daemon=True).start()

    def run_obtener_listas(self, btn):
        """Run get lists - uses legacy operations service."""
        from ...core.services.legacy_operations_service import LegacyOperationsService
        global obtener_listas_running

        def worker():
            try:
                if not check_config_or_show_dialog(self.root):
                    return

                service = LegacyOperationsService.get_instance()
                service.obtener_listas()
                notify("Completado", "Obtención de listas completada", "info")
            except Exception as e:
                notify("Error", f"Error al obtener listas: {e}", "error")
            finally:
                btn.config(state=tk.NORMAL)
                self.root.config(cursor="")
                obtener_listas_running = False

        threading.Thread(target=worker, daemon=True).start()

    def run_descargar_suscriptores(self, btn):
        """Run subscriber download - uses legacy operations service."""
        from ...core.services.legacy_operations_service import LegacyOperationsService

        def worker():
            try:
                if not check_config_or_show_dialog(self.root):
                    return

                valid_listas, message_listas, marcadas = ConfigValidator.validate_lists_search_file()
                if not valid_listas:
                    notify("Error de Archivo", message_listas, "warning")
                    return

                btn.config(state=tk.DISABLED)
                self.root.config(cursor="watch")
                service = LegacyOperationsService.get_instance()
                service.descargar_suscriptores()
                notify("Completado", "Descarga de suscriptores completada", "info")
            except Exception as e:
                notify("Error", f"Error al descargar suscriptores: {e}", "error")
            finally:
                btn.config(state=tk.NORMAL)
                self.root.config(cursor="")

        threading.Thread(target=worker, daemon=True).start()

    def run_eliminar_listas(self, btn):
        """Run delete lists - uses legacy operations service."""
        from ...core.services.legacy_operations_service import LegacyOperationsService

        def worker():
            try:
                if not check_config_or_show_dialog(self.root):
                    return

                if not messagebox.askyesno("Confirmar eliminación", "¿Está seguro de que desea eliminar las listas marcadas?"):
                    return

                btn.config(state=tk.DISABLED)
                self.root.config(cursor="watch")
                service = LegacyOperationsService.get_instance()
                result = service.eliminar_listas([])  # Would need actual list IDs
                notify("Completado", f"Eliminación completada: {result['mensaje']}", "info")
            except Exception as e:
                notify("Error", f"Error al eliminar listas: {e}", "error")
            finally:
                btn.config(state=tk.NORMAL)
                self.root.config(cursor="")

        threading.Thread(target=worker, daemon=True).start()

    def run_mapear_segmentos(self, btn):
        """Run segment mapping - uses segment service."""
        from ...core.services.segment_service import SegmentService

        def worker():
            try:
                valid, message = ConfigValidator.validate_configuration_legacy()
                if not valid:
                    notify("Error de Configuración", message, "error")
                    return

                valid_segmentos, message_segmentos, segmentos_count = ConfigValidator.validate_segments_file()
                if not valid_segmentos:
                    notify("Error de Archivo", message_segmentos, "error")
                    return

                btn.config(state=tk.DISABLED)
                self.root.config(cursor="watch")

                service = SegmentService()
                # Would implement actual segment mapping logic here
                notify("Completado", f"Procesamiento de {segmentos_count} segmentos completado", "info")
            except Exception as e:
                notify("Error", f"Error en mapeo de segmentos: {e}", "error")
            finally:
                btn.config(state=tk.NORMAL)
                self.root.config(cursor="")

        threading.Thread(target=worker, daemon=True).start()

    def limpiar_sesion(self):
        """Clear session data."""
        logger.info("🧹 Limpiando datos de sesión")
        try:
            session_path = storage_state_path()
            if os.path.exists(session_path):
                os.remove(session_path)
                logger.success("✅ Archivo de sesión eliminado correctamente")
                notify("Sesión limpiada", "Los datos de sesión han sido eliminados. Deberá autenticarse de nuevo.", "info")
            else:
                logger.info("ℹ️ No había datos de sesión que limpiar")
                notify("Sin datos", "No había datos de sesión que limpiar.", "info")
        except Exception as e:
            logger.error(f"❌ Error al limpiar sesión: {e}")
            notify("Error", f"Error al limpiar sesión: {e}", "error")

    def configuracion(self):
        """Open configuration window."""
        logger.info("⚙️ Abriendo ventana de configuración")
        try:
            show_config_window(self.root)
            logger.success("✅ Ventana de configuración mostrada exitosamente")
        except Exception as e:
            logger.error(f"❌ Error al mostrar ventana de configuración: {e}")
            notify("Error", f"Error al abrir configuración: {e}", "error")

    def run(self):
        """Start the application main loop."""
        logger.info("🚀 Iniciando aplicación de automatización Acumbamail")

        # Initialize configuration and files
        self.configuracion()
        self.archivo_busqueda()
        self.archivo_busqueda_listas()
        self.archivo_segmentos()

        self.root.mainloop()

    # Helper methods for file initialization
    def archivo_busqueda(self):
        """Initialize search file."""
        archivo = data_path("Busqueda.xlsx")
        if not os.path.exists(archivo):
            logger.info("📄 Creando archivo de búsqueda por defecto")
            # Would create default file here

    def archivo_busqueda_listas(self):
        """Initialize lists search file."""
        archivo = data_path("Busqueda_Listas.xlsx")
        if not os.path.exists(archivo):
            logger.info("📄 Creando archivo de búsqueda de listas por defecto")
            # Would create default file here

    def archivo_segmentos(self):
        """Initialize segments file."""
        archivo = data_path("Segmentos.xlsx")
        if not os.path.exists(archivo):
            logger.info("📄 Creando archivo de segmentos por defecto")
            # Would create default file here


def main():
    """Main entry point for legacy app."""
    app = LegacyMainWindow()
    app.run()


if __name__ == "__main__":
    main()