"""
Scorer de fragilidad de selectores.

Analiza un selector CSS/txt y devuelve un score 1-5 de fragilidad.
"""
import re
from dataclasses import dataclass

from src.shared.logging.logger import get_logger

logger = get_logger()


@dataclass
class FragilityScore:
    """Resultado del análisis de fragilidad."""
    score: int
    nivel: str
    razones: list[str]
    sugerencias: list[str]


class SelectorScorer:
    """Analiza fragilidad de un selector."""

    # Patrones que indican alta fragilidad
    MUY_FRAGIL_PATTERNS = [
        (r"nth-child\s*\(", "Usa nth-child() - muy frágil a cambios de estructura"),
        (r"nth-of-type\s*\(", "Usa nth-of-type() - muy frágil a cambios de estructura"),
        (r">\s*\w+\s+>\s*\w+\s+>\s*\w+", "Selector demasiado anidado - cualquier cambio de DOM rompe"),
        (r"^\w+\s+>\s*\w+$", "Selector simple con > directo - depende de posición"),
        (r"\[\d+\]", "Índice posicional en atributo - muy frágil"),
    ]

    FRAGIL_PATTERNS = [
        (r"ul\s+li", "UL + LI genérico - puede capturar muchos elementos no deseados"),
        (r"div\s+div", "Div anidado doble - frágil a cambios de estructura"),
        (r"span\s+span", "Span anidado doble - frágil a cambios de estructura"),
        (r"^\.\w+-\w+-\w+", "Clase CSS con múltiples guiones - típica de estilos, puede cambiar"),
        (r":nth-child\(\d+\)", "Índice posicional fijo - frágil"),
        (r"^\w+\.\w+", "Etiqueta con clase de estilo - puede cambiar con redesign"),
        (r"^\.\w+$", "Clase CSS genérica - puede cambiar con rediseño"),
    ]

    SEMI_STABLE_PATTERNS = [
        (r"\[id.*\]", "Selector con ID - relativamente estable"),
        (r"\[data-", "Selector con data-* - relativamente estable"),
        (r"\[aria-", "Selector aria-* - estable semánticamente"),
        (r"\[href\*=", "Selector href con patrón - estable si URLs son fijas"),
        (r"get_by_role", "Método get_by_role - semántico y robusto"),
        (r"get_by_label", "Método get_by_label - semántico y robusto"),
        (r"get_by_text", "Método get_by_text - semántico aunque depende de texto"),
        (r"id=", "Selector con id= - estable"),
    ]

    VERY_STABLE_PATTERNS = [
        (r"\[data-testid", "data-testid - el más estable"),
        (r"\[id=['\"]", "ID con valor exacto - muy estable"),
        (r"get_by_role.*name=", "get_by_role con name - muy estable"),
        (r"get_by_label.*name=", "get_by_label con name - muy estable"),
    ]

    def score(self, selector: str) -> FragilityScore:
        """Analiza un selector y devuelve su fragilidad."""
        razones = []
        sugerencias = []

        selector_lower = selector.lower().strip()

        for pattern, razon in self.MUY_FRAGIL_PATTERNS:
            if re.search(pattern, selector_lower):
                razones.append(razon)
                if "nth-child" in razon:
                    sugerencias.append("Considera usar get_by_role() o找一个 elemento con clase estable más cercana")
                elif "anidado" in razon:
                    sugerencias.append("Usa un ID o data-* más cercano al elemento objetivo")

        for pattern, razon in self.FRAGIL_PATTERNS:
            if re.search(pattern, selector_lower):
                razones.append(razon)
                if "ul" in razon or "li" in razon:
                    sugerencias.append("Usa un selector con href o id específico para filtrar")
                elif "nth-child" in razon:
                    sugerencias.append("Considera agregar un identificador único al elemento")

        for pattern, razon in self.SEMI_STABLE_PATTERNS:
            if re.search(pattern, selector_lower):
                razones.append(razon)

        for pattern, razon in self.VERY_STABLE_PATTERNS:
            if re.search(pattern, selector_lower):
                razones.append(razon)

        score = self._compute_score(razones, selector)

        nivel = self._get_nivel(score)

        return FragilityScore(
            score=score,
            nivel=nivel,
            razones=razones,
            sugerencias=sugerencias,
        )

    def _compute_score(self, razones: list[str], selector: str) -> int:
        """Calcula el score final basado en las razones encontradas."""
        if not razones:
            return 3

        tiene_muy_fragil = any("muy frágil" in r.lower() for r in razones)
        tiene_fragil = any("frágil" in r.lower() for r in razones)
        tiene_estable = any("estable" in r.lower() or "semántico" in r.lower() for r in razones)

        if tiene_muy_fragil and not tiene_estable:
            return 5
        if tiene_muy_fragil and tiene_estable:
            return 4

        if tiene_fragil and not tiene_estable:
            return 4
        if tiene_fragil and tiene_estable:
            return 3

        if tiene_estable and not tiene_fragil and not tiene_muy_fragil:
            return 2

        if selector.strip().startswith("//") or selector.strip().startswith("xpath"):
            return 4

        return 3

    def _get_nivel(self, score: int) -> str:
        """Convierte score numérico a nivel textual."""
        niveles = {
            1: "muy robusto",
            2: "robusto",
            3: "moderado",
            4: "frágil",
            5: "muy frágil",
        }
        return niveles.get(score, "desconocido")

    def get_mejor_selector(self, selector: str, page, context: str = "") -> list[dict]:
        """Sugiere mejores selectores alternativos para un elemento dado.

        Returns:
            Lista de diccionarios con {tipo, selector, score} ordenados por robustez.
        """
        sugerencias = []

        try:
            locator = page.locator(selector)
            count = locator.count()

            if count > 0:
                first = locator.first

                if hasattr(first, 'get_by_role') and context:
                    try:
                        role = first.get_attribute('role')
                        if role:
                            name = first.get_attribute('name') or first.inner_text().split('\n')[0][:30]
                            sugerencias.append({
                                "tipo": "get_by_role",
                                "selector": f"get_by_role(\"{role}\", name=\"{name}\")",
                                "score": 1,
                                "razon": "Usa rol semántico + nombre"
                            })
                    except Exception:
                        pass

                elem_id = first.get_attribute('id')
                if elem_id:
                    sugerencias.append({
                        "tipo": "id",
                        "selector": f"#{elem_id}",
                        "score": 2,
                        "razon": "ID único del elemento"
                    })

                data_testid = first.get_attribute('data-testid')
                if data_testid:
                    sugerencias.append({
                        "tipo": "data-testid",
                        "selector": f"[data-testid=\"{data_testid}\"]",
                        "score": 1,
                        "razon": "data-testid es el más estable"
                    })

                href = first.get_attribute('href')
                if href and '/report/campaign/' in href:
                    sugerencias.append({
                        "tipo": "href",
                        "selector": 'a[href*="/report/campaign/"]',
                        "score": 2,
                        "razon": "Usa patrón de URL estable"
                    })

                aria_label = first.get_attribute('aria-label')
                if aria_label:
                    sugerencias.append({
                        "tipo": "aria-label",
                        "selector": f"[aria-label=\"{aria_label}\"]",
                        "score": 2,
                        "razon": "aria-label es semántico y estable"
                    })

                text = first.inner_text().strip()
                if text and len(text) < 50:
                    sugerencias.append({
                        "tipo": "get_by_text",
                        "selector": f"get_by_text(\"{text[:30]}\")",
                        "score": 3,
                        "razon": "Texto visible - frágil si cambia el texto"
                    })

                class_list = []
                try:
                    class_attr = first.get_attribute('class')
                    if class_attr:
                        classes = class_attr.split()
                        for cls in classes:
                            if cls not in ['am-responsive-table-cell', 'font-color-darkblue-1']:
                                class_list.append(cls)
                except Exception:
                    pass

                if class_list:
                    selector_css = f".{'.'.join(class_list[:2])}"
                    score = self.score(selector_css).score
                    sugerencias.append({
                        "tipo": "css",
                        "selector": selector_css,
                        "score": score,
                        "razon": "Clases CSS - podría cambiar con redesign"
                    })

        except Exception as e:
            logger.error(f"Error generando sugerencias: {e}")

        sugerencias.sort(key=lambda x: x['score'])
        return sugerencias


_scorer_instance = None


def get_scorer() -> SelectorScorer:
    """Obtiene instancia singleton del scorer."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = SelectorScorer()
    return _scorer_instance