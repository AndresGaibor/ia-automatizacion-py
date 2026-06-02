"""Manejo mejorado de errores con jerarquías de excepciones personalizadas."""

from enum import Enum, auto
from typing import Optional, Dict, Any


class NivelSeveridad(Enum):
    """Niveles de severidad de errores estandarizados."""

    BAJO = auto()
    MEDIO = auto()
    ALTO = auto()
    CRITICO = auto()


class ErrorAcumbaMail(Exception):
    """Excepción base para automatización de Acumbamail."""

    def __init__(
        self,
        mensaje: str,
        severidad: NivelSeveridad = NivelSeveridad.MEDIO,
        contexto: Optional[Dict[str, Any]] = None,
        causa: Optional[Exception] = None,
    ):
        super().__init__(mensaje)
        self.severidad = severidad
        self.contexto = contexto or {}
        self.causa = causa

    def __str__(self):
        msg_base = super().__str__()
        if self.contexto:
            contexto_str = ", ".join(f"{k}={v}" for k, v in self.contexto.items())
            return f"{msg_base} (Contexto: {contexto_str})"
        return msg_base


class ErrorConfiguracion(ErrorAcumbaMail):
    """Lanzada cuando la configuración es inválida o falta."""

    def __init__(self, mensaje: str, contexto: Optional[Dict[str, Any]] = None):
        super().__init__(mensaje, severidad=NivelSeveridad.CRITICO, contexto=contexto)


class ErrorAutenticacion(ErrorAcumbaMail):
    """Lanzada cuando la autenticación falla."""

    def __init__(self, mensaje: str, contexto: Optional[Dict[str, Any]] = None):
        super().__init__(mensaje, severidad=NivelSeveridad.ALTO, contexto=contexto)


class ErrorAPI(ErrorAcumbaMail):
    """Lanzada para errores relacionados con la API."""

    def __init__(
        self,
        mensaje: str,
        codigo_estado: Optional[int] = None,
        endpoint: Optional[str] = None,
        contexto: Optional[Dict[str, Any]] = None,
    ):
        contexto_completo = contexto or {}
        if codigo_estado is not None:
            contexto_completo["status_code"] = codigo_estado
        if endpoint is not None:
            contexto_completo["endpoint"] = endpoint

        severidad = NivelSeveridad.ALTO if codigo_estado and codigo_estado >= 500 else NivelSeveridad.MEDIO
        super().__init__(mensaje, severidad=severidad, contexto=contexto_completo)


class ErrorAutomatizacionNavegador(ErrorAcumbaMail):
    """Lanzada para errores relacionados con automatización del navegador."""

    def __init__(
        self,
        mensaje: str,
        url_pagina: Optional[str] = None,
        selector: Optional[str] = None,
        contexto: Optional[Dict[str, Any]] = None,
    ):
        contexto_completo = contexto or {}
        if url_pagina:
            contexto_completo["page_url"] = url_pagina
        if selector:
            contexto_completo["selector"] = selector

        super().__init__(mensaje, severidad=NivelSeveridad.MEDIO, contexto=contexto_completo)


class ErrorProcesamientoDatos(ErrorAcumbaMail):
    """Lanzada para errores de procesamiento y validación de datos."""

    def __init__(
        self,
        mensaje: str,
        ruta_archivo: Optional[str] = None,
        numero_fila: Optional[int] = None,
        contexto: Optional[Dict[str, Any]] = None,
    ):
        contexto_completo = contexto or {}
        if ruta_archivo:
            contexto_completo["file_path"] = ruta_archivo
        if numero_fila is not None:
            contexto_completo["row_number"] = numero_fila

        super().__init__(mensaje, severidad=NivelSeveridad.MEDIO, contexto=contexto_completo)


class ErrorValidacion(ErrorAcumbaMail):
    """Lanzada cuando la validación de datos falla."""

    def __init__(
        self,
        mensaje: str,
        nombre_campo: Optional[str] = None,
        valor_campo: Optional[Any] = None,
        contexto: Optional[Dict[str, Any]] = None,
    ):
        contexto_completo = contexto or {}
        if nombre_campo:
            contexto_completo["field_name"] = nombre_campo
        if valor_campo is not None:
            contexto_completo["field_value"] = valor_campo

        super().__init__(mensaje, severidad=NivelSeveridad.BAJO, contexto=contexto_completo)


ErrorNavegador = ErrorAutomatizacionNavegador
