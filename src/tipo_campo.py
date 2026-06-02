"""
Utilidades para tipos de campos de Acumbamail.

MIGRADO: El código principal está en src.infrastructure.scraping.utils.field_types.
Este archivo existe solo para compatibilidad hacia atrás.
"""
from src.infrastructure.scraping.utils.field_types import (
    field_type_label,
    VALUE_TO_LABEL,
    NAME_TO_LABEL,
)

__all__ = ["field_type_label", "VALUE_TO_LABEL", "NAME_TO_LABEL"]