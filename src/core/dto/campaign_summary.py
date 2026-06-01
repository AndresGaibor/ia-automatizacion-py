from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CampaignSummary:
    """One row from the campaign report page.

    Replaces the old ``list[str]`` output from ``extraer_datos_campania_de_listitem``.

    Fields match the current Excel column order exactly (indices 0-7):
        buscar:        Empty placeholder for UI marking (currently always "")
        nombre:        Campaign name from ``a[href*="/report/campaign/"]``
        id_campania:   Numeric ID extracted from URL regex ``/campaign/(\\d+)``
        fecha:         Date string in DD/MM/YY format
        total_enviado: Total sent count (dots removed, string preserved for Excel)
        abierto:       Opened count (dots removed, string preserved for Excel)
        no_abierto:    Calculated as ``total_enviado - abierto``, fallback "0"
        url_correo:    Tracked email URL (empty until enrichment phase)
    """

    buscar: str = ""
    nombre: str = ""
    id_campania: str = ""
    fecha: str = ""
    total_enviado: str = "0"
    abierto: str = "0"
    no_abierto: str = "0"
    url_correo: str = ""

    @classmethod
    def from_raw_parts(
        cls,
        nombre: str,
        id_campania: str,
        fecha: str,
        total_enviado: str,
        abierto: str,
    ) -> "CampaignSummary":
        """Build from scraped parts, computing ``no_abierto``."""
        no_abierto = _safe_diff(total_enviado, abierto)
        return cls(
            buscar="",
            nombre=nombre,
            id_campania=id_campania,
            fecha=fecha,
            total_enviado=total_enviado,
            abierto=abierto,
            no_abierto=no_abierto,
        )

    def with_url(self, url: str) -> "CampaignSummary":
        """Return a copy with the URL enriched."""
        return CampaignSummary(
            buscar=self.buscar,
            nombre=self.nombre,
            id_campania=self.id_campania,
            fecha=self.fecha,
            total_enviado=self.total_enviado,
            abierto=self.abierto,
            no_abierto=self.no_abierto,
            url_correo=url,
        )

    def to_excel_row(self) -> list[str]:
        """Convert to a flat list for Excel output (current column order)."""
        return [
            self.buscar,
            self.nombre,
            self.id_campania,
            self.fecha,
            self.total_enviado,
            self.abierto,
            self.no_abierto,
            self.url_correo,
        ]


def _safe_diff(a: str, b: str) -> str:
    """``int(a) - int(b)``, returning ``"0"`` on parse error. Matches original runtime."""
    try:
        result = int(a.replace(".", "")) - int(b.replace(".", ""))
        return str(result)
    except (ValueError, TypeError):
        return "0"
