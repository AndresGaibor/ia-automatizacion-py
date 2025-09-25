"""Operation handlers for GUI actions - extracted from app.py to reduce complexity."""
import tkinter as tk
from tkinter import messagebox
import importlib
from typing import Optional

from .config_validator import ConfigValidator
from .progress_dialog import ThreadedOperation
from ...shared.utils import load_config, data_path, notify
from ...shared.logging import get_logger
from ...config_validator import check_config_or_show_dialog

logger = get_logger()


class OperationHandlers:
    """Handles all GUI operations with proper threading and error handling."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.obtener_listas_running = False

    def run_listar_campanias(self, btn: tk.Button) -> None:
        """Run campaign listing operation."""
        logger.info("🚀 Starting campaign listing process")

        def operation(progress):
            progress.update_progress("Validating configuration...")

            # Validate configuration with automatic dialog
            if not check_config_or_show_dialog(self.root):
                logger.warning("❌ Invalid configuration, canceling process")
                raise ValueError("Configuration validation failed")

            progress.update_progress("Loading campaign module...")
            logger.info("📥 Importing listar_campanias module")
            import src.listar_campanias as m
            importlib.reload(m)

            progress.update_progress("Processing campaigns...")
            logger.info("⚙️ Executing main campaign listing function")
            m.main()

            logger.success("✅ Campaign listing completed successfully")

        def on_complete(success: bool, error: Optional[Exception]):
            if success:
                notify("Completed", "Campaign listing finished successfully", "info")
            else:
                logger.error(f"❌ Error listing campaigns: {error}")
                notify("Error", f"Error listing campaigns: {error}", "error")

            btn.config(state=tk.NORMAL)
            self.root.config(cursor="")

        btn.config(state=tk.DISABLED)
        self.root.config(cursor="watch")

        threaded_op = ThreadedOperation(
            self.root,
            operation,
            "Listing Campaigns",
            on_complete
        )
        threaded_op.start()

    def run_obtener_suscriptores(self, btn: tk.Button) -> None:
        """Run subscriber extraction operation."""
        logger.info("🚀 Starting subscriber extraction process")

        def operation(progress):
            progress.update_progress("Validating configuration...")

            # Validate configuration with automatic dialog
            if not check_config_or_show_dialog(self.root):
                logger.warning("❌ Invalid configuration, canceling process")
                raise ValueError("Configuration validation failed")

            progress.update_progress("Validating search file...")
            # Validate search file
            logger.info("🔍 Validating search file")
            valid_busqueda, message_busqueda, marcados = ConfigValidator.validate_search_file()
            if not valid_busqueda:
                logger.warning(f"❌ Invalid search file: {message_busqueda}")
                raise ValueError(f"Search file validation failed: {message_busqueda}")

            progress.update_progress("Loading subscriber extraction module...")
            logger.info(f"📥 Importing demo module - Campaigns to process: {marcados}")
            import src.demo as m
            importlib.reload(m)

            progress.update_progress("Processing campaigns and extracting subscribers...")
            logger.info("⚙️ Executing main subscriber extraction function")
            m.main()

            logger.success("✅ Subscriber extraction completed successfully")

        def on_complete(success: bool, error: Optional[Exception]):
            if success:
                notify("Completed", "Subscriber extraction finished successfully", "info")
            else:
                logger.error(f"❌ Error extracting subscribers: {error}")
                error_msg = str(error)
                if "Error en campaña" in error_msg:
                    notify("Campaign Error", f"The selected campaign is not available or was deleted: {error_msg}", "error")
                else:
                    notify("Error", f"Error extracting subscribers: {error_msg}", "error")

            btn.config(state=tk.NORMAL)
            self.root.config(cursor="")

        btn.config(state=tk.DISABLED)
        self.root.config(cursor="watch")

        threaded_op = ThreadedOperation(
            self.root,
            operation,
            "Extracting Subscribers",
            on_complete
        )
        threaded_op.start()

    def run_crear_lista(self, btn: tk.Button) -> None:
        """Run list creation operation."""
        logger.info("🚀 Starting list creation process")

        def operation(progress):
            progress.update_progress("Validating configuration...")

            # Validate configuration with automatic dialog
            if not check_config_or_show_dialog(self.root):
                logger.warning("❌ Invalid configuration, canceling process")
                raise ValueError("Configuration validation failed")

            # Verify list configuration
            progress.update_progress("Validating list configuration...")
            logger.info("🔍 Validating list configuration")
            config = load_config()
            lista_config = config.get('lista', {})
            if not lista_config.get('sender_email') or lista_config.get('sender_email') == 'usuario@correo.com':
                logger.error("❌ Incomplete list configuration", sender_email=lista_config.get('sender_email'))
                raise ValueError("Error: Missing list configuration (sender_email, company, etc.) in config.yaml")

            progress.update_progress("Loading list creation module...")
            logger.info("📥 Importing crear_lista_mejorado module")
            import src.crear_lista_mejorado as m
            importlib.reload(m)

            progress.update_progress("Validating data and uploading to Acumbamail...")
            # Execute automatic creation
            logger.info("⚙️ Executing main list creation function")
            m.main_automatico()

            logger.success("✅ List creation completed successfully")

        def on_complete(success: bool, error: Optional[Exception]):
            if success:
                notify("Completed", "Subscriber list uploaded successfully", "info")
            else:
                logger.error(f"❌ Error creating list: {error}")
                notify("Error", f"Error creating list: {error}", "error")

            btn.config(state=tk.NORMAL)
            self.root.config(cursor="")

        btn.config(state=tk.DISABLED)
        self.root.config(cursor="watch")

        threaded_op = ThreadedOperation(
            self.root,
            operation,
            "Creating List",
            on_complete
        )
        threaded_op.start()

    def run_obtener_listas(self, btn: tk.Button) -> None:
        """Run list retrieval operation."""
        if self.obtener_listas_running:
            logger.warning("⚠️ List retrieval operation already running")
            return

        self.obtener_listas_running = True
        logger.info("🚀 Starting list retrieval process")

        def operation(progress):
            progress.update_progress("Validating configuration...")

            # Validate configuration with automatic dialog
            if not check_config_or_show_dialog(self.root):
                logger.warning("❌ Invalid configuration, canceling process")
                raise ValueError("Configuration validation failed")

            progress.update_progress("Loading list retrieval module...")
            logger.info("📥 Importing obtener_listas module")
            import src.obtener_listas as m
            importlib.reload(m)

            def progress_callback(msg: str):
                if msg.startswith('__ESTIMATED_TIME__:'):
                    return  # Skip estimated time messages in new system
                progress.update_progress(msg)

            progress.update_progress("Connecting to Acumbamail API...")
            logger.info("⚙️ Executing main list retrieval function")
            m.main(progress_callback=progress_callback)

            # Read resulting Excel and notify path + saved rows to avoid confusion
            try:
                import pandas as _pd
                archivo = data_path("Busqueda_Listas.xlsx")
                df_after = _pd.read_excel(archivo)
                filas = len(df_after)
                logger.success(f"✅ List retrieval completed: {filas} rows saved", archivo=archivo, filas=filas)
                return f"List retrieval finished: {filas} rows saved in {archivo}"
            except Exception as e:
                logger.success("✅ List retrieval completed successfully", error=str(e))
                return "List retrieval finished successfully"

        def on_complete(success: bool, error: Optional[Exception]):
            try:
                if success:
                    notify("Completed", "List retrieval finished successfully", "info")
                else:
                    logger.error(f"❌ Error retrieving lists: {error}")
                    notify("Error", f"Error retrieving lists: {error}", "error")

                btn.config(state=tk.NORMAL)
                self.root.config(cursor="")
            finally:
                self.obtener_listas_running = False

        btn.config(state=tk.DISABLED)
        self.root.config(cursor="watch")

        threaded_op = ThreadedOperation(
            self.root,
            operation,
            "Retrieving Lists",
            on_complete
        )
        threaded_op.start()

    def run_descargar_suscriptores(self, btn: tk.Button) -> None:
        """Run subscriber download operation."""
        logger.info("🚀 Starting subscriber download process")

        def operation(progress):
            progress.update_progress("Validating configuration...")

            # Validate configuration with automatic dialog
            if not check_config_or_show_dialog(self.root):
                logger.warning("❌ Invalid configuration, canceling process")
                raise ValueError("Configuration validation failed")

            progress.update_progress("Validating lists search file...")
            # Validate lists search file
            logger.info("🔍 Validating lists search file")
            valid_listas, message_listas, marcadas = ConfigValidator.validate_lists_search_file()
            if not valid_listas:
                logger.warning(f"❌ Invalid lists search file: {message_listas}")
                raise ValueError(f"Lists search file validation failed: {message_listas}")

            progress.update_progress("Loading subscriber download module...")
            logger.info("📥 Importing descargar_suscriptores module")
            import src.descargar_suscriptores as m
            importlib.reload(m)

            progress.update_progress("Downloading subscriber data...")
            logger.info("⚙️ Executing main subscriber download function")
            m.main()

            logger.success("✅ Subscriber download completed successfully")

        def on_complete(success: bool, error: Optional[Exception]):
            if success:
                notify("Completed", "Subscriber download finished successfully", "info")
            else:
                logger.error(f"❌ Error downloading subscribers: {error}")
                notify("Error", f"Error downloading subscribers: {error}", "error")

            btn.config(state=tk.NORMAL)
            self.root.config(cursor="")

        btn.config(state=tk.DISABLED)
        self.root.config(cursor="watch")

        threaded_op = ThreadedOperation(
            self.root,
            operation,
            "Downloading Subscribers",
            on_complete
        )
        threaded_op.start()

    def run_eliminar_listas(self, btn: tk.Button) -> None:
        """Run list deletion operation."""
        logger.info("🚀 Starting list deletion process")

        def operation(progress):
            progress.update_progress("Validating configuration...")

            # Validate configuration with automatic dialog
            if not check_config_or_show_dialog(self.root):
                logger.warning("❌ Invalid configuration, canceling process")
                raise ValueError("Configuration validation failed")

            progress.update_progress("Loading list deletion module...")
            logger.info("📥 Importing eliminar_listas module")
            import src.eliminar_listas as m
            importlib.reload(m)

            progress.update_progress("Validating lists file for deletion...")
            # Validate file before continuing
            logger.info("🔍 Validating lists search file for deletion")
            valid_listas, message_listas, marcadas = m.validar_archivo_busqueda_listas()
            if not valid_listas:
                logger.warning(f"❌ Invalid lists search file: {message_listas}")
                raise ValueError(f"Lists search file validation failed: {message_listas}")

            logger.info(f"⚠️ Requesting confirmation to delete {marcadas} lists")

            # User confirmation - need to do this on main thread
            confirmation_result = {'confirmed': False}

            def ask_confirmation():
                confirmation_result['confirmed'] = messagebox.askyesno(
                    "Confirm deletion",
                    f"You are about to delete {marcadas} lists in Acumbamail. Continue?"
                )

            self.root.after_idle(ask_confirmation)

            # Wait for confirmation
            import time
            while 'confirmed' not in confirmation_result:
                time.sleep(0.1)

            if not confirmation_result['confirmed']:
                logger.info("↩️ Deletion canceled by user")
                raise ValueError("Deletion canceled by user")

            progress.update_progress("Executing list deletion...")
            # Execute deletion
            logger.info("🗑️ Executing list deletion")
            exitosas, fallidas, mensaje = m.eliminar_listas_marcadas()

            logger.success(f"✅ Deletion completed: {exitosas} successful, {fallidas} failed", exitosas=exitosas, fallidas=fallidas)
            return exitosas, fallidas, mensaje

        def on_complete(success: bool, error: Optional[Exception]):
            if success:
                # Handle successful deletion result
                notify("Deletion Result", "Lists deleted successfully", "info")
            else:
                if "canceled by user" in str(error).lower():
                    logger.info("↩️ Deletion canceled by user")
                    # Don't show error for user cancellation
                else:
                    logger.error(f"❌ Error deleting lists: {error}")
                    notify("Error", f"Error deleting lists: {error}", "error")

            btn.config(state=tk.NORMAL)
            self.root.config(cursor="")

        btn.config(state=tk.DISABLED)
        self.root.config(cursor="watch")

        threaded_op = ThreadedOperation(
            self.root,
            operation,
            "Deleting Lists",
            on_complete
        )
        threaded_op.start()