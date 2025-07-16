#!/bin/bash

echo "🔧 Solucionando problema de versión de Neo4j..."

# Detener servicios
echo "⏹️ Deteniendo servicios..."
docker compose down

# Eliminar volúmenes de Neo4j
echo "🗑️ Eliminando volúmenes de Neo4j..."
docker volume rm kognito-ai_neo4j_data 2>/dev/null || true
docker volume ls -q | grep neo4j | xargs docker volume rm 2>/dev/null || true

# Eliminar imágenes de Neo4j para forzar descarga fresca
echo "🖼️ Eliminando imágenes de Neo4j..."
docker image rm neo4j:5 neo4j:latest neo4j:5.25-community neo4j:5.15-community 2>/dev/null || true

# Limpiar contenedores
echo "🧹 Limpiando contenedores..."
docker container prune -f

# Verificar que no queden volúmenes de Neo4j
echo "🔍 Verificando limpieza..."
NEO4J_VOLUMES=$(docker volume ls | grep neo4j || true)
if [ -n "$NEO4J_VOLUMES" ]; then
    echo "⚠️ Aún quedan volúmenes de Neo4j:"
    echo "$NEO4J_VOLUMES"
    echo "Eliminándolos manualmente..."
    echo "$NEO4J_VOLUMES" | awk '{print $2}' | xargs docker volume rm 2>/dev/null || true
fi

# Reiniciar solo Neo4j primero
echo "🚀 Iniciando Neo4j..."
docker compose up -d neo4j

# Esperar un momento
echo "⏳ Esperando que Neo4j se inicie..."
sleep 10

# Verificar logs
echo "📋 Verificando logs de Neo4j..."
docker logs kognito_neo4j

# Verificar estado
echo "✅ Verificando estado..."
if docker ps | grep kognito_neo4j | grep -q "Up"; then
    echo "✅ Neo4j está corriendo correctamente!"
    echo "🌐 Accede a: http://localhost:7474"
    echo "👤 Usuario: neo4j"
    echo "🔑 Password: tu_neo4j_password del .env"
else
    echo "❌ Neo4j no está corriendo. Verificando logs..."
    docker logs kognito_neo4j
fi

echo "🎯 Limpieza completada. Si aún hay problemas, revisa los logs arriba."
