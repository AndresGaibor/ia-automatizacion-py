"""
Ventana de progreso para operaciones largas.
Reemplaza las variables globales y funciones sueltas de app.py.
"""
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional


class ProgressWindow:
    """Ventana modal con barra de progreso y contador de tiempo."""

    def __init__(self, parent: tk.Tk, title: str, estimated_seconds: int = 60):
        self._window: Optional[tk.Toplevel] = None
        self._label: Optional[tk.Label] = None
        self._time_label: Optional[tk.Label] = None
        self._start_time: Optional[float] = None
        self._parent = parent
        self._title = title
        self._estimated = estimated_seconds

    def show(self):
        """Muestra la ventana de progreso (debe llamarse desde el hilo principal)."""
        if self._window and self._window.winfo_exists():
            return

        self._start_time = time.time()
        self._window = tk.Toplevel(self._parent)
        self._window.title(self._title)
        self._window.geometry("400x150")
        self._window.resizable(False, False)
        self._window.transient(self._parent)
        self._window.grab_set()

        main_frame = tk.Frame(self._window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._label = tk.Label(main_frame, text="Iniciando...", font=("Arial", 10))
        self._label.pack(pady=(0, 10))

        progress_bar = ttk.Progressbar(main_frame, mode="indeterminate")
        progress_bar.pack(fill=tk.X, pady=(0, 10))
        progress_bar.start(10)

        self._time_label = tk.Label(
            main_frame,
            text=f"Tiempo estimado: {self._estimated // 60}m {self._estimated % 60}s",
            font=("Arial", 9),
            fg="gray",
        )
        self._time_label.pack()

        self._update_timer()

    def update_message(self, message: str):
        """Actualiza el mensaje de estado (puede llamarse desde cualquier thread)."""
        if self._label and self._label.winfo_exists():
            self._label.config(text=message)

    def close(self):
        """Cierra la ventana de progreso."""
        if self._window and self._window.winfo_exists():
            self._window.destroy()
            self._window = None

    def _update_timer(self):
        """Actualiza el contador de tiempo transcurrido."""
        if self._window and self._window.winfo_exists() and self._start_time is not None:
            elapsed = int(time.time() - self._start_time)
            if self._time_label and self._time_label.winfo_exists():
                self._time_label.config(
                    text=f"Tiempo estimado: {self._estimated // 60}m {self._estimated % 60}s"
                    f" | Transcurrido: {elapsed // 60}m {elapsed % 60}s"
                )
            self._window.after(1000, self._update_timer)
