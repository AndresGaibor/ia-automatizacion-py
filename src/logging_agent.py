"""
Agente de Logging Profesional para Acumbamail Automation

Este agente se encarga de:
1. Gestionar logs de manera inteligente basado en config.yaml
2. Convertir prints existentes a logging estructurado
3. Añadir logs estratégicos en lugares clave
4. Mantener compatibilidad con el sistema existente
"""

import ast
import os
import re
import yaml
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

class LogLevel(Enum):
    """Niveles de logging configurables"""
    SILENT = 0      # Solo errores críticos
    MINIMAL = 1     # Errores y warnings importantes
    NORMAL = 2      # Flujo principal de operaciones
    VERBOSE = 3     # Información detallada
    DEBUG = 4       # Todo incluido
    TRACE = 5       # Máximo detalle para desarrollo

@dataclass
class LoggingConfig:
    """Configuración de logging desde config.yaml"""
    enabled: bool = True
    level: LogLevel = LogLevel.NORMAL
    console_output: bool = True
    file_output: bool = True
    performance_tracking: bool = True
    emoji_style: bool = True
    structured_format: bool = False

    @classmethod
    def from_yaml(cls, config_path: str) -> 'LoggingConfig':
        """Carga configuración desde config.yaml"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            # Determinar nivel basado en debug flag
            debug_enabled = config_data.get('debug', False)

            if debug_enabled:
                level = LogLevel.DEBUG
                console_output = True
            else:
                level = LogLevel.MINIMAL
                console_output = False

            # Buscar configuración de logging específica si existe
            logging_config = config_data.get('logging', {})

            # Mapear string a enum de forma segura
            level_str = logging_config.get('level', level.name).upper()
            try:
                final_level = LogLevel[level_str]
            except KeyError:
                final_level = level

            return cls(
                enabled=logging_config.get('enabled', True),
                level=final_level,
                console_output=logging_config.get('console_output', console_output),
                file_output=logging_config.get('file_output', True),
                performance_tracking=logging_config.get('performance_tracking', True),
                emoji_style=logging_config.get('emoji_style', True),
                structured_format=logging_config.get('structured_format', False)
            )
        except Exception as e:
            print(f"⚠️ Error cargando configuración de logging: {e}")
            return cls()

class CodeAnalyzer:
    """Analizador de código para identificar oportunidades de logging"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.logging_opportunities: List[Dict[str, Any]] = []

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analiza un archivo Python para oportunidades de logging"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            analyzer = LoggingOpportunityVisitor(str(file_path))
            analyzer.visit(tree)

            return {
                'file_path': str(file_path),
                'print_statements': analyzer.print_statements,
                'function_definitions': analyzer.function_definitions,
                'exception_handlers': analyzer.exception_handlers,
                'long_operations': analyzer.long_operations,
                'api_calls': analyzer.api_calls,
                'file_operations': analyzer.file_operations,
                'browser_actions': analyzer.browser_actions,
                'current_logger_usage': analyzer.current_logger_usage
            }
        except Exception as e:
            return {
                'file_path': str(file_path),
                'error': str(e),
                'print_statements': [],
                'function_definitions': [],
                'exception_handlers': [],
                'long_operations': [],
                'api_calls': [],
                'file_operations': [],
                'browser_actions': [],
                'current_logger_usage': []
            }

class LoggingOpportunityVisitor(ast.NodeVisitor):
    """Visitor AST para encontrar oportunidades de logging"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.print_statements: List[Dict[str, Any]] = []
        self.function_definitions: List[Dict[str, Any]] = []
        self.exception_handlers: List[Dict[str, Any]] = []
        self.long_operations: List[Dict[str, Any]] = []
        self.api_calls: List[Dict[str, Any]] = []
        self.file_operations: List[Dict[str, Any]] = []
        self.browser_actions: List[Dict[str, Any]] = []
        self.current_logger_usage: List[Dict[str, Any]] = []

    def visit_Call(self, node):
        """Visita llamadas a funciones"""
        # Detectar print statements
        if isinstance(node.func, ast.Name) and node.func.id == 'print':
            self.print_statements.append({
                'line': node.lineno,
                'content': self._extract_print_content(node),
                'type': self._classify_print_type(node)
            })

        # Detectar uso actual de logger
        elif (isinstance(node.func, ast.Attribute) and
              isinstance(node.func.value, ast.Name) and
              node.func.value.id in ['logger', 'log']):
            self.current_logger_usage.append({
                'line': node.lineno,
                'method': node.func.attr,
                'level': node.func.attr
            })

        # Detectar operaciones de API
        elif (isinstance(node.func, ast.Attribute) and
              any(api_method in str(node.func.attr) for api_method in
                  ['get', 'post', 'put', 'delete', 'request'])):
            self.api_calls.append({
                'line': node.lineno,
                'method': node.func.attr,
                'type': 'api_request'
            })

        # Detectar operaciones de browser/playwright
        elif (isinstance(node.func, ast.Attribute) and
              any(browser_method in str(node.func.attr) for browser_method in
                  ['click', 'fill', 'goto', 'wait_for', 'locator', 'get_by'])):
            self.browser_actions.append({
                'line': node.lineno,
                'method': node.func.attr,
                'type': 'browser_action'
            })

        # Detectar operaciones de archivo
        elif isinstance(node.func, ast.Name) and node.func.id in ['open', 'read', 'write']:
            self.file_operations.append({
                'line': node.lineno,
                'operation': node.func.id,
                'type': 'file_operation'
            })

        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Visita definiciones de funciones"""
        # Detectar funciones que podrían beneficiarse de logging
        is_important = any(keyword in node.name.lower() for keyword in
                          ['login', 'auth', 'download', 'upload', 'process', 'extract',
                           'scrape', 'navigate', 'search', 'create', 'delete'])

        self.function_definitions.append({
            'line': node.lineno,
            'name': node.name,
            'is_async': isinstance(node, ast.AsyncFunctionDef),
            'is_important': is_important,
            'has_decorators': len(node.decorator_list) > 0
        })

        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        """Visita manejadores de excepciones"""
        self.exception_handlers.append({
            'line': node.lineno,
            'exception_type': node.type.id if node.type and isinstance(node.type, ast.Name) else 'generic',
            'has_logging': self._has_logging_in_block(node.body)
        })

        self.generic_visit(node)

    def visit_For(self, node):
        """Visita bucles for (operaciones potencialmente largas)"""
        self.long_operations.append({
            'line': node.lineno,
            'type': 'for_loop',
            'might_need_progress': True
        })

        self.generic_visit(node)

    def visit_While(self, node):
        """Visita bucles while (operaciones potencialmente largas)"""
        self.long_operations.append({
            'line': node.lineno,
            'type': 'while_loop',
            'might_need_progress': True
        })

        self.generic_visit(node)

    def _extract_print_content(self, node) -> str:
        """Extrae el contenido de un print statement"""
        try:
            if node.args:
                # Simplificación: solo tomar el primer argumento
                return str(node.args[0])[:100]
            return ""
        except:
            return "complex_print"

    def _classify_print_type(self, node) -> str:
        """Clasifica el tipo de print statement"""
        content = self._extract_print_content(node).lower()

        if any(keyword in content for keyword in ['error', 'exception', 'failed', 'fail']):
            return 'error'
        elif any(keyword in content for keyword in ['warning', 'warn', 'caution']):
            return 'warning'
        elif any(keyword in content for keyword in ['success', 'complete', 'done', '✅', '✓']):
            return 'success'
        elif any(keyword in content for keyword in ['processing', 'loading', 'extracting', '⏳']):
            return 'progress'
        elif any(keyword in content for keyword in ['debug', 'info', 'detail']):
            return 'debug'
        else:
            return 'info'

    def _has_logging_in_block(self, body) -> bool:
        """Verifica si un bloque ya tiene logging"""
        for stmt in body:
            if (isinstance(stmt, ast.Expr) and
                isinstance(stmt.value, ast.Call) and
                isinstance(stmt.value.func, ast.Attribute) and
                stmt.value.func.attr in ['debug', 'info', 'warning', 'error', 'critical']):
                return True
        return False

class LoggingAgent:
    """Agente principal para gestión automática de logging"""

    def __init__(self, project_root: str, config_path: str = None):
        self.project_root = Path(project_root)
        self.config_path = config_path or str(self.project_root / "config.yaml")
        self.logging_config = LoggingConfig.from_yaml(self.config_path)
        self.analyzer = CodeAnalyzer(project_root)

        # Patrones de logging para diferentes situaciones
        self.logging_patterns = {
            'function_entry': self._get_function_entry_pattern,
            'function_exit': self._get_function_exit_pattern,
            'error_handling': self._get_error_handling_pattern,
            'progress_tracking': self._get_progress_pattern,
            'api_request': self._get_api_request_pattern,
            'browser_action': self._get_browser_action_pattern,
            'file_operation': self._get_file_operation_pattern,
            'print_replacement': self._get_print_replacement_pattern
        }

    def analyze_project(self) -> Dict[str, Any]:
        """Analiza todo el proyecto para oportunidades de logging"""
        python_files = list(self.project_root.rglob("*.py"))
        analysis = {
            'total_files': len(python_files),
            'files_analyzed': [],
            'total_print_statements': 0,
            'total_logging_opportunities': 0,
            'recommendations': []
        }

        for py_file in python_files:
            # Evitar archivos de tests, migrations, etc.
            if any(skip_dir in str(py_file) for skip_dir in ['.venv', '__pycache__', '.git', 'tests']):
                continue

            file_analysis = self.analyzer.analyze_file(py_file)
            analysis['files_analyzed'].append(file_analysis)
            analysis['total_print_statements'] += len(file_analysis.get('print_statements', []))

        # Generar recomendaciones
        analysis['recommendations'] = self._generate_recommendations(analysis['files_analyzed'])

        return analysis

    def enhance_file_logging(self, file_path: str, dry_run: bool = True) -> Dict[str, Any]:
        """Mejora el logging de un archivo específico"""
        file_path = Path(file_path)

        if not file_path.exists():
            return {'error': 'File not found'}

        analysis = self.analyzer.analyze_file(file_path)
        improvements = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Procesar mejoras basadas en análisis
            modified_content = self._apply_logging_improvements(original_content, analysis)

            if not dry_run and modified_content != original_content:
                # Crear backup
                backup_path = file_path.with_suffix('.py.backup')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)

                # Aplicar cambios
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)

                improvements.append({
                    'type': 'file_modified',
                    'backup_created': str(backup_path)
                })

            return {
                'file_path': str(file_path),
                'analysis': analysis,
                'improvements': improvements,
                'dry_run': dry_run,
                'config_level': self.logging_config.level.name
            }

        except Exception as e:
            return {
                'file_path': str(file_path),
                'error': str(e)
            }

    def _apply_logging_improvements(self, content: str, analysis: Dict[str, Any]) -> str:
        """Aplica mejoras de logging al contenido del archivo"""
        lines = content.split('\n')
        modified_lines = lines.copy()

        # Solo aplicar si el logging está habilitado en config
        if not self.logging_config.enabled:
            return content

        # Agregar import de logger si no existe
        if not any('from .logger import get_logger' in line or 'from src.logger import get_logger' in line
                  for line in lines):
            # Encontrar lugar apropiado para import
            import_line = self._find_import_insertion_point(lines)
            if 'src/' in analysis['file_path']:
                modified_lines.insert(import_line, 'from .logger import get_logger')
            else:
                modified_lines.insert(import_line, 'from src.logger import get_logger')

            # Agregar inicialización de logger
            modified_lines.insert(import_line + 1, '')
            modified_lines.insert(import_line + 2, '# Configurar logger basado en config.yaml')
            modified_lines.insert(import_line + 3, 'logger = get_logger()')
            modified_lines.insert(import_line + 4, '')

        # Reemplazar print statements con logging apropiado
        for print_stmt in analysis.get('print_statements', []):
            line_idx = print_stmt['line'] - 1
            if line_idx < len(modified_lines):
                replacement = self._generate_print_replacement(
                    modified_lines[line_idx],
                    print_stmt['type']
                )
                if replacement:
                    modified_lines[line_idx] = replacement

        # Agregar logging a funciones importantes
        for func in analysis.get('function_definitions', []):
            if func['is_important'] and func['line'] - 1 < len(modified_lines):
                # Agregar logging de entrada a función
                func_line_idx = func['line'] - 1
                indent = self._get_line_indent(modified_lines[func_line_idx])

                # Buscar el lugar después de la definición de función
                body_start_idx = func_line_idx + 1
                while (body_start_idx < len(modified_lines) and
                       (modified_lines[body_start_idx].strip() == '' or
                        modified_lines[body_start_idx].strip().startswith('"""') or
                        modified_lines[body_start_idx].strip().startswith("'''"))):
                    body_start_idx += 1

                if body_start_idx < len(modified_lines):
                    entry_log = f"{indent}    logger.log_checkpoint(f'Iniciando {func['name']}')"
                    modified_lines.insert(body_start_idx, entry_log)

        # Mejorar exception handlers
        for exc_handler in analysis.get('exception_handlers', []):
            if not exc_handler['has_logging']:
                line_idx = exc_handler['line'] - 1
                if line_idx < len(modified_lines):
                    indent = self._get_line_indent(modified_lines[line_idx])
                    error_log = f"{indent}    logger.log_error('{exc_handler['exception_type']}', e, context='Exception en operación')"
                    # Insertar después de la línea except
                    modified_lines.insert(line_idx + 1, error_log)

        return '\n'.join(modified_lines)

    def _generate_print_replacement(self, print_line: str, print_type: str) -> Optional[str]:
        """Genera reemplazo de print con logging apropiado"""
        if not self.logging_config.enabled:
            return None

        # Extraer el contenido del print
        content_match = re.search(r'print\((.*)\)', print_line)
        if not content_match:
            return None

        print_content = content_match.group(1)
        indent = self._get_line_indent(print_line)

        # Mapear tipo de print a método de logger
        method_map = {
            'error': 'error',
            'warning': 'warning',
            'success': 'log_success',
            'progress': 'log_progress',
            'debug': 'debug',
            'info': 'info'
        }

        method = method_map.get(print_type, 'info')

        # Solo mostrar si el nivel de config lo permite
        if print_type == 'debug' and self.logging_config.level.value < LogLevel.DEBUG.value:
            return f"{indent}# Debug print removed - enable debug mode to see"
        elif print_type == 'info' and self.logging_config.level.value < LogLevel.VERBOSE.value:
            return f"{indent}# Info print removed - increase verbosity to see"

        return f"{indent}logger.{method}({print_content})"

    def _find_import_insertion_point(self, lines: List[str]) -> int:
        """Encuentra el punto apropiado para insertar imports"""
        # Buscar después del último import existente
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                last_import_idx = i

        return last_import_idx + 1

    def _get_line_indent(self, line: str) -> str:
        """Obtiene la indentación de una línea"""
        return line[:len(line) - len(line.lstrip())]

    def _generate_recommendations(self, files_analyzed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Genera recomendaciones basadas en análisis"""
        recommendations = []

        # Archivos con muchos prints
        for file_analysis in files_analyzed:
            print_count = len(file_analysis.get('print_statements', []))
            if print_count > 10:
                recommendations.append({
                    'type': 'high_print_usage',
                    'file': file_analysis['file_path'],
                    'print_count': print_count,
                    'priority': 'high',
                    'description': f'Archivo con {print_count} print statements que deberían convertirse a logging'
                })

        return recommendations

    def generate_config_update(self) -> str:
        """Genera configuración sugerida para config.yaml"""
        config_addition = """
# Configuración de Logging Profesional
logging:
  enabled: true                    # Habilitar sistema de logging
  level: "normal"                  # minimal, normal, verbose, debug, trace
  console_output: false            # Mostrar logs en consola (automático si debug: true)
  file_output: true               # Guardar logs en archivos
  performance_tracking: true       # Tracking de performance automático
  emoji_style: true               # Usar emojis en logs para mejor legibilidad
  structured_format: false        # Usar formato JSON (para integración con sistemas externos)

  # Configuración avanzada
  batch_operations: true          # Agrupar operaciones repetitivas
  heartbeat_interval: 30          # Segundos entre heartbeats para operaciones largas
  auto_cleanup_days: 30           # Días para mantener logs antiguos

  # Niveles específicos por módulo
  modules:
    api: "verbose"                # Logging detallado para API calls
    scraping: "normal"            # Logging normal para web scraping
    authentication: "verbose"     # Logging detallado para autenticación
    file_operations: "minimal"    # Logging mínimo para operaciones de archivo
"""
        return config_addition

    def create_logging_report(self) -> str:
        """Crea un reporte completo del estado del logging"""
        analysis = self.analyze_project()

        report = f"""
# 📊 Reporte de Logging - Acumbamail Automation

## Estado Actual
- **Archivos analizados**: {analysis['total_files']}
- **Print statements encontrados**: {analysis['total_print_statements']}
- **Configuración actual**: {self.logging_config.level.name}
- **Logging habilitado**: {'✅' if self.logging_config.enabled else '❌'}

## Archivos que Necesitan Atención

"""

        for rec in analysis['recommendations']:
            if rec['type'] == 'high_print_usage':
                report += f"### {rec['file']}\n"
                report += f"- **Prioridad**: {rec['priority']}\n"
                report += f"- **Print statements**: {rec['print_count']}\n"
                report += f"- **Acción**: {rec['description']}\n\n"

        report += f"""
## Configuración Recomendada

Para habilitar logging profesional, actualiza tu `config.yaml`:

```yaml
{self.generate_config_update()}
```

## Próximos Pasos

1. **Actualizar config.yaml** con la configuración de logging
2. **Ejecutar conversión automática** de prints a logging
3. **Probar con debug: true** para ver todos los logs
4. **Ajustar niveles** según necesidades

## Beneficios del Sistema de Logging Profesional

- ✅ **Control granular** de verbosidad
- ✅ **Performance tracking** automático
- ✅ **Logs estructurados** para análisis
- ✅ **Gestión automática** de archivos de log
- ✅ **Compatibilidad** con sistema existente
- ✅ **Emojis y formato visual** para mejor legibilidad
"""

        return report

    # Métodos de patrones de logging (placeholders para futura expansión)
    def _get_function_entry_pattern(self, func_name: str) -> str:
        return f"logger.log_checkpoint(f'Iniciando {func_name}')"

    def _get_function_exit_pattern(self, func_name: str) -> str:
        return f"logger.log_success(f'Completado {func_name}')"

    def _get_error_handling_pattern(self, exception_type: str) -> str:
        return f"logger.log_error('{exception_type}', e, context='Exception en operación')"

    def _get_progress_pattern(self, current: str, total: str) -> str:
        return f"logger.log_progress({current}, {total})"

    def _get_api_request_pattern(self, method: str, url: str) -> str:
        return f"logger.log_browser_action('API {method}', '{url}')"

    def _get_browser_action_pattern(self, action: str, target: str) -> str:
        return f"logger.log_browser_action('{action}', '{target}')"

    def _get_file_operation_pattern(self, operation: str, file_path: str) -> str:
        return f"logger.log_file_operation('{operation}', '{file_path}')"

    def _get_print_replacement_pattern(self, content: str, level: str) -> str:
        return f"logger.{level}({content})"

def main():
    """Función principal para ejecutar el agente de logging"""
    import argparse

    parser = argparse.ArgumentParser(description='Agente de Logging Profesional')
    parser.add_argument('--project-root', default='.', help='Directorio raíz del proyecto')
    parser.add_argument('--analyze', action='store_true', help='Analizar proyecto sin hacer cambios')
    parser.add_argument('--enhance-file', help='Mejorar logging de un archivo específico')
    parser.add_argument('--dry-run', action='store_true', help='Simular cambios sin aplicarlos')
    parser.add_argument('--report', action='store_true', help='Generar reporte completo')

    args = parser.parse_args()

    agent = LoggingAgent(args.project_root)

    if args.report:
        print(agent.create_logging_report())
    elif args.analyze:
        analysis = agent.analyze_project()
        print(f"📊 Análisis completado:")
        print(f"   Archivos: {analysis['total_files']}")
        print(f"   Print statements: {analysis['total_print_statements']}")
        print(f"   Recomendaciones: {len(analysis['recommendations'])}")
    elif args.enhance_file:
        result = agent.enhance_file_logging(args.enhance_file, dry_run=args.dry_run)
        print(f"🔧 Resultado para {result['file_path']}:")
        if 'error' in result:
            print(f"   ❌ Error: {result['error']}")
        else:
            print(f"   ✅ Análisis completado")
            print(f"   📊 Print statements: {len(result['analysis']['print_statements'])}")
    else:
        print("Usa --help para ver opciones disponibles")

if __name__ == "__main__":
    main()