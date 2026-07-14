"""
Módulo de creación de listas de suscriptores con selección automática.

Submódulos:
- file_utils: Extracción de IDs, nombres y renombrado de archivos
- remote_ops: Verificación de listas y comparación de suscriptores
- sheet_validation: Validación de hojas Excel
- subscriber_ops: Campos personalizados y operaciones API
- list_creation: Lógica principal de creación de listas
- main: Puntos de entrada (main_automatico, main_lote)
"""

from .file_utils import (
    extraer_id_desde_nombre_archivo,
    tiene_formato_id_existente,
    obtener_nombre_lista_desde_archivo,
    renombrar_archivo_con_id,
)
from .remote_ops import (
    verificar_lista_existe_remota,
    obtener_suscriptores_remotos,
    comparar_suscriptores_local_vs_remoto,
)
from .sheet_validation import (
    seleccionar_archivo_excel,
    validar_diferencias_hojas,
)
from .subscriber_ops import (
    crear_campos_personalizados,
    crear_lista_via_api,
    verificar_y_mostrar_campos,
    agregar_suscriptores_via_api,
)
from .list_creation import (
    cargar_configuracion_lista,
    procesar_hoja_excel,
    crear_lista_automatica_interna,
    crear_lista_automatica,
)
from .main import (
    procesar_archivo_con_id_existente,
    main_automatico,
    main_lote,
)

__all__ = [
    'extraer_id_desde_nombre_archivo',
    'tiene_formato_id_existente',
    'obtener_nombre_lista_desde_archivo',
    'renombrar_archivo_con_id',
    'verificar_lista_existe_remota',
    'obtener_suscriptores_remotos',
    'comparar_suscriptores_local_vs_remoto',
    'seleccionar_archivo_excel',
    'validar_diferencias_hojas',
    'crear_campos_personalizados',
    'crear_lista_via_api',
    'verificar_y_mostrar_campos',
    'agregar_suscriptores_via_api',
    'cargar_configuracion_lista',
    'procesar_hoja_excel',
    'crear_lista_automatica_interna',
    'crear_lista_automatica',
    'procesar_archivo_con_id_existente',
    'main_automatico',
    'main_lote',
]
