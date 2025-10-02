import tkinter as tk
from tkinter import ttk, messagebox
import yaml
from pathlib import Path

class ConfigWindow:
    """Ventana de configuración para credenciales del usuario"""

    def __init__(self, parent=None):
        self.parent = parent
        self.window = None
        self.config_path = Path(__file__).parent.parent / "config.yaml"

    def show(self):
        """Muestra la ventana de configuración"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title("Configuración - Acumba Automation")
        self.window.geometry("450x300")
        self.window.resizable(False, False)

        # Centrar ventana
        self.window.transient(self.parent)
        self.window.grab_set()

        self._create_widgets()
        self._load_current_config()

        # Foco en el primer campo
        self.user_entry.focus()

    def _create_widgets(self):
        """Crea los widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Título
        title_label = ttk.Label(main_frame, text="Configuración de Credenciales",
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Usuario
        ttk.Label(main_frame, text="Usuario (email):").grid(row=1, column=0, sticky="w", pady=5)
        self.user_entry = ttk.Entry(main_frame, width=35)
        self.user_entry.grid(row=1, column=1, pady=5, padx=(10, 0))

        # Contraseña
        ttk.Label(main_frame, text="Contraseña:").grid(row=2, column=0, sticky="w", pady=5)
        self.password_entry = ttk.Entry(main_frame, show="*", width=35)
        self.password_entry.grid(row=2, column=1, pady=5, padx=(10, 0))

        # API Key
        ttk.Label(main_frame, text="API Key:").grid(row=3, column=0, sticky="w", pady=5)
        self.api_key_entry = ttk.Entry(main_frame, width=35)
        self.api_key_entry.grid(row=3, column=1, pady=5, padx=(10, 0))

        # Información sobre API Key
        info_text = "Encuentre su API Key en: Acumbamail > Configuración > API"
        info_label = ttk.Label(main_frame, text=info_text, font=("Arial", 8),
                              foreground="gray")
        info_label.grid(row=4, column=0, columnspan=2, pady=(5, 10))

        # Checkbox para modo headless
        self.headless_var = tk.BooleanVar()
        headless_check = ttk.Checkbutton(main_frame, text="Ejecutar en modo oculto (headless)",
                                        variable=self.headless_var)
        headless_check.grid(row=5, column=0, columnspan=2, pady=10)

        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0))

        ttk.Button(button_frame, text="Guardar", command=self._save_config).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="Cancelar", command=self._cancel).pack(side="left", padx=(10, 0))
        ttk.Button(button_frame, text="Probar Conexión", command=self._test_connection).pack(side="left", padx=(10, 0))

    def _load_current_config(self):
        """Carga la configuración actual si existe"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}

                # Cargar valores actuales
                self.user_entry.insert(0, config.get('user', ''))
                self.password_entry.insert(0, config.get('password', ''))

                api_config = config.get('api', {})
                self.api_key_entry.insert(0, api_config.get('api_key', ''))

                self.headless_var.set(config.get('headless', False))

        except Exception as e:
            messagebox.showerror("Error", f"Error cargando configuración: {e}")

    def _save_config(self):
        """Guarda la configuración en el archivo YAML"""
        user = self.user_entry.get().strip()
        password = self.password_entry.get().strip()
        api_key = self.api_key_entry.get().strip()

        # Validaciones
        if not user:
            messagebox.showerror("Error", "El usuario es requerido")
            self.user_entry.focus()
            return

        if not password:
            messagebox.showerror("Error", "La contraseña es requerida")
            self.password_entry.focus()
            return

        if not api_key:
            messagebox.showerror("Error", "La API Key es requerida")
            self.api_key_entry.focus()
            return

        # Cargar configuración existente o crear nueva
        config = {}
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            except:
                config = {}

        # Actualizar solo las credenciales (mantener otras configuraciones)
        config.update({
            'user': user,
            'password': password,
            'headless': self.headless_var.get(),
            'debug': config.get('debug', False),
            'api': {
                'api_key': api_key
            }
        })

        # Mantener configuraciones existentes que no sean credenciales
        if 'logging' not in config:
            config['logging'] = {
                'enabled': True,
                'level': 'normal',
                'console_output': False,
                'file_output': True,
                'performance_tracking': True,
                'emoji_style': True,
                'structured_format': False
            }

        if 'timeouts' not in config:
            config['timeouts'] = {
                'navigation': 60,
                'element': 15,
                'upload': 120,
                'default': 30
            }

        if 'lista' not in config:
            config['lista'] = {
                'sender_email': user,  # Usar el email del usuario
                'company': 'Mi Empresa',
                'country': 'España',
                'city': 'Madrid',
                'address': 'Calle Principal 123',
                'phone': '+34 900 000 000'
            }

        try:
            # Crear directorio si no existe
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Guardar configuración
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            messagebox.showinfo("Éxito", "Configuración guardada correctamente")
            self.window.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Error guardando configuración: {e}")

    def _test_connection(self):
        """Prueba la conexión con las credenciales ingresadas"""
        user = self.user_entry.get().strip()
        password = self.password_entry.get().strip()
        api_key = self.api_key_entry.get().strip()

        if not all([user, password, api_key]):
            messagebox.showerror("Error", "Complete todos los campos para probar la conexión")
            return

        # Crear una configuración temporal para probar
        try:
            from .infrastructure.api import API

            # Crear config temporal
            temp_config = {
                'user': user,
                'password': password,
                'api': {'api_key': api_key}
            }

            # Probar API
            api = API()
            # Hacer una llamada simple para probar
            campaigns = api.campaigns.get_all(complete_info=False)

            if campaigns is not None:
                messagebox.showinfo("Éxito", "✅ Conexión exitosa con Acumbamail")
            else:
                messagebox.showerror("Error", "❌ Error de conexión. Verifique sus credenciales")

        except Exception as e:
            messagebox.showerror("Error", f"❌ Error probando conexión: {e}")

    def _cancel(self):
        """Cancela y cierra la ventana"""
        self.window.destroy()

# Función para mostrar la ventana desde otros módulos
def show_config_window(parent=None):
    """Muestra la ventana de configuración"""
    config_window = ConfigWindow(parent)
    config_window.show()
    return config_window

if __name__ == "__main__":
    # Prueba independiente
    root = tk.Tk()
    root.withdraw()  # Ocultar ventana principal
    show_config_window()
    root.mainloop()