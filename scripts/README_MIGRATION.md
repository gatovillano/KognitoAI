# Guía de Migración de Equipos a Workspaces

Este directorio contiene scripts para migrar los datos de equipos existentes a workspaces antes de eliminar las tablas de equipos del sistema.

## 📋 Resumen del Proceso

La migración consta de 4 fases principales:

1. **Verificación**: Analizar equipos existentes y sus recursos asociados
2. **Migración**: Transferir recursos de equipos a workspaces
3. **Validación**: Verificar la integridad de la migración
4. **Limpieza**: Eliminar tablas de equipos (opcional)

## 📁 Archivos del Script

### Scripts Principales

- **`team_migration_helper.py`** - Asistente interactivo completo (recomendado)
- **`migrate_teams_to_workspaces.py`** - Script de migración avanzado
- **`validate_migration.py`** - Validador de integridad de migración
- **`remove_team_tables.py`** - Eliminador de tablas de equipos

### Scripts Independientes

Cada script puede ejecutarse de forma independiente según sea necesario:

#### 1. Asistente de Migración (Recomendado)

```bash
python scripts/team_migration_helper.py
```

Guía paso a paso a través de todo el proceso de migración.

#### 2. Script de Migración Avanzado

```bash
# Listar equipos con recursos
python scripts/migrate_teams_to_workspaces.py --action list

# Migración interactiva
python scripts/migrate_teams_to_workspaces.py --action migrate

# Migrar equipo específico
python scripts/migrate_teams_to_workspaces.py --action migrate --team-id <team_id> --workspace-id <workspace_id>

# Generar reporte
python scripts/migrate_teams_to_workspaces.py --action report --output migration_report.json
```

#### 3. Validador de Migración

```bash
# Validación básica
python scripts/validate_migration.py

# Validación con resultados detallados
python scripts/validate_migration.py --detailed

# Validación con reporte
python scripts/validate_migration.py --output validation_report.json
```

#### 4. Eliminador de Tablas

```bash
# Verificar estado de migración
python scripts/remove_team_tables.py --action verify

# Listar equipos existentes
python scripts/remove_team_tables.py --action list

# Crear respaldo
python scripts/remove_team_tables.py --action backup

# Eliminar tablas (interactivo)
python scripts/remove_team_tables.py --action remove --confirm
```

## 🚀 Uso Recomendado

### Para Primera Migración (Recomendado)

```bash
python scripts/team_migration_helper.py
```

Este script guiará paso a paso a través de todo el proceso, desde la verificación inicial hasta la eliminación final de tablas.

### Para Migraciones Específicas

```bash
# 1. Verificar estado
python scripts/validate_migration.py

# 2. Migrar equipos específicos
python scripts/migrate_teams_to_workspaces.py --action migrate

# 3. Validar migración
python scripts/validate_migration.py --detailed

# 4. Eliminar tablas (si todo está correcto)
python scripts/remove_team_tables.py --action remove --confirm
```

## 📊 Recursos que se Migran

La migración maneja los siguientes tipos de recursos:

### 1. Miembros de Equipos

- Se crean permisos de workspace para cada miembro del equipo
- Los roles se asignan como 'editor' por defecto

### 2. Notas

- Se transfieren notas del campo `team_id` al campo `workspace_id`
- Se mantiene la integridad de las relaciones con cuentas

### 3. Eventos de Agenda

- Se migran eventos asociados a equipos a workspaces
- Se preservan todas las relaciones y metadatos

### 4. Documentos (Embeddings)

- Se actualizan todos los embeddings en `langchain_pg_embedding`
- Se mantiene la integridad de las colecciones y topics

### 5. Topics/Colecciones

- Se transfieren topics definidos por usuarios
- Se preservan las relaciones con contactos y otros recursos

## 🔍 Opciones de Migración

### 1. Creación Automática de Workspaces

- Cada equipo genera un workspace con nombre "Equipo: [nombre_equipo]"
- El administrador del equipo se convierte en owner del workspace

### 2. Migración a Workspaces Existentes

- Permite seleccionar workspaces existentes para los recursos
- Útil para consolidar equipos en workspaces preexistentes

### 3. Migración Interactiva

- Guía al usuario paso a paso
- Permite decisiones individuales para cada equipo

## ⚠️ Advertencias Importantes

### Antes de Migrar

1. **Realice un respaldo completo** de la base de datos
2. **Detenga la aplicación** durante el proceso de migración
3. **Verifique permisos** de acceso a la base de datos

### Durante la Migración

1. **No interrumpa el proceso** una vez iniciado
2. **Monitoree los logs** para detectar errores
3. **Verifique la integridad** después de cada fase

### Después de la Migración

1. **Ejecute validaciones** para asegurar la integridad
2. **Pruebe la funcionalidad** de workspaces
3. **Solo elimine tablas** si la validación es exitosa

## 📈 Reportes y Logs

### Reportes Generados

1. **Reporte de Migración** (`migration_report_*.json`)
   - Resumen de recursos migrados
   - Detalles por equipo
   - Log de operaciones realizadas

2. **Reporte de Validación** (`validation_report_*.json`)
   - Estado de cada verificación
   - Advertencias y errores detectados
   - Recomendaciones de acción

3. **Respaldo de Equipos** (`team_backup_*.sql`)
   - Datos de equipos antes de la eliminación
   - Información para posibles restauraciones

### Niveles de Validación

- **PASS**: ✅ Todo correcto
- **WARN**: ⚠️ Advertencia, puede proceder con precaución
- **FAIL**: ❌ Error crítico, no debe proceder

## 🔧 Solución de Problemas

### Problemas Comunes

#### 1. Error de Conexión a Base de Datos

```bash
# Verifique la configuración en .env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
```

#### 2. Permisos Insuficientes

```bash
# Asegúrese de tener permisos de lectura/escritura
# en todas las tablas del sistema
```

#### 3. Espacio en Disco Insuficiente

```bash
# La migración puede requerir espacio temporal
# para operaciones de respaldo y validación
```

#### 4. Proceso Interrumpido

```bash
# Si la migración se interrumpe, ejecute validación
# para determinar el estado y reanudar si es seguro
python scripts/validate_migration.py --detailed
```

### Comandos de Diagnóstico

```bash
# Verificar estado de equipos
python scripts/migrate_teams_to_workspaces.py --action list

# Validar integridad general
python scripts/validate_migration.py

# Crear respaldo de estado actual
python scripts/remove_team_tables.py --action backup
```

## 📞 Soporte

Para soporte adicional:

1. Revise los logs generados durante la migración
2. Consulte los reportes de validación
3. Verifique la configuración de la base de datos
4. Contacte al equipo de desarrollo si persisten los problemas

---

**⚠️ ADVERTENCIA**: Estos scripts realizan operaciones en la base de datos que pueden ser irreversibles. Asegúrese de comprender completamente el proceso y tener respaldos completos antes de proceder.
