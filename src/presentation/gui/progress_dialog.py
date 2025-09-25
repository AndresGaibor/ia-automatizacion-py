"""Progress dialog utilities for GUI operations."""
import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Optional, Callable

from ...shared.logging import get_logger

logger = get_logger()


class ProgressDialog:
    """Enhanced progress dialog for long-running operations."""

    def __init__(self, parent: tk.Tk, title: str = "Processing..."):
        self.parent = parent
        self.window: Optional[tk.Toplevel] = None
        self.progress_var: Optional[tk.StringVar] = None
        self.progress_label: Optional[tk.Label] = None
        self.time_label: Optional[tk.Label] = None
        self.start_time: Optional[float] = None
        self.title = title
        self._is_closed = False

    def show(self) -> None:
        """Show the progress dialog."""
        if self.window is not None:
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title(self.title)
        self.window.geometry("400x150")
        self.window.resizable(False, False)

        # Center the window
        self.window.transient(self.parent)
        self.window.grab_set()

        # Configure grid
        self.window.columnconfigure(0, weight=1)

        # Progress bar
        progress_bar = ttk.Progressbar(
            self.window,
            mode='indeterminate',
            length=350
        )
        progress_bar.grid(row=0, column=0, pady=20, padx=25, sticky="ew")
        progress_bar.start()

        # Progress label
        self.progress_var = tk.StringVar()
        self.progress_var.set("Initializing...")
        self.progress_label = tk.Label(
            self.window,
            textvariable=self.progress_var,
            wraplength=350
        )
        self.progress_label.grid(row=1, column=0, pady=5, padx=25)

        # Time label
        self.time_label = tk.Label(self.window, text="Time elapsed: 0s")
        self.time_label.grid(row=2, column=0, pady=5, padx=25)

        # Start time tracking
        self.start_time = time.time()
        self._update_time()

        logger.info("📊 Progress dialog shown", title=self.title)

    def update_progress(self, message: str) -> None:
        """Update the progress message."""
        if self.progress_var and not self._is_closed:
            def update():
                if self.progress_var:
                    self.progress_var.set(message)

            if self.parent:
                self.parent.after(0, update)
            logger.debug("📊 Progress updated", message=message)

    def _update_time(self) -> None:
        """Update the elapsed time display."""
        if self.time_label and self.start_time and not self._is_closed:
            def update():
                if self.time_label and self.start_time:
                    elapsed = int(time.time() - self.start_time)
                    minutes, seconds = divmod(elapsed, 60)
                    time_str = f"Time elapsed: {minutes}m {seconds}s" if minutes > 0 else f"Time elapsed: {seconds}s"
                    self.time_label.config(text=time_str)

            if self.parent:
                self.parent.after(0, update)
                # Schedule next update
                self.parent.after(1000, self._update_time)

    def close(self) -> None:
        """Close the progress dialog."""
        if self.window and not self._is_closed:
            self._is_closed = True
            def close_window():
                if self.window:
                    self.window.grab_release()
                    self.window.destroy()
                    self.window = None
                    self.progress_var = None
                    self.progress_label = None
                    self.time_label = None
                    self.start_time = None

            if self.parent:
                self.parent.after(0, close_window)
            logger.info("📊 Progress dialog closed", title=self.title)

    def __enter__(self) -> 'ProgressDialog':
        """Context manager entry."""
        self.show()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


class ThreadedOperation:
    """Helper class for running operations in background threads with progress tracking."""

    def __init__(
        self,
        parent: tk.Tk,
        operation: Callable[['ProgressDialog'], None],
        title: str = "Processing...",
        on_complete: Optional[Callable[[bool, Optional[Exception]], None]] = None
    ):
        self.parent = parent
        self.operation = operation
        self.title = title
        self.on_complete = on_complete
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the threaded operation."""
        if self._thread and self._thread.is_alive():
            logger.warning("⚠️ Operation already running")
            return

        logger.info("🚀 Starting threaded operation", title=self.title)
        self._thread = threading.Thread(target=self._run_operation, daemon=True)
        self._thread.start()

    def _run_operation(self) -> None:
        """Run the operation in a background thread."""
        success = False
        error = None

        try:
            with ProgressDialog(self.parent, self.title) as progress:
                self.operation(progress)
            success = True
            logger.success("✅ Threaded operation completed successfully", title=self.title)

        except Exception as e:
            error = e
            logger.error(f"❌ Threaded operation failed: {e}", title=self.title, error=str(e))

        # Notify completion on main thread
        if self.on_complete:
            def notify_complete():
                self.on_complete(success, error)

            if self.parent:
                self.parent.after(0, notify_complete)


# Global variables for backward compatibility with existing code
progress_window = None
progress_var = None
progress_label = None
time_label = None
start_time = None


def show_progress(root: tk.Tk, title: str = "Processing...") -> ProgressDialog:
    """Show a progress dialog (backward compatibility function)."""
    global progress_window, progress_var, progress_label, time_label, start_time

    if progress_window:
        return progress_window

    progress_dialog = ProgressDialog(root, title)
    progress_dialog.show()

    # Set global variables for backward compatibility
    progress_window = progress_dialog.window
    progress_var = progress_dialog.progress_var
    progress_label = progress_dialog.progress_label
    time_label = progress_dialog.time_label
    start_time = progress_dialog.start_time

    return progress_dialog


def update_progress(message: str) -> None:
    """Update progress message (backward compatibility function)."""
    global progress_var
    if progress_var:
        progress_var.set(message)


def close_progress(root: tk.Tk) -> None:
    """Close progress dialog (backward compatibility function)."""
    global progress_window, progress_var, progress_label, time_label, start_time

    if progress_window:
        progress_window.grab_release()
        progress_window.destroy()

    # Reset global variables
    progress_window = None
    progress_var = None
    progress_label = None
    time_label = None
    start_time = None