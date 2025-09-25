"""Shared utility functions."""

# Import from legacy utils module for backward compatibility
try:
    from .legacy_utils import (
        project_root,
        data_path,
        storage_state_path,
        load_config,
        notify,
        cargar_terminos_busqueda,
        cargar_campanias_a_buscar,
        cargar_id_campanias_a_buscar
    )
except ImportError:
    try:
        from ...utils import (
            project_root,
            data_path,
            storage_state_path,
            load_config,
            notify,
            cargar_terminos_busqueda,
            cargar_campanias_a_buscar,
            cargar_id_campanias_a_buscar
        )
    except ImportError:
        from src.utils import (
            project_root,
            data_path,
            storage_state_path,
            load_config,
            notify,
            cargar_terminos_busqueda,
            cargar_campanias_a_buscar,
            cargar_id_campanias_a_buscar
        )

__all__ = [
    'project_root',
    'data_path',
    'storage_state_path',
    'load_config',
    'notify',
    'cargar_terminos_busqueda',
    'cargar_campanias_a_buscar',
    'cargar_id_campanias_a_buscar'
]