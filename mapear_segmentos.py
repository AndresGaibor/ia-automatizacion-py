#!/usr/bin/env python3
"""
Script CLI para mapear segmentos desde Excel a listas de Acumbamail.

Uso:
    python mapear_segmentos.py

El script:
1. Lee el archivo data/Segmentos.xlsx
2. Para cada lista encontrada:
   - Busca la lista en Acumbamail por nombre
   - Crea campos necesarios (Segmentos, SEDE, ORGANO, etc.) si no existen
   - Procesa el archivo local data/listas/{nombre_lista}.xlsx
   - Aplica condiciones de segmentación (lógica AND)
   - Elimina y re-sube usuarios que cambiaron de segmento
   - Guarda cambios localmente y en Acumbamail
"""

import sys
import os
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.mapeo_segmentos import mapear_segmentos_completo, main as mapeo_main
from src.logger import get_logger

def main():
    """Función principal del CLI"""
    logger = get_logger()

    print("🚀 Iniciando mapeo de segmentos de Excel a Acumbamail")
    print("=" * 60)

    try:
        # Ejecutar el mapeo completo
        resultado = mapear_segmentos_completo()

        if "error" in resultado:
            print(f"\n❌ Error: {resultado['error']}")
            logger.error(f"Error en mapeo CLI: {resultado['error']}")
            return False

        # Mostrar resumen final
        print("\n" + "=" * 60)
        print("📊 RESUMEN FINAL DEL MAPEO")
        print("=" * 60)

        print(f"📋 Total de listas procesadas: {resultado['total_listas']}")
        print(f"✅ Listas exitosas: {len(resultado['listas_procesadas'])}")
        print(f"❌ Listas fallidas: {len(resultado['listas_fallidas'])}")

        if resultado['listas_procesadas']:
            print(f"\n🎉 Listas procesadas exitosamente:")
            for lista in resultado['listas_procesadas']:
                print(f"   • {lista}")

        if resultado['listas_fallidas']:
            print(f"\n⚠️  Listas que fallaron:")
            for lista in resultado['listas_fallidas']:
                print(f"   • {lista}")

        print(f"\n📁 Campos de segmentación utilizados:")
        for header in resultado.get('headers', []):
            print(f"   • {header}")

        # Resumen de archivos generados
        print(f"\n📄 Archivos generados en data/listas/:")
        listas_dir = Path("data/listas")
        if listas_dir.exists():
            for archivo in sorted(listas_dir.glob("*.xlsx")):
                print(f"   • {archivo.name}")

        print("\n" + "=" * 60)

        if resultado['listas_procesadas']:
            print("🎉 ¡Mapeo completado exitosamente!")
            logger.info("Mapeo CLI completado exitosamente")
            return True
        else:
            print("⚠️  No se procesaron listas correctamente")
            logger.warning("Mapeo CLI sin listas procesadas")
            return False

    except KeyboardInterrupt:
        print("\n\n⏹️  Proceso interrumpido por el usuario")
        logger.info("Mapeo CLI interrumpido por usuario")
        return False

    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        logger.error(f"Error inesperado en mapeo CLI: {e}")
        return False

def mostrar_ayuda():
    """Muestra información de ayuda"""
    print("""
🔧 MAPEO DE SEGMENTOS - Ayuda

DESCRIPCIÓN:
    Este script procesa segmentos desde Excel y los aplica a listas de Acumbamail.

ARCHIVOS REQUERIDOS:
    • data/Segmentos.xlsx - Definiciones de segmentos por lista
    • data/listas/{nombre_lista}.xlsx - Datos de usuarios por lista

NOTA: Ya NO se usa Lista_envio.xlsx (obsoleto)

PROCESO:
    1. Lee definiciones de segmentos desde Segmentos.xlsx
    2. Para cada lista:
       - Busca la lista en Acumbamail por nombre
       - Crea campo 'Segmentos' si no existe
       - Aplica condiciones AND para asignar segmentos
       - Elimina y re-sube usuarios que cambiaron
       - Guarda cambios localmente y en la nube

CONFIGURACIÓN:
    • API Token de Acumbamail debe estar en config.yaml
    • Usuario debe tener permisos de administración de listas

ESTRUCTURA DE SEGMENTOS.xlsx:
    Columnas requeridas:
    - NOMBRE LISTA: Nombre exacto de la lista en Acumbamail
    - NOMBRE SEGMENTO: Nombre del segmento a crear/aplicar
    - SEDE, ORGANO, ROL USUARIO, etc.: Condiciones de filtrado

USO:
    python mapear_segmentos.py          # Procesar todos los segmentos
    python mapear_segmentos.py --help   # Mostrar esta ayuda

EJEMPLOS:
    # Ejecutar mapeo completo
    python mapear_segmentos.py

    # Ver logs detallados
    tail -f data/automation_$(date +%Y%m%d).log
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        mostrar_ayuda()
        sys.exit(0)

    success = main()
    sys.exit(0 if success else 1)