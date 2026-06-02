"""Excepciones personalizadas para el sistema de automatización Acumbamail."""

from .exceptions import (
    ErrorAcumbaMail,
    ErrorConfiguracion,
    ErrorAutenticacion,
    ErrorAPI,
    ErrorAutomatizacionNavegador,
    ErrorNavegador,
    ErrorProcesamientoDatos,
    ErrorValidacion,
    NivelSeveridad,
)

DataProcessingError = ErrorProcesamientoDatos

__all__ = [
    "ErrorAcumbaMail",
    "ErrorConfiguracion",
    "ErrorAutenticacion",
    "ErrorAPI",
    "ErrorAutomatizacionNavegador",
    "ErrorNavegador",
    "ErrorProcesamientoDatos",
    "ErrorValidacion",
    "NivelSeveridad",
    "DataProcessingError",
]
