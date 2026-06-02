"""
SelectorEditorWindow - GUI para editar selectores de scraping.

Permite al usuario final:
- Ver selectores por pantalla
- Editar selector principal y fallbacks
- Probar selectores en la página activa
- Ver fragilidad y auditoría
- Exportar/importar cambios
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import threading

try:
    from ...infrastructure.scraping.selectors.catalog import get_catalog, SelectorCatalog
    from ...infrastructure.scraping.selectors.scorer import get_scorer
    from ...infrastructure.scraping.selectors.validator import get_validator
except ImportError:
    try:
        from src.infrastructure.scraping.selectors.catalog import get_catalog, SelectorCatalog
        from src.infrastructure.scraping.selectors.scorer import get_scorer
        from src.infrastructure.scraping.selectors.validator import get_validator
    except ImportError:
        pass

try:
    from ...shared.logging import get_logger
except ImportError:
    from src.shared.logging import get_logger

logger = get_logger()

FRAGILITY_COLORS = {
    1: "#d4edda",
    2: "#c3e6cb",
    3: "#fff3cd",
    4: "#ffeeba",
    5: "#f8d7da",
}

FRAGILITY_TEXT = {
    1: "muy robusto",
    2: "robusto",
    3: "moderado",
    4: "frágil",
    5: "muy frágil",
}


class SelectorEditorWindow:
    """Ventana para editar selectores."""

    def __init__(self, parent=None):
        self.parent = parent
        self.window = None
        self.catalog = None
        self.scorer = None
        self.validator = None
        self.current_pantalla = None
        self.current_selector = None
        self.page = None
        self.pantalla_buttons = {}

    def show(self):
        """Muestra la ventana del editor de selectores."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title("Editor de Selectores - Acumba Automation")
        self.window.geometry("1100x700")

        self.catalog = get_catalog()
        self.scorer = get_scorer()
        self.validator = get_validator()

        self._create_widgets()
        self._load_pantallas()

        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        """Crea los widgets de la interfaz."""
        main_paned = ttk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        main_paned.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_paned, width=200)
        main_paned.add(left_frame, weight=1)

        center_frame = ttk.Frame(main_paned)
        main_paned.add(center_frame, weight=3)

        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        self._create_left_panel(left_frame)
        self._create_center_panel(center_frame)
        self._create_right_panel(right_frame)

        self._create_bottom_bar()

    def _create_left_panel(self, parent):
        """Panel izquierdo con lista de pantallas."""
        ttk.Label(parent, text="Pantallas", font=("Arial", 12, "bold")).pack(pady=(0, 10))

        scroll_canvas = tk.Canvas(parent)
        scroll_bar = ttk.Scrollbar(parent, orient="vertical", command=scroll_canvas.yview)
        scroll_frame_inner = tk.Frame(scroll_canvas)

        scroll_frame_inner.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        )
        scroll_canvas.create_window((0, 0), window=scroll_frame_inner, anchor="nw")
        scroll_canvas.configure(yscrollcommand=scroll_bar.set)

        scroll_canvas.pack(side="left", fill="both", expand=True)
        scroll_bar.pack(side="right", fill="y")

        for pantalla in self.catalog.get_pantallas():
            btn = tk.Button(
                scroll_frame_inner,
                text=pantalla.capitalize(),
                font=("Arial", 11),
                width=15,
                command=lambda p=pantalla: self._select_pantalla(p)
            )
            btn.pack(pady=3, padx=5)
            self.pantalla_buttons[pantalla] = btn

        ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=15)

        ttk.Label(parent, text="Auditoría", font=("Arial", 10, "bold")).pack(pady=(0, 5))

        self.btn_auditoria = tk.Button(
            parent,
            text="Ver Fragilidad",
            font=("Arial", 10),
            command=self._show_auditoria
        )
        self.btn_auditoria.pack(pady=3, padx=5)

        self.btn_export = tk.Button(
            parent,
            text="Exportar YAML",
            font=("Arial", 10),
            command=self._export_yaml
        )
        self.btn_export.pack(pady=3, padx=5)

        self.btn_import = tk.Button(
            parent,
            text="Importar YAML",
            font=("Arial", 10),
            command=self._import_yaml
        )
        self.btn_import.pack(pady=3, padx=5)

    def _create_center_panel(self, parent):
        """Panel central con tabla de selectores."""
        ttk.Label(parent, text="Selectores", font=("Arial", 12, "bold")).pack(pady=(0, 10))

        columns = ("clave", "descripcion", "selector", "fragilidad", "estado")
        self.table = ttk.Treeview(parent, columns=columns, show="tree headings", height=20)

        self.table.heading("#0", text="#")
        self.table.column("#0", width=30)

        self.table.heading("clave", text="Clave")
        self.table.column("clave", width=120)

        self.table.heading("descripcion", text="Descripción")
        self.table.column("descripcion", width=180)

        self.table.heading("selector", text="Selector Principal")
        self.table.column("selector", width=200)

        self.table.heading("fragilidad", text="Fragilidad")
        self.table.column("fragilidad", width=80)

        self.table.heading("estado", text="Estado")
        self.table.column("estado", width=80)

        scroll_y = ttk.Scrollbar(parent, orient="vertical", command=self.table.yview)
        scroll_x = ttk.Scrollbar(parent, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.table.pack(fill="both", expand=True, side="left")
        scroll_y.pack(fill="y", side="right")
        scroll_x.pack(fill="x", side="bottom")

        self.table.bind("<<TreeviewSelect>>", self._on_select_row)

    def _create_right_panel(self, parent):
        """Panel derecho con detalle del selector."""
        ttk.Label(parent, text="Detalle del Selector", font=("Arial", 12, "bold")).pack(pady=(0, 10))

        self.detail_frame = ttk.LabelFrame(parent, text="Información", padding=10)
        self.detail_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.lbl_clave = ttk.Label(self.detail_frame, text="Clave:", font=("Arial", 10, "bold"))
        self.lbl_clave_val = ttk.Label(self.detail_frame, text="-")
        self.lbl_clave.grid(row=0, column=0, sticky="w", pady=2)
        self.lbl_clave_val.grid(row=0, column=1, sticky="w", pady=2, padx=(10, 0))

        self.lbl_desc = ttk.Label(self.detail_frame, text="Descripción:")
        self.lbl_desc_val = ttk.Label(self.detail_frame, text="-")
        self.lbl_desc.grid(row=1, column=0, sticky="w", pady=2)
        self.lbl_desc_val.grid(row=1, column=1, sticky="w", pady=2, padx=(10, 0))

        self.lbl_fragilidad = ttk.Label(self.detail_frame, text="Fragilidad:")
        self.lbl_fragilidad_val = ttk.Label(self.detail_frame, text="-")
        self.lbl_fragilidad.grid(row=2, column=0, sticky="w", pady=2)
        self.lbl_fragilidad_val.grid(row=2, column=1, sticky="w", pady=2, padx=(10, 0))

        self.lbl_estado = ttk.Label(self.detail_frame, text="Estado:")
        self.lbl_estado_val = ttk.Label(self.detail_frame, text="-")
        self.lbl_estado.grid(row=3, column=0, sticky="w", pady=2)
        self.lbl_estado_val.grid(row=3, column=1, sticky="w", pady=2, padx=(10, 0))

        selector_frame = ttk.LabelFrame(self.detail_frame, text="Selector Principal", padding=5)
        selector_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.selector_entry = ttk.Entry(selector_frame, width=40)
        self.selector_entry.pack(fill="x", padx=5, pady=5)

        fallbacks_frame = ttk.LabelFrame(self.detail_frame, text="Fallbacks (uno por línea)", padding=5)
        fallbacks_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.fallbacks_text = scrolledtext.ScrolledText(fallbacks_frame, height=4, width=40)
        self.fallbacks_text.pack(fill="x", padx=5, pady=5)

        nota_frame = ttk.LabelFrame(self.detail_frame, text="Nota", padding=5)
        nota_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.nota_text = scrolledtext.ScrolledText(nota_frame, height=3, width=40)
        self.nota_text.pack(fill="x", padx=5, pady=5)

        btn_frame = ttk.Frame(self.detail_frame)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(10, 0))

        self.btn_guardar = tk.Button(
            btn_frame,
            text="Guardar",
            font=("Arial", 10, "bold"),
            bg="#d4edda",
            command=self._guardar_selector
        )
        self.btn_guardar.pack(side="left", padx=(0, 5))

        self.btn_probar = tk.Button(
            btn_frame,
            text="Probar",
            font=("Arial", 10),
            command=self._probar_selector
        )
        self.btn_probar.pack(side="left", padx=(0, 5))

        self.btn_restaurar = tk.Button(
            btn_frame,
            text="Restaurar",
            font=("Arial", 10),
            command=self._restaurar_selector
        )
        self.btn_restaurar.pack(side="left")

        self.btn_capturar = tk.Button(
            btn_frame,
            text="Capturar",
            font=("Arial", 10),
            bg="#cce5ff",
            command=self._capturar_selector
        )
        self.btn_capturar.pack(side="left", padx=(5, 0))

    def _create_bottom_bar(self):
        """Barra inferior con info y tabs."""
        self.bottom_notebook = ttk.Notebook(self.window)
        self.bottom_notebook.pack(fill="both", expand=False, padx=10, pady=(0, 10))

        self.tab_raw = scrolledtext.ScrolledText(self.bottom_notebook, height=8)
        self.tab_raw.configure(font=("Courier", 9))
        self.bottom_notebook.add(self.tab_raw, text="Vista YAML (raw)")

        self.tab_test = scrolledtext.ScrolledText(self.bottom_notebook, height=8)
        self.tab_test.configure(font=("Courier", 9))
        self.bottom_notebook.add(self.tab_test, text="Resultado de prueba")

        self.status_label = ttk.Label(self.window, text="Listo", relief="sunken", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=(0, 5))

    def _load_pantallas(self):
        """Carga la lista de pantallas en el panel izquierdo."""
        for pantalla, btn in self.pantalla_buttons.items():
            count = len(self.catalog.get_pantalla(pantalla).selectores)
            btn.config(text=f"{pantalla.capitalize()} ({count})")

    def _select_pantalla(self, pantalla):
        """Muestra los selectores de una pantalla."""
        self.current_pantalla = pantalla

        for p, btn in self.pantalla_buttons.items():
            btn.config(relief="raised", bg="SystemButtonFace")

        self.pantalla_buttons[pantalla].config(relief="sunken", bg="#e0e0e0")

        for item in self.table.get_children():
            self.table.delete(item)

        pant_obj = self.catalog.get_pantalla(pantalla)
        if not pant_obj:
            return

        for i, sel in enumerate(pant_obj.selectores):
            frag_color = FRAGILITY_COLORS.get(sel.fragilidad, "#ffffff")
            self.table.insert(
                "",
                "end",
                text=str(i + 1),
                values=(
                    sel.clave,
                    sel.descripcion[:40] + "..." if len(sel.descripcion) > 40 else sel.descripcion,
                    sel.selector_principal[:35] + "..." if len(sel.selector_principal) > 35 else sel.selector_principal,
                    FRAGILITY_TEXT.get(sel.fragilidad, "??"),
                    sel.estado,
                ),
                tags=(f"frag_{sel.fragilidad}",)
            )

        self.table.tag_configure("frag_5", background=FRAGILITY_COLORS[5])
        self.table.tag_configure("frag_4", background=FRAGILITY_COLORS[4])
        self.table.tag_configure("frag_3", background=FRAGILITY_COLORS[3])
        self.table.tag_configure("frag_2", background=FRAGILITY_COLORS[2])
        self.table.tag_configure("frag_1", background=FRAGILITY_COLORS[1])

        self._update_raw_view()

    def _on_select_row(self, event):
        """Cuando el usuario selecciona una fila."""
        selection = self.table.selection()
        if not selection:
            return

        item = self.table.item(selection[0])
        idx = int(item["text"]) - 1

        pant_obj = self.catalog.get_pantalla(self.current_pantalla)
        if not pant_obj or idx >= len(pant_obj.selectores):
            return

        sel = pant_obj.selectores[idx]
        self.current_selector = sel

        self.lbl_clave_val.config(text=sel.clave)
        self.lbl_desc_val.config(text=sel.descripcion[:50] + "..." if len(sel.descripcion) > 50 else sel.descripcion)
        self.lbl_fragilidad_val.config(text=f"{sel.fragilidad}/5 - {FRAGILITY_TEXT.get(sel.fragilidad, '?')}")
        self.lbl_estado_val.config(text=sel.estado)

        self.selector_entry.delete(0, tk.END)
        self.selector_entry.insert(0, sel.selector_principal)

        self.fallbacks_text.delete("1.0", tk.END)
        self.fallbacks_text.insert("1.0", "\n".join(sel.fallbacks))

        self.nota_text.delete("1.0", tk.END)
        self.nota_text.insert("1.0", sel.nota)

    def _guardar_selector(self):
        """Guarda los cambios al selector."""
        if not self.current_selector or not self.current_pantalla:
            messagebox.showwarning("Aviso", "Selecciona un selector primero")
            return

        nuevo_selector = self.selector_entry.get().strip()
        if not nuevo_selector:
            messagebox.showerror("Error", "El selector no puede estar vacío")
            return

        self.current_selector.selector_principal = nuevo_selector
        self.current_selector.fallbacks = [
            f.strip() for f in self.fallbacks_text.get("1.0", tk.END).strip().split("\n") if f.strip()
        ]
        self.current_selector.nota = self.nota_text.get("1.0", tk.END).strip()

        score_result = self.scorer.score(nuevo_selector)
        self.current_selector.fragilidad = score_result.score

        if self.catalog.guardar_selector(self.current_pantalla, self.current_selector):
            self.status_label.config(text=f"✅ Guardado: {self.current_selector.clave}")
            self._select_pantalla(self.current_pantalla)
        else:
            messagebox.showerror("Error", "No se pudo guardar el selector")

    def _probar_selector(self):
        """Prueba el selector en la página activa."""
        if not self.current_selector:
            messagebox.showwarning("Aviso", "Selecciona un selector primero")
            return

        selector = self.selector_entry.get().strip()
        if not selector:
            messagebox.showerror("Error", "Selector vacío")
            return

        self.tab_test.delete("1.0", tk.END)
        self.tab_test.insert("1.0", f"Probando selector: {selector}\n")
        self.tab_test.insert(tk.END, f"Fragilidad: {FRAGILITY_TEXT.get(self.current_selector.fragilidad, '?')}\n")
        self.tab_test.insert(tk.END, "-" * 50 + "\n")

        score_result = self.scorer.score(selector)
        self.tab_test.insert(tk.END, f"Score: {score_result.score}/5\n")
        self.tab_test.insert(tk.END, f"Nivel: {score_result.nivel}\n\n")

        if score_result.razones:
            self.tab_test.insert(tk.END, "Razones:\n")
            for r in score_result.razones:
                self.tab_test.insert(tk.END, f"  • {r}\n")

        if score_result.sugerencias:
            self.tab_test.insert(tk.END, "\nSugerencias:\n")
            for s in score_result.sugerencias:
                self.tab_test.insert(tk.END, f"  • {s}\n")

        self.bottom_notebook.select(1)

    def _restaurar_selector(self):
        """Restaura los valores originales del selector."""
        if not self.current_selector:
            return

        self.selector_entry.delete(0, tk.END)
        self.selector_entry.insert(0, self.current_selector.selector_principal)

        self.fallbacks_text.delete("1.0", tk.END)
        self.fallbacks_text.insert("1.0", "\n".join(self.current_selector.fallbacks))

        self.nota_text.delete("1.0", tk.END)
        self.nota_text.insert("1.0", self.current_selector.nota)

        self.status_label.config(text=f"🔄 Restaurado: {self.current_selector.clave}")

    def _capturar_selector(self):
        """Abre diálogo para capturar selector manualmente."""
        win = tk.Toplevel(self.window)
        win.title("Capturar Selector")
        win.geometry("500x400")

        ttk.Label(win, text="Capturar nuevo selector", font=("Arial", 12, "bold")).pack(pady=(15, 10))
        ttk.Label(win, text="Ingresa el selector CSS o XPath que quieres capturar:", wraplength=450).pack()

        selector_frame = ttk.Frame(win, padding=10)
        selector_frame.pack(fill="x", padx=20, pady=10)

        ttk.Label(selector_frame, text="Selector:").pack(side="left")
        capture_entry = ttk.Entry(selector_frame, width=50)
        capture_entry.pack(side="left", padx=(10, 0), fill="x", expand=True)

        self.captured_suggestions = []

        result_text = scrolledtext.ScrolledText(win, height=12, font=("Courier", 9))
        result_text.pack(fill="both", expand=True, padx=20, pady=10)

        def analizar():
            selector = capture_entry.get().strip()
            if not selector:
                messagebox.showwarning("Aviso", "Ingresa un selector primero")
                return

            result_text.delete("1.0", tk.END)
            result_text.insert("1.0", f"Analizando: {selector}\n")
            result_text.insert(tk.END, "=" * 50 + "\n\n")

            score_result = self.scorer.score(selector)
            result_text.insert(tk.END, f"Fragilidad: {score_result.score}/5 ({score_result.nivel})\n\n")

            if score_result.razones:
                result_text.insert(tk.END, "Razones:\n")
                for r in score_result.razones:
                    result_text.insert(tk.END, f"  ⚠️ {r}\n")
                result_text.insert(tk.END, "\n")

            if score_result.sugerencias:
                result_text.insert(tk.END, "Sugerencias de mejora:\n")
                for s in score_result.sugerencias:
                    result_text.insert(tk.END, f"  💡 {s}\n")
                result_text.insert(tk.END, "\n")

            result_text.insert(tk.END, "Orden recomendado de selectores:\n")
            orden = [
                ("get_by_role + name", 1),
                ("id (#)", 2),
                ("data-testid", 1),
                ("href*", 2),
                ("aria-label", 2),
                ("get_by_text", 3),
                ("CSS con clase", 3),
                ("nth()", 5),
            ]
            for desc, score in orden:
                result_text.insert(tk.END, f"  {score}/5 {desc}\n")

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Analizar", command=analizar).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cerrar", command=win.destroy).pack(side="left", padx=5)

    def _update_raw_view(self):
        """Actualiza la vista YAML raw."""
        if not self.current_pantalla:
            return

        pant_obj = self.catalog.get_pantalla(self.current_pantalla)
        if not pant_obj:
            return

        import yaml

        data = {
            "pantalla": self.current_pantalla,
            "selectores": []
        }

        for sel in pant_obj.selectores:
            data["selectores"].append({
                "clave": sel.clave,
                "descripcion": sel.descripcion,
                "selector_principal": sel.selector_principal,
                "fallbacks": sel.fallbacks,
                "fragilidad": sel.fragilidad,
                "estado": sel.estado,
                "nota": sel.nota,
                "origen": sel.origen,
                "ultima_validacion": sel.ultima_validacion,
                "ejemplo_dom": sel.ejemplo_dom,
            })

        yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)

        self.tab_raw.delete("1.0", tk.END)
        self.tab_raw.insert("1.0", yaml_str)

    def _show_auditoria(self):
        """Muestra ventana con auditoría de fragilidad."""
        informe = self.validator.generar_informe_auditoria(self.catalog)

        win = tk.Toplevel(self.window)
        win.title("Auditoría de Fragilidad")
        win.geometry("800x500")

        text = scrolledtext.ScrolledText(win, font=("Courier", 10))
        text.pack(fill="both", expand=True, padx=10, pady=10)

        text.insert("1.0", "=" * 60 + "\n")
        text.insert(tk.END, "AUDITORÍA DE FRAGILIDAD DE SELECTORES\n")
        text.insert(tk.END, f"Fecha: {informe['fecha']}\n")
        text.insert(tk.END, "=" * 60 + "\n\n")

        text.insert(tk.END, f"Total selectores: {informe['total_selectores']}\n\n")

        text.insert(tk.END, "-" * 40 + "\n")
        text.insert(tk.END, f"MUY FRÁGILES (5/5): {len(informe['muy_fragiles'])}\n")
        text.insert(tk.END, "-" * 40 + "\n")
        for s in informe['muy_fragiles']:
            text.insert(tk.END, f"  ⚠️ {s['clave']}: {s['selector']}\n")
            text.insert(tk.END, f"     Nota: {s.get('nota', '-')}\n\n")

        text.insert(tk.END, "-" * 40 + "\n")
        text.insert(tk.END, f"FRÁGILES (4/5): {len(informe['fragiles'])}\n")
        text.insert(tk.END, "-" * 40 + "\n")
        for s in informe['fragiles']:
            text.insert(tk.END, f"  ⚡ {s['clave']}: {s['selector']}\n")
            text.insert(tk.END, f"     Nota: {s.get('nota', '-')}\n\n")

        text.insert(tk.END, "-" * 40 + "\n")
        text.insert(tk.END, f"POR PANTALLA:\n")
        text.insert(tk.END, "-" * 40 + "\n")
        for pant, stats in informe['por_pantalla'].items():
            text.insert(tk.END, f"  {pant}: {stats['total']} total, {stats['muy_fragiles']} muy frágiles, {stats['fragiles']} frágiles\n")

        text.config(state="disabled")

    def _export_yaml(self):
        """Exporta el catálogo completo a un archivo."""
        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML", "*.yaml"), ("Todos", "*")]
        )

        if not path:
            return

        try:
            import yaml

            todo = {}
            for pant_nombre, pant_obj in self.catalog.get_todos().items():
                todo[pant_nombre] = {
                    "pantalla": pant_nombre,
                    "selectores": []
                }
                for sel in pant_obj.selectores:
                    todo[pant_nombre]["selectores"].append({
                        "clave": sel.clave,
                        "descripcion": sel.descripcion,
                        "selector_principal": sel.selector_principal,
                        "fallbacks": sel.fallbacks,
                        "fragilidad": sel.fragilidad,
                        "estado": sel.estado,
                        "nota": sel.nota,
                        "origen": sel.origen,
                        "ultima_validacion": sel.ultima_validacion,
                        "ejemplo_dom": sel.ejemplo_dom,
                    })

            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(todo, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            messagebox.showinfo("Éxito", f"Catálogo exportado a:\n{path}")

        except Exception as e:
            messagebox.showerror("Error", f"Error exportando:\n{e}")

    def _import_yaml(self):
        """Importa un catálogo desde un archivo YAML."""
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            filetypes=[("YAML", "*.yaml"), ("Todos", "*")]
        )

        if not path:
            return

        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            for pant_nombre, pant_data in data.items():
                file_path = Path(self.catalog.selectors_dir) / f"{pant_nombre}.yaml"
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(pant_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            messagebox.showinfo("Éxito", "Catálogo importado. Reinicia la ventana para ver los cambios.")
            self.status_label.config(text="✅ Catálogo importado. Cierra y abre la ventana para ver cambios.")

        except Exception as e:
            messagebox.showerror("Error", f"Error importando:\n{e}")

    def _on_close(self):
        """Cuando se cierra la ventana."""
        if self.window:
            self.window.destroy()
            self.window = None


def show_selector_editor(parent=None):
    """Muestra la ventana del editor de selectores."""
    editor = SelectorEditorWindow(parent)
    editor.show()
    return editor