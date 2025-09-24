"""
Migrador y validador de configuración para manejar archivos config.yaml desactualizados o corruptos
"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
import shutil
from datetime import datetime

class ConfigMigrator:
    """Maneja la validación y migración automática de config.yaml"""

    def __init__(self, config_path: Path = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        self.config_path = config_path
        self.backup_dir = config_path.parent / "config_backups"

    def get_expected_structure(self) -> Dict[str, Any]:
        """Estructura esperada del config.yaml (esquema)"""
        return {
            # Credenciales del usuario (requeridas)
            'user': None,  # str: Email del usuario
            'password': None,  # str: Contraseña

            # Configuración opcional con defaults
            'headless': False,  # bool: Modo headless del navegador
            'debug': False,  # bool: Modo debug

            # API (solo api_key es configurable por usuario)
            'api': {
                'api_key': None  # str: API Key de Acumbamail
            },

            # Logging (estructura completa)
            'logging': {
                'enabled': True,
                'level': 'normal',  # minimal, normal, verbose, debug, trace
                'console_output': False,
                'file_output': True,
                'performance_tracking': True,
                'emoji_style': True,
                'structured_format': False
            },

            # Timeouts
            'timeouts': {
                'navigation': 60,
                'element': 15,
                'upload': 120,
                'default': 30
            },

            # Configuración de lista (usa email del usuario por defecto)
            'lista': {
                'sender_email': None,  # Se establece automáticamente
                'company': 'Mi Empresa',
                'country': 'España',
                'city': 'Madrid',
                'address': 'Calle Principal 123',
                'phone': '+34 900 000 000'
            }
        }

    def backup_config(self) -> Path:
        """Crea backup del config actual"""
        if not self.config_path.exists():
            return None

        # Crear directorio de backups
        self.backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"config_backup_{timestamp}.yaml"

        shutil.copy2(self.config_path, backup_path)
        return backup_path

    def validate_yaml_syntax(self) -> Tuple[bool, str]:
        """Valida que el YAML tenga sintaxis correcta"""
        if not self.config_path.exists():
            return False, "Archivo config.yaml no existe"

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            return True, "Sintaxis YAML válida"
        except yaml.YAMLError as e:
            return False, f"Error de sintaxis YAML: {e}"
        except Exception as e:
            return False, f"Error leyendo archivo: {e}"

    def validate_structure(self, config: Dict[str, Any]) -> List[str]:
        """Valida la estructura del config y retorna lista de problemas"""
        problems = []
        expected = self.get_expected_structure()

        def check_nested(current: Dict[str, Any], expected_nested: Dict[str, Any], path: str = ""):
            for key, expected_value in expected_nested.items():
                current_path = f"{path}.{key}" if path else key

                if key not in current:
                    problems.append(f"Campo faltante: {current_path}")
                    continue

                if isinstance(expected_value, dict):
                    if not isinstance(current[key], dict):
                        problems.append(f"Campo {current_path} debe ser un diccionario")
                    else:
                        check_nested(current[key], expected_value, current_path)

        check_nested(config, expected)
        return problems

    def migrate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Migra y completa la configuración con campos faltantes"""
        expected = self.get_expected_structure()
        migrated = {}

        def merge_nested(current: Dict[str, Any], expected_nested: Dict[str, Any]) -> Dict[str, Any]:
            result = {}

            # Copiar valores existentes
            for key, value in current.items():
                if key in expected_nested:
                    if isinstance(expected_nested[key], dict) and isinstance(value, dict):
                        result[key] = merge_nested(value, expected_nested[key])
                    else:
                        result[key] = value
                else:
                    # Mantener campos no esperados (para compatibilidad futura)
                    result[key] = value

            # Agregar campos faltantes con defaults
            for key, default_value in expected_nested.items():
                if key not in result:
                    if isinstance(default_value, dict):
                        result[key] = merge_nested({}, default_value)
                    else:
                        result[key] = default_value

            return result

        migrated = merge_nested(config, expected)

        # Lógica especial: si hay user pero no sender_email, usar user como sender_email
        if migrated.get('user') and not migrated.get('lista', {}).get('sender_email'):
            migrated['lista']['sender_email'] = migrated['user']

        return migrated

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Guarda la configuración migrada"""
        try:
            # Crear directorio si no existe
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True,
                         sort_keys=False, indent=2)
            return True
        except Exception as e:
            print(f"Error guardando configuración: {e}")
            return False

    def validate_and_migrate(self) -> Tuple[bool, str, List[str]]:
        """
        Proceso completo de validación y migración

        Returns:
            Tuple[success, message, warnings]
        """
        warnings = []

        # 1. Validar sintaxis YAML
        is_valid, syntax_msg = self.validate_yaml_syntax()
        if not is_valid:
            # Archivo corrupto o no existe, crear uno nuevo
            if "no existe" in syntax_msg:
                warnings.append("config.yaml no existe, creando uno nuevo")
            else:
                # Crear backup del archivo corrupto
                backup_path = self.backup_config()
                if backup_path:
                    warnings.append(f"config.yaml corrupto, backup creado en: {backup_path}")
                warnings.append("Creando config.yaml nuevo debido a errores de sintaxis")

            # Crear configuración nueva
            new_config = self.get_expected_structure()
            if self.save_config(new_config):
                return True, "Configuración creada exitosamente", warnings
            else:
                return False, "Error creando nueva configuración", warnings

        # 2. Cargar configuración actual
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                current_config = yaml.safe_load(f) or {}
        except Exception as e:
            return False, f"Error cargando configuración: {e}", warnings

        # 3. Validar estructura
        problems = self.validate_structure(current_config)

        # 4. Migrar si hay problemas
        if problems:
            warnings.extend([f"⚠️ {problem}" for problem in problems])

            # Crear backup antes de migrar
            backup_path = self.backup_config()
            if backup_path:
                warnings.append(f"Backup creado en: {backup_path}")

            # Migrar configuración
            migrated_config = self.migrate_config(current_config)

            if self.save_config(migrated_config):
                warnings.append("✅ Configuración actualizada automáticamente")
                return True, "Configuración migrada exitosamente", warnings
            else:
                return False, "Error guardando configuración migrada", warnings

        return True, "Configuración válida", warnings

    def get_migration_report(self) -> Dict[str, Any]:
        """Genera un reporte detallado del estado de la configuración"""
        report = {
            'file_exists': self.config_path.exists(),
            'syntax_valid': False,
            'structure_valid': False,
            'problems': [],
            'warnings': [],
            'backup_created': False
        }

        if not report['file_exists']:
            report['problems'].append("Archivo config.yaml no existe")
            return report

        # Validar sintaxis
        is_valid, syntax_msg = self.validate_yaml_syntax()
        report['syntax_valid'] = is_valid
        if not is_valid:
            report['problems'].append(syntax_msg)
            return report

        # Validar estructura
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                current_config = yaml.safe_load(f) or {}

            structure_problems = self.validate_structure(current_config)
            report['structure_valid'] = len(structure_problems) == 0
            report['problems'].extend(structure_problems)

        except Exception as e:
            report['problems'].append(f"Error procesando configuración: {e}")

        return report

# Función de conveniencia para usar desde otros módulos
def ensure_config_valid(config_path: Path = None) -> Tuple[bool, str, List[str]]:
    """
    Asegura que el config.yaml sea válido, migrándolo si es necesario

    Returns:
        Tuple[success, message, warnings]
    """
    migrator = ConfigMigrator(config_path)
    return migrator.validate_and_migrate()

# Función para obtener reporte sin modificar archivos
def get_config_status(config_path: Path = None) -> Dict[str, Any]:
    """Obtiene el estado de la configuración sin modificarla"""
    migrator = ConfigMigrator(config_path)
    return migrator.get_migration_report()

if __name__ == "__main__":
    # Prueba del migrador
    migrator = ConfigMigrator()
    success, message, warnings = migrator.validate_and_migrate()

    print(f"Resultado: {message}")
    if warnings:
        print("Advertencias:")
        for warning in warnings:
            print(f"  - {warning}")