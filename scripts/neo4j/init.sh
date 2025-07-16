#!/bin/bash

# Script de inicialización inteligente para Neo4j
# Evita el loop infinito de cambio de contraseña

set -e

echo "🚀 Configurando Neo4j para KognitoAI..."

# Verificar si Neo4j ya está corriendo
if pgrep -f "java.*neo4j" > /dev/null; then
    echo "⚠️ Neo4j ya está ejecutándose, deteniendo proceso existente..."
    pkill -f "java.*neo4j" || true
    sleep 2
fi

# Verificar si ya existe configuración de autenticación
if [ -f "/data/dbms/auth" ] && [ -s "/data/dbms/auth" ]; then
    echo "✅ Neo4j ya configurado, iniciando sin cambiar contraseña..."
    # NO establecer NEO4J_AUTH para evitar intentos de cambio
    unset NEO4J_AUTH 2>/dev/null || true
else
    echo "🔧 Primera configuración de Neo4j, estableciendo contraseña..."
    # Solo en la primera ejecución, configurar la contraseña
    if [ -n "$KOGNITO_NEO4J_PASSWORD" ]; then
        export NEO4J_AUTH="neo4j/$KOGNITO_NEO4J_PASSWORD"
        echo "✅ Contraseña configurada para primera ejecución: neo4j/$KOGNITO_NEO4J_PASSWORD"
    else
        export NEO4J_AUTH="neo4j/password"
        echo "✅ Contraseña por defecto configurada: neo4j/password"
    fi
fi

# Configuraciones adicionales
export NEO4J_ACCEPT_LICENSE_AGREEMENT=yes

echo "🚀 Iniciando Neo4j..."

# Buscar el entrypoint correcto
if [ -f "/docker-entrypoint.sh" ]; then
    exec /docker-entrypoint.sh neo4j
elif [ -f "/startup/docker-entrypoint.sh" ]; then
    exec /startup/docker-entrypoint.sh neo4j
elif [ -f "/usr/local/bin/docker-entrypoint.sh" ]; then
    exec /usr/local/bin/docker-entrypoint.sh neo4j
else
    echo "⚠️ No se encontró entrypoint, iniciando Neo4j directamente..."
    exec neo4j console
fi
