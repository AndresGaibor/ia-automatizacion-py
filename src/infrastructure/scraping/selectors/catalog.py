"""
Catálogo de selectores para scraping.

Carga selectores desde archivos YAML y proporciona acceso centralizado.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml

from src.shared.logging.logger import get_logger

logger = get_logger()

SELECTORS_DIR = Path(__file__).parent.parent.parent.parent.parent / "selectors"


@dataclass
class SelectorEntry:
    """Entrada individual de un selector."""
    clave: str
    descripcion: str
    selector_principal: str
    fallbacks: list[str] = field(default_factory=list)
    fragilidad: int = 3
    estado: str = "no_validado"
    nota: str = ""
    origen: str = "manual"
    ultima_validacion: Optional[str] = None
    ejemplo_dom: str = ""

    def tiene_fallbacks(self) -> bool:
        return len(self.fallbacks) > 0

    def es_fragil(self) -> bool:
        return self.fragilidad >= 4

    def es_muy_fragil(self) -> bool:
        return self.fragilidad >= 5


@dataclass
class PantallaSelectores:
    """Conjunto de selectores para una pantalla específica."""
    pantalla: str
    selectores: list[SelectorEntry]


class SelectorCatalog:
    """Cargador y acceso al catálogo de selectores."""

    def __init__(self, selectors_dir: Path = SELECTORS_DIR):
        self.selectors_dir = selectors_dir
        self._catalog: dict[str, PantallaSelectores] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Carga todos los archivos YAML del directorio."""
        if not self.selectors_dir.exists():
            logger.warning(f"Directorio de selectores no existe: {self.selectors_dir}")
            return

        for yaml_file in self.selectors_dir.glob("*.yaml"):
            try:
                self._load_file(yaml_file)
            except Exception as e:
                logger.error(f"Error cargando {yaml_file}: {e}")

    def _load_file(self, path: Path) -> None:
        """Carga un archivo YAML individual."""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        pantalla = data.get("pantalla", path.stem)
        entries = []

        for sel in data.get("selectores", []):
            entry = SelectorEntry(
                clave=sel.get("clave", ""),
                descripcion=sel.get("descripcion", ""),
                selector_principal=sel.get("selector_principal", ""),
                fallbacks=sel.get("fallbacks", []),
                fragilidad=sel.get("fragilidad", 3),
                estado=sel.get("estado", "no_validado"),
                nota=sel.get("nota", ""),
                origen=sel.get("origen", "manual"),
                ultima_validacion=sel.get("ultima_validacion"),
                ejemplo_dom=sel.get("ejemplo_dom", ""),
            )
            entries.append(entry)

        self._catalog[pantalla] = PantallaSelectores(pantalla=pantalla, selectores=entries)
        logger.info(f"✅ Cargados {len(entries)} selectores para '{pantalla}'")

    def get_pantalla(self, nombre: str) -> Optional[PantallaSelectores]:
        """Obtiene selectores de una pantalla específica."""
        return self._catalog.get(nombre)

    def get_selector(self, pantalla: str, clave: str) -> Optional[SelectorEntry]:
        """Obtiene un selector específico por pantalla y clave."""
        pant = self.get_pantalla(pantalla)
        if not pant:
            return None
        for sel in pant.selectores:
            if sel.clave == clave:
                return sel
        return None

    def get_todos(self) -> dict[str, PantallaSelectores]:
        """Retorna todo el catálogo."""
        return self._catalog

    def get_pantallas(self) -> list[str]:
        """Lista de pantallas disponibles."""
        return list(self._catalog.keys())

    def get_selectores_fragiles(self) -> list[SelectorEntry]:
        """Retorna todos los selectores con fragilidad >= 4."""
        fragiles = []
        for pant in self._catalog.values():
            for sel in pant.selectores:
                if sel.es_fragil():
                    fragiles.append(sel)
        return fragiles

    def get_selectores_muy_fragiles(self) -> list[SelectorEntry]:
        """Retorna todos los selectores con fragilidad >= 5."""
        muy_fragiles = []
        for pant in self._catalog.values():
            for sel in pant.selectores:
                if sel.es_muy_fragil():
                    muy_fragiles.append(sel)
        return muy_fragiles

    def get_estadisticas(self) -> dict:
        """Retorna estadísticas del catálogo."""
        total = 0
        por_estado = {}
        por_fragilidad = {}

        for pant in self._catalog.values():
            for sel in pant.selectores:
                total += 1
                por_estado[sel.estado] = por_estado.get(sel.estado, 0) + 1
                frag_key = f"fragilidad_{sel.fragilidad}"
                por_fragilidad[frag_key] = por_fragilidad.get(frag_key, 0) + 1

        return {
            "total": total,
            "pantallas": len(self._catalog),
            "por_estado": por_estado,
            "por_fragilidad": por_fragilidad,
            "fragiles": len(self.get_selectores_fragiles()),
            "muy_fragiles": len(self.get_selectores_muy_fragiles()),
        }

    def guardar_selector(self, pantalla: str, entry: SelectorEntry) -> bool:
        """Guarda cambios a un selector en el archivo YAML."""
        pant_obj = self.get_pantalla(pantalla)
        if not pant_obj:
            logger.error(f"Pantalla '{pantalla}' no encontrada")
            return False

        for i, sel in enumerate(pant_obj.selectores):
            if sel.clave == entry.clave:
                pant_obj.selectores[i] = entry
                return self._save_pantalla(pantalla)
        return False

    def _save_pantalla(self, pantalla: str) -> bool:
        """Guarda una pantalla completa al archivo YAML."""
        pant_obj = self.get_pantalla(pantalla)
        if not pant_obj:
            return False

        data = {
            "pantalla": pantalla,
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

        file_path = self.selectors_dir / f"{pantalla}.yaml"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.info(f"✅ Guardado: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error guardando {file_path}: {e}")
            return False


_catalog_instance: Optional[SelectorCatalog] = None


def get_catalog() -> SelectorCatalog:
    """Obtiene instancia singleton del catálogo."""
    global _catalog_instance
    if _catalog_instance is None:
        _catalog_instance = SelectorCatalog()
    return _catalog_instance