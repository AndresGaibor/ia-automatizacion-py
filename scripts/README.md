# Scripts de Automatización

Este directorio contiene scripts de utilidad para el desarrollo y despliegue del proyecto.

## 📦 release.sh

Script para crear y publicar nuevas versiones del proyecto automáticamente.

### Uso

```bash
# Incrementar versión patch (v2.18.0 → v2.18.1)
./scripts/release.sh

# Incrementar versión minor (v2.18.0 → v2.19.0)
./scripts/release.sh minor

# Incrementar versión major (v2.18.0 → v3.0.0)
./scripts/release.sh major
```

### Opciones

- `--force` - No pedir confirmación antes de crear el tag
- `--dry-run` - Mostrar qué haría sin ejecutar comandos (útil para probar)
- `--allow-dirty` - Permitir cambios sin commitear en el repositorio
- `-m, --message` - Mensaje personalizado para el tag
- `-h, --help` - Mostrar ayuda completa

### Ejemplos

```bash
# Ver qué haría sin ejecutar
./scripts/release.sh minor --dry-run

# Crear release sin confirmación
./scripts/release.sh patch --force

# Crear release con mensaje personalizado
./scripts/release.sh minor -m "Nueva funcionalidad de segmentos"

# Crear release permitiendo cambios sin commitear
./scripts/release.sh patch --allow-dirty
```

### Proceso Automático

Cuando ejecutas el script, automáticamente:

1. ✅ Valida que estés en un repositorio git limpio
2. 📌 Obtiene el último tag del repositorio (ej: v2.18.0)
3. 📈 Calcula la nueva versión según el tipo de incremento
4. 🏷️ Crea el tag localmente con mensaje descriptivo
5. 🚀 Sube el tag a GitHub (origin)
6. 🤖 GitHub Actions se dispara automáticamente para:
   - Compilar el ejecutable Windows
   - Crear release en GitHub
   - Generar release notes automáticamente

### Versionado Semántico

El proyecto usa [Semantic Versioning](https://semver.org/) en formato `vX.Y.Z`:

- **Major (X)**: Cambios incompatibles con versiones anteriores
  - `v2.18.0 → v3.0.0`
  - Ejemplo: Cambio de arquitectura, API breaking changes

- **Minor (Y)**: Nueva funcionalidad compatible con versiones anteriores
  - `v2.18.0 → v2.19.0`
  - Ejemplo: Nueva funcionalidad, mejoras significativas

- **Patch (Z)**: Correcciones de bugs compatibles
  - `v2.18.0 → v2.18.1`
  - Ejemplo: Hotfix, corrección de bugs menores

### Workflow de Release

```bash
# 1. Hacer cambios y commitearlos
git add .
git commit -m "feat: agregar nueva funcionalidad"

# 2. (Opcional) Ver qué versión se crearía
./scripts/release.sh minor --dry-run

# 3. Crear y publicar el release
./scripts/release.sh minor

# 4. El script crea el tag y lo sube a GitHub

# 5. GitHub Actions automáticamente:
#    - Compila el ejecutable Windows
#    - Crea el release
#    - Publica el ejecutable en Releases
```

### Verificación

Después de ejecutar el script, puedes verificar:

- **GitHub Actions**: https://github.com/AndresGaibor/ia-automatizacion-py/actions
- **Releases**: https://github.com/AndresGaibor/ia-automatizacion-py/releases
- **Tags**: https://github.com/AndresGaibor/ia-automatizacion-py/tags

### Solución de Problemas

**Error: "El directorio de trabajo tiene cambios sin commitear"**
```bash
# Opción 1: Commitear los cambios primero
git add .
git commit -m "descripción de cambios"

# Opción 2: Usar --allow-dirty (no recomendado)
./scripts/release.sh --allow-dirty
```

**Error: "El tag vX.Y.Z ya existe"**
```bash
# Ver todos los tags
git tag --sort=-v:refname

# Si necesitas recrear el tag (úsalo con cuidado)
git tag -d v2.18.1           # Eliminar localmente
git push origin :v2.18.1     # Eliminar del remoto
./scripts/release.sh         # Crear nuevamente
```

**Cancelar un release que ya se subió**
```bash
# 1. Eliminar el tag del remoto
git push origin :refs/tags/v2.18.1

# 2. Eliminar el tag local
git tag -d v2.18.1

# 3. Eliminar el release en GitHub
# Ve a: https://github.com/AndresGaibor/ia-automatizacion-py/releases
# Y elimina el release manualmente
```

### Requisitos

- Git instalado y configurado
- Acceso de push al repositorio remoto (origin)
- Bash shell (disponible por defecto en macOS/Linux)

### Notas

- El script valida que el directorio de trabajo esté limpio antes de crear el tag
- Usa confirmación interactiva a menos que uses `--force`
- En caso de error al subir el tag, se hace rollback automático
- Los mensajes de error son claros y sugieren soluciones
