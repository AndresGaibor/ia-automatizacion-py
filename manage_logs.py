#!/usr/bin/env python3
"""
🔧 Herramienta CLI para Gestión de Logging Profesional

Esta herramienta permite analizar, mejorar y gestionar el logging
en el proyecto Acumbamail Automation de forma automática.

Uso:
    python manage_logs.py --report              # Generar reporte completo
    python manage_logs.py --analyze             # Analizar sin cambios
    python manage_logs.py --enhance-file path   # Mejorar archivo específico
    python manage_logs.py --convert-prints      # Convertir prints a logging
    python manage_logs.py --update-config       # Actualizar config.yaml

Ejemplos:
    # Ver estado actual del logging
    python manage_logs.py --report

    # Analizar qué archivos necesitan atención
    python manage_logs.py --analyze

    # Mejorar logging de un archivo específico
    python manage_logs.py --enhance-file src/autentificacion.py

    # Convertir todos los prints a logging (dry-run primero)
    python manage_logs.py --convert-prints --dry-run

    # Aplicar cambios reales
    python manage_logs.py --convert-prints
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Agregar src al path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.logging_agent import LoggingAgent, LoggingConfig
    from src.utils import load_config, save_config
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de ejecutar desde el directorio raíz del proyecto")
    sys.exit(1)

class LoggingCLI:
    """CLI para gestión de logging"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.agent = LoggingAgent(str(self.project_root))

    def generate_report(self) -> None:
        """Genera reporte completo del estado del logging"""
        print("🔍 Generando reporte de logging...")
        report = self.agent.create_logging_report()
        print(report)

        # Guardar reporte en archivo
        report_file = self.project_root / "data" / "logging_report.md"
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n📄 Reporte guardado en: {report_file}")

    def analyze_project(self) -> None:
        """Analiza el proyecto sin hacer cambios"""
        print("🔍 Analizando proyecto...")
        analysis = self.agent.analyze_project()

        print(f"\n📊 Resultados del análisis:")
        print(f"   📁 Archivos analizados: {analysis['total_files']}")
        print(f"   🖨️  Print statements: {analysis['total_print_statements']}")
        print(f"   💡 Oportunidades de mejora: {len(analysis['recommendations'])}")

        if analysis['recommendations']:
            print(f"\n🎯 Archivos que necesitan atención:")
            for rec in analysis['recommendations']:
                if rec['type'] == 'high_print_usage':
                    print(f"   📄 {Path(rec['file']).name}: {rec['print_count']} prints")

    def enhance_file(self, file_path: str, dry_run: bool = False) -> None:
        """Mejora el logging de un archivo específico"""
        print(f"🔧 {'Analizando' if dry_run else 'Mejorando'} archivo: {file_path}")

        result = self.agent.enhance_file_logging(file_path, dry_run=dry_run)

        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return

        analysis = result['analysis']
        print(f"\n📊 Análisis de {Path(file_path).name}:")
        print(f"   🖨️  Print statements: {len(analysis.get('print_statements', []))}")
        print(f"   🔧 Funciones importantes: {len([f for f in analysis.get('function_definitions', []) if f.get('is_important', False)])}")
        print(f"   ⚠️  Exception handlers: {len(analysis.get('exception_handlers', []))}")

        if not dry_run:
            if 'improvements' in result and result['improvements']:
                print(f"✅ Mejoras aplicadas")
                for improvement in result['improvements']:
                    if improvement['type'] == 'file_modified':
                        print(f"   💾 Backup creado: {improvement['backup_created']}")
            else:
                print("ℹ️  No se requirieron cambios")

    def convert_prints_to_logging(self, dry_run: bool = False) -> None:
        """Convierte prints a logging en archivos principales"""
        print(f"🔄 {'Simulando conversión' if dry_run else 'Convirtiendo'} prints a logging...")

        # Archivos prioritarios para conversión
        priority_files = [
            'src/autentificacion.py',
            'src/descargar_suscriptores.py',
            'src/mapeo_segmentos.py',
            'src/demo.py',
            'src/listar_campanias.py',
            'app.py'
        ]

        converted_files = 0
        total_prints_converted = 0

        for file_path in priority_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            print(f"\n📄 Procesando {file_path}...")
            result = self.agent.enhance_file_logging(str(full_path), dry_run=dry_run)

            if 'error' not in result:
                print_count = len(result['analysis'].get('print_statements', []))
                if print_count > 0:
                    print(f"   🖨️  {print_count} print statements {'analizados' if dry_run else 'convertidos'}")
                    total_prints_converted += print_count
                    converted_files += 1
                else:
                    print(f"   ✅ No requiere cambios")

        print(f"\n🎯 Resumen:")
        print(f"   📁 Archivos procesados: {converted_files}")
        print(f"   🖨️  Print statements {'analizados' if dry_run else 'convertidos'}: {total_prints_converted}")

        if dry_run and total_prints_converted > 0:
            print(f"\n💡 Para aplicar cambios, ejecuta sin --dry-run")

    def update_config(self) -> None:
        """Actualiza config.yaml con configuración de logging"""
        print("⚙️  Actualizando config.yaml...")

        config = load_config()

        # Agregar configuración de logging si no existe
        if 'logging' not in config:
            config['logging'] = {
                'enabled': True,
                'level': 'normal',
                'console_output': False,
                'file_output': True,
                'performance_tracking': True,
                'emoji_style': True,
                'structured_format': False
            }

            save_config(config)
            print("✅ Configuración de logging agregada a config.yaml")
            print("\n📋 Nueva configuración:")
            print("   logging:")
            for key, value in config['logging'].items():
                print(f"     {key}: {value}")

            print(f"\n💡 Para habilitar logs en consola, cambia 'debug: true' en config.yaml")
        else:
            print("ℹ️  Configuración de logging ya existe en config.yaml")

    def toggle_debug_mode(self, enable: bool) -> None:
        """Habilita o deshabilita modo debug"""
        config = load_config()
        config['debug'] = enable
        save_config(config)

        status = "habilitado" if enable else "deshabilitado"
        print(f"🔧 Modo debug {status}")

        if enable:
            print("💡 Ahora los logs se mostrarán en consola durante la ejecución")
        else:
            print("💡 Los logs solo se guardarán en archivos")

    def show_current_config(self) -> None:
        """Muestra la configuración actual de logging"""
        config = load_config()
        logging_config = config.get('logging', {})

        print("⚙️  Configuración actual de logging:")
        print(f"   Debug mode: {'✅' if config.get('debug', False) else '❌'}")

        if logging_config:
            print(f"   Logging enabled: {'✅' if logging_config.get('enabled', True) else '❌'}")
            print(f"   Level: {logging_config.get('level', 'normal')}")
            print(f"   Console output: {'✅' if logging_config.get('console_output', False) else '❌'}")
            print(f"   File output: {'✅' if logging_config.get('file_output', True) else '❌'}")
        else:
            print("   ⚠️  No hay configuración específica de logging")
            print("   💡 Ejecuta --update-config para agregar configuración")

def main():
    parser = argparse.ArgumentParser(
        description='🔧 Herramienta de Gestión de Logging Profesional',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Ver reporte completo del estado actual
  python manage_logs.py --report

  # Analizar proyecto sin hacer cambios
  python manage_logs.py --analyze

  # Mejorar logging de archivo específico
  python manage_logs.py --enhance-file src/autentificacion.py

  # Simular conversión de prints (recomendado primero)
  python manage_logs.py --convert-prints --dry-run

  # Aplicar conversión de prints
  python manage_logs.py --convert-prints

  # Configurar config.yaml para logging
  python manage_logs.py --update-config

  # Habilitar modo debug (logs en consola)
  python manage_logs.py --debug-on

  # Ver configuración actual
  python manage_logs.py --show-config
        """
    )

    # Opciones principales
    parser.add_argument('--report', action='store_true',
                       help='Generar reporte completo del estado del logging')
    parser.add_argument('--analyze', action='store_true',
                       help='Analizar proyecto sin hacer cambios')
    parser.add_argument('--enhance-file', metavar='PATH',
                       help='Mejorar logging de un archivo específico')
    parser.add_argument('--convert-prints', action='store_true',
                       help='Convertir prints a logging en archivos principales')
    parser.add_argument('--update-config', action='store_true',
                       help='Actualizar config.yaml con configuración de logging')

    # Opciones de configuración
    parser.add_argument('--debug-on', action='store_true',
                       help='Habilitar modo debug (logs en consola)')
    parser.add_argument('--debug-off', action='store_true',
                       help='Deshabilitar modo debug')
    parser.add_argument('--show-config', action='store_true',
                       help='Mostrar configuración actual de logging')

    # Opciones de modificación
    parser.add_argument('--dry-run', action='store_true',
                       help='Simular cambios sin aplicarlos (recomendado primero)')
    parser.add_argument('--project-root', default='.',
                       help='Directorio raíz del proyecto (default: .)')

    args = parser.parse_args()

    # Verificar que estamos en el directorio correcto
    project_root = Path(args.project_root)
    if not (project_root / 'config.yaml').exists():
        print("❌ Error: No se encontró config.yaml")
        print("   Asegúrate de ejecutar desde el directorio raíz del proyecto")
        sys.exit(1)

    cli = LoggingCLI(args.project_root)

    # Ejecutar comando seleccionado
    try:
        if args.report:
            cli.generate_report()
        elif args.analyze:
            cli.analyze_project()
        elif args.enhance_file:
            cli.enhance_file(args.enhance_file, dry_run=args.dry_run)
        elif args.convert_prints:
            cli.convert_prints_to_logging(dry_run=args.dry_run)
        elif args.update_config:
            cli.update_config()
        elif args.debug_on:
            cli.toggle_debug_mode(True)
        elif args.debug_off:
            cli.toggle_debug_mode(False)
        elif args.show_config:
            cli.show_current_config()
        else:
            print("🤔 No se especificó ninguna acción.")
            print("💡 Usa --help para ver opciones disponibles")
            print("\n🚀 Comandos rápidos:")
            print("   python manage_logs.py --report        # Ver estado actual")
            print("   python manage_logs.py --analyze       # Analizar sin cambios")
            print("   python manage_logs.py --update-config # Configurar logging")

    except KeyboardInterrupt:
        print("\n⏹️  Operación cancelada por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        print("💡 Si el problema persiste, verifica la configuración del proyecto")
        sys.exit(1)

if __name__ == "__main__":
    main()