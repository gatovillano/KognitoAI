#!/bin/bash

# Script para reiniciar el servicio core con el nuevo archivo .env
# Este script reconstruye el contenedor para que los cambios en .env se apliquen

echo "🔄 Reiniciando el servicio core con el nuevo archivo .env..."

# Detener el servicio core
echo "🛑 Deteniendo el servicio core..."
docker-compose stop core

# Reconstruir el servicio core (esto copiará el nuevo archivo .env)
echo "🔨 Reconstruyendo el servicio core..."
docker-compose build core

# Iniciar el servicio core
echo "▶️ Iniciando el servicio core..."
docker-compose up -d core

# Verificar que el servicio esté corriendo
echo "✅ Verificando que el servicio core esté corriendo..."
docker-compose ps core

echo "🎉 Servicio core reiniciado exitosamente con el nuevo archivo .env"
echo "📝 Los cambios en el modelo LLM deberían estar activos ahora"
