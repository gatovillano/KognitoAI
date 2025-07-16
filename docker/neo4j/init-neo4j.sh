#!/bin/bash

echo "🚀 Inicializando Neo4j para KognitoAI..."

# Esperar a que Neo4j esté listo
until cypher-shell -u neo4j -p "${NEO4J_AUTH#neo4j/}" "RETURN 1;" > /dev/null 2>&1; do
    echo "⏳ Esperando a que Neo4j esté listo..."
    sleep 2
done

echo "✅ Neo4j está listo!"

# Verificar que APOC está disponible
echo "🔧 Verificando plugins APOC..."
cypher-shell -u neo4j -p "${NEO4J_AUTH#neo4j/}" "CALL apoc.help('apoc') YIELD name RETURN count(name) as apoc_procedures;" || echo "⚠️ APOC no está completamente cargado aún"

echo "🎉 Inicialización de Neo4j completada!"
