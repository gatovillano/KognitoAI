#!/bin/sh
# ============================================================
# backup.sh — Backup automatico de PostgreSQL + Neo4j
# Ejecutado dentro del contenedor `backup` (postgres:15-alpine)
# Destino: /backups  (bind mount -> disco externo persistente)
# ============================================================
set -u

BACKUP_DIR="/backups"
DATE=$(date +"%Y-%m-%d_%H-%M-%S")
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"; }

mkdir -p "$BACKUP_DIR" || { log "ERROR: no se puede escribir en $BACKUP_DIR"; exit 1; }

# ---------- PostgreSQL ----------
log "Backup de PostgreSQL (${POSTGRES_DB:-kognito_db})..."
if pg_dump -U "$POSTGRES_USER" -h db -Fc -f "$BACKUP_DIR/postgres_${DATE}.dump" 2>/tmp/pgerr.txt; then
    log "  OK: postgres_${DATE}.dump ($(du -h "$BACKUP_DIR/postgres_${DATE}.dump" | cut -f1))"
else
    log "  ERROR pg_dump: $(cat /tmp/pgerr.txt)"
fi

# SQL plano (legible / auditable)
if pg_dump -U "$POSTGRES_USER" -h db > "$BACKUP_DIR/postgres_${DATE}.sql" 2>/dev/null; then
    log "  OK: postgres_${DATE}.sql ($(du -h "$BACKUP_DIR/postgres_${DATE}.sql" | cut -f1))"
else
    log "  ERROR: dump SQL plano fallo"
fi

# Globales (roles) - una sola vez es suficiente pero se refresca
pg_dumpall -U "$POSTGRES_USER" --globals-only > "$BACKUP_DIR/globals_${DATE}.sql" 2>/dev/null \
    && log "  OK: globals_${DATE}.sql"

# ---------- Neo4j ----------
# cypher-shell NO existe en postgres:15-alpine -> se usa un contenedor efimera neo4j
log "Backup de Neo4j..."
if [ -n "${NEO4J_PASSWORD:-}" ]; then
    if docker run --rm --network kognitoai_kognito_network \
        -e NEO4J_PASSWORD="$NEO4J_PASSWORD" \
        -v "$BACKUP_DIR":/backups \
        neo4j:5.15-community sh -c '
            cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -a bolt://neo4j:7687 "CALL dbms.backup()" 2>&1 \
              && echo "NEO4J_BACKUP_OK" \
              || echo "NEO4J_BACKUP_FAIL"
        ' > /tmp/neo4j_out.txt 2>&1; then
        if grep -q "NEO4J_BACKUP_OK" /tmp/neo4j_out.txt; then
            # El dump queda en /data/dump del volumen neo4j -> se copia desde el host (fuera de scope aqui)
            log "  OK: dump Neo4j creado en el volumen kognitoai_neo4j_data"
        else
            log "  WARN: dump Neo4j fallo: $(tr '\n' ' ' < /tmp/neo4j_out.txt | head -c 300)"
        fi
    else
        log "  WARN: no se pudo ejecutar el contenedor neo4j para el dump"
    fi
else
    log "  SKIP: NEO4J_PASSWORD no definido"
fi

# ---------- Rotacion ----------
log "Rotacion (retiene $RETENTION_DAYS dias)..."
find "$BACKUP_DIR" -maxdepth 1 -type f \( -name "postgres_*.dump" -o -name "postgres_*.sql" -o -name "globals_*.sql" \) -mtime "+$RETENTION_DAYS" -delete 2>/dev/null
log "  Ficheros actuales: $(ls -1 "$BACKUP_DIR" 2>/dev/null | wc -l)"

log "Backups completados en $BACKUP_DIR"
exit 0
