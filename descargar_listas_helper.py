#!/usr/bin/env python3
"""
Script helper para descargar listas de AcumbaMail

Uso:
    ./descargar_listas_helper.py                    # Usar archivo por defecto
    ./descargar_listas_helper.py archivo.xlsx       # Usar archivo específico
    ./descargar_listas_helper.py --listar           # Listar archivos descargados
    ./descargar_listas_helper.py --help             # Ayuda
"""

import sys
import os
from pathlib import Path
import argparse

# Agregar el directorio raíz al path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from src.descargar_listas import procesar_listas_marcadas, listar_archivos_descargados

def main():
    parser = argparse.ArgumentParser(
        description="Descargador de listas de suscriptores de AcumbaMail",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  %(prog)s                              # Procesar data/Busqueda_Listas.xlsx
  %(prog)s data/mi_archivo.xlsx         # Procesar archivo específico
  %(prog)s --listar                     # Listar archivos descargados
  
Instrucciones:
  1. Abre el archivo Excel de búsqueda
  2. Marca con 'x' las listas que quieres descargar en la columna 'Buscar'
  3. Ejecuta este script
  4. Los archivos se guardarán en data/listas/
        """
    )
    
    parser.add_argument(
        'archivo',
        nargs='?',
        default='data/Busqueda_Listas.xlsx',
        help='Archivo Excel con listas a procesar (default: data/Busqueda_Listas.xlsx)'
    )
    
    parser.add_argument(
        '--listar', '-l',
        action='store_true',
        help='Listar archivos descargados existentes'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostrar información detallada'
    )
    
    args = parser.parse_args()
    
    print("📋 === DESCARGADOR DE LISTAS DE ACUMBAMAIL ===")
    
    if args.listar:
        print("📂 Listando archivos descargados...")
        archivos = listar_archivos_descargados()
        
        if archivos:
            print(f"📁 {len(archivos)} archivos encontrados en data/listas/:")
            for archivo in archivos:
                archivo_relativo = os.path.relpath(archivo)
                # Obtener información del archivo
                try:
                    stat = os.stat(archivo)
                    size_mb = stat.st_size / (1024 * 1024)
                    mtime = os.path.getmtime(archivo)
                    import datetime
                    fecha = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                    print(f"   📄 {archivo_relativo} ({size_mb:.1f} MB, {fecha})")
                except:
                    print(f"   📄 {archivo_relativo}")
        else:
            print("📂 No hay archivos descargados en data/listas/")
            print("\n💡 Para descargar listas:")
            print("   1. Marca listas con 'x' en data/Busqueda_Listas.xlsx")
            print("   2. Ejecuta: python descargar_listas_helper.py")
        return
    
    # Verificar que el archivo existe
    if not os.path.exists(args.archivo):
        print(f"❌ Error: No se encontró el archivo {args.archivo}")
        print("\n💡 Asegúrate de que:")
        print("   - El archivo existe")
        print("   - Tiene la estructura correcta (columnas: Buscar, ID_LISTA, NOMBRE LISTA, etc.)")
        print("   - Hay listas marcadas con 'x' en la columna 'Buscar'")
        sys.exit(1)
    
    print(f"🔍 Procesando archivo: {args.archivo}")
    
    try:
        # Procesar listas marcadas
        print("🚀 Iniciando descarga...")
        resultados = procesar_listas_marcadas(args.archivo)
        
        # Mostrar resultados
        print(f"\n📊 === RESUMEN DE RESULTADOS ===")
        print(f"Total listas procesadas: {resultados['total_listas']}")
        print(f"✅ Exitosas: {resultados['exitosas']}")
        print(f"❌ Fallidas: {resultados['fallidas']}")
        
        if resultados['archivos_creados']:
            print(f"\n📁 ARCHIVOS CREADOS ({len(resultados['archivos_creados'])}):")
            for archivo in resultados['archivos_creados']:
                archivo_relativo = os.path.relpath(archivo)
                print(f"   📄 {archivo_relativo}")
        
        if resultados['errores']:
            print(f"\n⚠️ ERRORES ENCONTRADOS ({len(resultados['errores'])}):")
            for error in resultados['errores']:
                print(f"   ❌ {error}")
        
        if resultados['total_listas'] == 0:
            print("\n💡 NO HAY LISTAS MARCADAS")
            print("Instrucciones:")
            print(f"   1. Abre {args.archivo}")
            print("   2. Marca con 'x' las listas que quieres descargar en la columna 'Buscar'")
            print("   3. Ejecuta este script nuevamente")
        else:
            print(f"\n🎉 ¡Proceso completado exitosamente!")
            
            # Mostrar estadísticas adicionales si es verbose
            if args.verbose and resultados['detalle']:
                print(f"\n📋 DETALLE POR LISTA:")
                for detalle in resultados['detalle']:
                    status = "✅" if detalle['exitoso'] else "❌"
                    print(f"   {status} {detalle['nombre']} (ID: {detalle['id_lista']})")
                    if detalle['exitoso']:
                        print(f"      📊 {detalle['suscriptores_descargados']} suscriptores descargados")
                        print(f"      📄 {os.path.relpath(detalle['archivo_creado'])}")
                    else:
                        print(f"      ⚠️ Error: {detalle['error']}")
        
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()