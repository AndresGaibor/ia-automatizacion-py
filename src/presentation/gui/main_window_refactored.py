"""Refactored main window using new architecture and extracted components."""
import tkinter as tk
from tkinter import messagebox, ttk
import os
from pathlib import Path

# New architecture imports
from ...core.config.config_manager import ConfigManager
from .config_validator import ConfigValidator
from .operation_handlers import OperationHandlers
from .progress_dialog import ProgressDialog, ThreadedOperation

# Backward compatibility imports
from ...shared.utils import load_config, data_path, storage_state_path, notify
from ...config_window import show_config_window
from ...config.settings import settings
from ...config_validator import check_config_or_show_dialog
from ...shared.logging import get_logger

logger = get_logger()


class MainWindowRefactored:
    """Refactored main window with improved architecture and separation of concerns."""

    # Default configuration
    DEFAULTS = {
        'url': 'https://acumbamail.com/app/newsletter/',
        'url_base': 'https://acumbamail.com',
        'user': 'usuario@correo.com',
        'password': 'clave',
        'headless': False,
        'timeouts': {
            'navigation': 60,
            'element': 15,
            'upload': 120,
            'default': 30
        },
        'api': {
            'base_url': 'https://acumbamail.com/api/1/',
            'api_key': ''
        },
        'lista': {
            'sender_email': 'usuario@correo.com',
            'company': 'Tu Empresa',
            'country': 'España',
            'city': 'Tu Ciudad',
            'address': 'Tu Dirección',
            'phone': '+34 000 000 000'
        }
    }

    def __init__(self):
        self.root = tk.Tk()
        self.config_manager = ConfigManager()
        self.config_validator = ConfigValidator()
        self.operation_handlers = OperationHandlers(self.root)

        self._setup_window()
        self._create_ui()
        self._initialize_config()

    def _setup_window(self):
        """Set up main window properties."""
        self.root.title("Acumbamail Automation Tool")
        self.root.geometry("600x800")
        self.root.resizable(True, True)

        # Configure grid weights for responsive layout
        self.root.columnconfigure(0, weight=1)

    def _initialize_config(self):
        """Initialize configuration manager."""
        try:
            config_path = Path("config.yaml")
            self.config_manager.load(config_path, self.DEFAULTS)
            logger.info("✅ Configuration loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            notify("Configuration Error", f"Failed to load configuration: {e}", "error")

    def _create_ui(self):
        """Create the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="Acumbamail Automation Tool",
            font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, pady=(0, 20))

        # Configuration section
        self._create_config_section(main_frame, 1)

        # Operations section
        self._create_operations_section(main_frame, 2)

        # Advanced operations section
        self._create_advanced_section(main_frame, 3)

        # Status section
        self._create_status_section(main_frame, 4)

    def _create_config_section(self, parent, row):
        """Create configuration section."""
        config_frame = ttk.LabelFrame(parent, text="Configuration", padding="10")
        config_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)

        # Configuration status
        self.config_status_var = tk.StringVar(value="Checking configuration...")
        status_label = ttk.Label(config_frame, textvariable=self.config_status_var)
        status_label.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Configuration buttons
        ttk.Button(
            config_frame,
            text="Edit Configuration",
            command=self._edit_config
        ).grid(row=1, column=0, padx=(0, 5), sticky=(tk.W, tk.E))

        ttk.Button(
            config_frame,
            text="Validate Configuration",
            command=self._validate_config
        ).grid(row=1, column=1, padx=(5, 0), sticky=(tk.W, tk.E))

        # Update configuration status
        self._update_config_status()

    def _create_operations_section(self, parent, row):
        """Create main operations section."""
        ops_frame = ttk.LabelFrame(parent, text="Main Operations", padding="10")
        ops_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ops_frame.columnconfigure(0, weight=1)

        # Campaign operations
        campaign_frame = ttk.Frame(ops_frame)
        campaign_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        campaign_frame.columnconfigure(0, weight=1)
        campaign_frame.columnconfigure(1, weight=1)

        self.btn_list_campaigns = ttk.Button(
            campaign_frame,
            text="List Campaigns",
            command=lambda: self.operation_handlers.run_listar_campanias(self.btn_list_campaigns)
        )
        self.btn_list_campaigns.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))

        self.btn_extract_subscribers = ttk.Button(
            campaign_frame,
            text="Extract Subscribers",
            command=lambda: self.operation_handlers.run_obtener_suscriptores(self.btn_extract_subscribers)
        )
        self.btn_extract_subscribers.grid(row=0, column=1, padx=(5, 0), sticky=(tk.W, tk.E))

        # List operations
        list_frame = ttk.Frame(ops_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.columnconfigure(1, weight=1)

        self.btn_create_list = ttk.Button(
            list_frame,
            text="Create List",
            command=lambda: self.operation_handlers.run_crear_lista(self.btn_create_list)
        )
        self.btn_create_list.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))

        self.btn_get_lists = ttk.Button(
            list_frame,
            text="Get All Lists",
            command=lambda: self.operation_handlers.run_obtener_listas(self.btn_get_lists)
        )
        self.btn_get_lists.grid(row=0, column=1, padx=(5, 0), sticky=(tk.W, tk.E))

        # Subscriber operations
        subscriber_frame = ttk.Frame(ops_frame)
        subscriber_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        subscriber_frame.columnconfigure(0, weight=1)

        self.btn_download_subscribers = ttk.Button(
            subscriber_frame,
            text="Download Subscribers",
            command=lambda: self.operation_handlers.run_descargar_suscriptores(self.btn_download_subscribers)
        )
        self.btn_download_subscribers.grid(row=0, column=0, sticky=(tk.W, tk.E))

    def _create_advanced_section(self, parent, row):
        """Create advanced operations section."""
        advanced_frame = ttk.LabelFrame(parent, text="Advanced Operations", padding="10")
        advanced_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        advanced_frame.columnconfigure(0, weight=1)

        # Advanced operations buttons
        self.btn_map_segments = ttk.Button(
            advanced_frame,
            text="Map Segments",
            command=self._run_map_segments
        )
        self.btn_map_segments.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        self.btn_delete_lists = ttk.Button(
            advanced_frame,
            text="Delete Lists",
            command=lambda: self.operation_handlers.run_eliminar_listas(self.btn_delete_lists),
            style="Danger.TButton"
        )
        self.btn_delete_lists.grid(row=1, column=0, sticky=(tk.W, tk.E))

    def _create_status_section(self, parent, row):
        """Create status and information section."""
        status_frame = ttk.LabelFrame(parent, text="Status", padding="10")
        status_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.S))
        status_frame.columnconfigure(0, weight=1)
        parent.rowconfigure(row, weight=1)

        # Status text area
        self.status_text = tk.Text(
            status_frame,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Scrollbar for status text
        status_scrollbar = ttk.Scrollbar(status_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        status_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.status_text.config(yscrollcommand=status_scrollbar.set)

        status_frame.rowconfigure(0, weight=1)

        # Clear status button
        ttk.Button(
            status_frame,
            text="Clear Status",
            command=self._clear_status
        ).grid(row=1, column=0, columnspan=2, pady=(10, 0))

    def _edit_config(self):
        """Open configuration editor."""
        try:
            show_config_window(self.root)
            self._update_config_status()
        except Exception as e:
            logger.error(f"❌ Failed to open configuration editor: {e}")
            notify("Error", f"Failed to open configuration editor: {e}", "error")

    def _validate_config(self):
        """Validate current configuration."""
        try:
            valid, message = self.config_validator.validate_configuration()
            if valid:
                notify("Configuration Valid", message, "info")
                self._update_config_status()
            else:
                notify("Configuration Error", message, "warning")
                self._update_config_status(valid=False, message=message)
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            notify("Validation Error", f"Configuration validation failed: {e}", "error")

    def _update_config_status(self, valid=None, message=None):
        """Update configuration status display."""
        if valid is None or message is None:
            try:
                valid, message = self.config_validator.validate_configuration()
            except Exception as e:
                valid = False
                message = f"Configuration check failed: {e}"

        status_text = f"Configuration: {'✅ Valid' if valid else '❌ Invalid'} - {message}"
        self.config_status_var.set(status_text)

    def _run_map_segments(self):
        """Run segment mapping operation."""
        logger.info("🚀 Starting segment mapping process")

        def operation(progress):
            progress.update_progress("Validating configuration...")

            # Validate configuration
            valid, message = self.config_validator.validate_configuration()
            if not valid:
                raise ValueError(f"Configuration validation failed: {message}")

            progress.update_progress("Validating segments file...")
            # Validate segments file
            valid_segments, message_segments, segments_count = self.config_validator.validate_segments_file()
            if not valid_segments:
                raise ValueError(f"Segments file validation failed: {message_segments}")

            progress.update_progress("Creating lists directory if needed...")
            # Ensure lists directory exists
            lists_dir = data_path("listas")
            os.makedirs(lists_dir, exist_ok=True)

            progress.update_progress("Loading segment mapping module...")
            import importlib
            import src.mapeo_segmentos as m
            importlib.reload(m)

            progress.update_progress("Processing segments...")
            result = m.mapear_segmentos_completo()

            if "error" in result:
                raise ValueError(f"Segment mapping error: {result['error']}")

            return result

        def on_complete(success: bool, error: Exception = None):
            if success:
                # Process successful result (would need to be passed from operation)
                notify("Segment Mapping", "Segment mapping completed successfully", "info")
            else:
                logger.error(f"❌ Error mapping segments: {error}")
                notify("Error", f"Error mapping segments: {error}", "error")

            self.btn_map_segments.config(state=tk.NORMAL)
            self.root.config(cursor="")

        self.btn_map_segments.config(state=tk.DISABLED)
        self.root.config(cursor="watch")

        threaded_op = ThreadedOperation(
            self.root,
            operation,
            "Mapping Segments",
            on_complete
        )
        threaded_op.start()

    def _clear_status(self):
        """Clear status text area."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)

    def _log_status(self, message: str):
        """Add message to status area."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)

    def run(self):
        """Start the application."""
        try:
            logger.info("🚀 Starting refactored Acumbamail Automation Tool")
            self._log_status("Application started with refactored architecture")
            self.root.mainloop()
        except Exception as e:
            logger.error(f"❌ Application startup failed: {e}")
            notify("Startup Error", f"Application startup failed: {e}", "error")


def main():
    """Main entry point for refactored application."""
    try:
        app = MainWindowRefactored()
        app.run()
    except Exception as e:
        print(f"Critical error starting application: {e}")


if __name__ == "__main__":
    main()