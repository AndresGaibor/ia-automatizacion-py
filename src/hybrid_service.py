# Wrapper delgado - código real en src/core/services/hybrid_service.py
from .core.services.hybrid_service import *

# Re-exportar clase pública
from .core.services.hybrid_service import HybridDataService

__all__ = ['HybridDataService']
