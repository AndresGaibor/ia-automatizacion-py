"""
Validador de selectores.

Prueba selectores contra una página real de Playwright.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from playwright.sync_api import Page

from src.shared.logging.logger import get_logger
from .scorer import get_scorer, SelectorScorer

logger = get_logger()


@dataclass
class ValidationResult:
    """Resultado de validar un selector."""
    selector: str
    matches: int
    es_valido: bool
    score: int
    nivel: str
    razones: list[str]
    sugerencias: list[str]
    timestamp: str


class SelectorValidator:
    """Valida selectores contra una página real."""

    def __init__(self):
        self.scorer: SelectorScorer = get_scorer()

    def validar_selector(
        self,
        selector: str,
        page: Page,
        timeout: int = 5000
    ) -> ValidationResult:
        """Valida un selector contra la página actual.

        Args:
            selector: Selector CSS o Playwright a probar
            page: Página de Playwright activa
            timeout: Tiempo máximo de espera en ms

        Returns:
            ValidationResult con el resultado del test
        """
        razones = []
        sugerencias = []
        score = 3
        nivel = "moderado"
        matches = 0
        es_valido = False

        try:
            locator = page.locator(selector)
            count = locator.count()
            matches = count

            if count > 0:
                es_valido = True

                frag_result = self.scorer.score(selector)
                score = frag_result.score
                nivel = frag_result.nivel
                razones = frag_result.razones
                sugerencias = frag_result.sugerencias

            else:
                razones.append(f"Selector no encuentra elementos en la página")
                sugerencias.append("Verifica que la página haya cargado completamente")

        except Exception as e:
            razones.append(f"Error ejecutando selector: {str(e)}")
            sugerencias.append("Verifica la sintaxis del selector")
            score = 5
            nivel = "muy frágil"

        return ValidationResult(
            selector=selector,
            matches=matches,
            es_valido=es_valido,
            score=score,
            nivel=nivel,
            razones=razones,
            sugerencias=sugerencias,
            timestamp=datetime.now().isoformat(),
        )

    def validar_entry(
        self,
        selector_principal: str,
        fallbacks: list[str],
        page: Page
    ) -> dict:
        """Valida un selector principal y sus fallbacks.

        Returns:
            Dict con resultados para principal y cada fallback
        """
        resultados = {}

        principal_result = self.validar_selector(selector_principal, page)
        resultados["principal"] = principal_result

        resultados["fallbacks"] = []
        for fb in fallbacks:
            fb_result = self.validar_selector(fb, page)
            resultados["fallbacks"].append(fb_result)

        return resultados

    def validar_todos_los_selectores(
        self,
        catalog,
        page: Page
    ) -> dict:
        """Valida todos los selectores de un catálogo contra la página.

        Returns:
            Dict con resultados por pantalla y selector
        """
        resultados = {}

        for pantalla_nombre, pantalla in catalog.get_todos().items():
            resultados[pantalla_nombre] = {}

            for selector_entry in pantalla.selectores:
                result = self.validar_entry(
                    selector_entry.selector_principal,
                    selector_entry.fallbacks,
                    page
                )
                resultados[pantalla_nombre][selector_entry.clave] = result

        return resultados

    def generar_informe_auditoria(self, catalog) -> dict:
        """Genera un informe de auditoría de fragilidad sin hacer validación en página.

        Returns:
            Dict con estadísticas y lista de selectores frágiles
        """
        informe = {
            "fecha": datetime.now().isoformat(),
            "total_selectores": 0,
            "muy_fragiles": [],
            "fragiles": [],
            "moderados": [],
            "robustos": [],
            "por_pantalla": {},
        }

        for pantalla_nombre, pantalla in catalog.get_todos().items():
            informe["por_pantalla"][pantalla_nombre] = {
                "total": 0,
                "muy_fragiles": 0,
                "fragiles": 0,
            }

            for selector_entry in pantalla.selectores:
                informe["total_selectores"] += 1
                informe["por_pantalla"][pantalla_nombre]["total"] += 1

                score = selector_entry.fragilidad
                info = {
                    "clave": selector_entry.clave,
                    "descripcion": selector_entry.descripcion,
                    "selector": selector_entry.selector_principal,
                    "fragilidad": score,
                    "estado": selector_entry.estado,
                    "nota": selector_entry.nota,
                }

                if score >= 5:
                    informe["muy_fragiles"].append(info)
                    informe["por_pantalla"][pantalla_nombre]["muy_fragiles"] += 1
                elif score >= 4:
                    informe["fragiles"].append(info)
                    informe["por_pantalla"][pantalla_nombre]["fragiles"] += 1
                elif score >= 3:
                    informe["moderados"].append(info)
                else:
                    informe["robustos"].append(info)

        return informe


_validator_instance: Optional[SelectorValidator] = None


def get_validator() -> SelectorValidator:
    """Obtiene instancia singleton del validador."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SelectorValidator()
    return _validator_instance