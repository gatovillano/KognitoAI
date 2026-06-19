#!/bin/sh
set -e

BACKUP_DIR="/backups"
DATE=$(date +"%Y-%m-%d_%H-%M-%S")

# Backup PostgreSQL
echo "[INFO] Iniciando backup de PostgreSQL..."
pg_dump -U "$POSTGRES_USER" -h db "$POSTGRES_DB" > "$BACKUP_DIR/postgres_${DATE}.sql"

# Backup Neo4j (dump)
echo "[INFO] Iniciando backup de Neo4j..."
if [ -n "$NEO4J_PASSWORD" ]; then
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "CALL dbms.backup()"
fi
# Opción alternativa: copiar directorio de datos (requiere acceso a volumen)
# cp -r /data "$BACKUP_DIR/neo4j_${DATE}"

echo "[INFO] Backups completados en $BACKUP_DIR"
