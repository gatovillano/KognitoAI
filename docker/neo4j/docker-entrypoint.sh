#!/bin/bash
set -e

# Eliminar el archivo de bloqueo si existe para evitar conflictos de reinicio
if [ -f "/var/lib/neo4j/run/neo4j.pid" ]; then
    echo "Eliminando archivo de bloqueo PID de Neo4j obsoleto."
    rm -f "/var/lib/neo4j/run/neo4j.pid"
fi

# Lista de posibles ubicaciones para el entrypoint original de Neo4j
declare -a possible_entrypoints=(
    "/docker-entrypoint.sh"
    "/usr/local/bin/docker-entrypoint.sh"
    "/sbin/docker-entrypoint.sh"
)

# Buscar y ejecutar el entrypoint original que sea ejecutable
for entrypoint in "${possible_entrypoints[@]}"; do
    if [ -x "$entrypoint" ]; then
        echo "Entrypoint original encontrado en: $entrypoint"
        exec "$entrypoint" "$@"
    fi
done

# --- Fallback si no se encuentra el script --- 
echo "ADVERTENCIA: No se pudo encontrar el script de entrypoint original de Neo4j en las rutas comunes."
echo "Intentando ejecutar el comando directamente: $@"

# Como último recurso, ejecutar el comando que se pasó al script (ej. "neo4j")
exec "$@"
