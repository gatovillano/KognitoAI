#!/bin/bash

echo "🔧 REPARACIÓN AUTOMÁTICA DE CONFIGURACIÓN LLM"
echo "=============================================="
echo ""

# Backup del .env actual
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup del .env creado"

# Actualizar las variables en el .env
sed -i 's/^LLM_MODEL=.*/LLM_MODEL=gemini\/gemini-1.5-flash/' .env
sed -i 's/^FAST_LLM_MODEL=.*/FAST_LLM_MODEL=gemini\/gemini-1.5-flash/' .env

echo "✅ Variables LLM_MODEL y FAST_LLM_MODEL actualizadas a gemini/gemini-1.5-flash"
echo ""

# Verificar que GOOGLE_API_KEY esté configurada
if grep -q "^GOOGLE_API_KEY=" .env; then
    echo "✅ GOOGLE_API_KEY encontrada en .env"
else
    echo "⚠️  ADVERTENCIA: GOOGLE_API_KEY no encontrada en .env"
fi

echo ""
echo "🔄 Reiniciando contenedor core..."
docker-compose restart core

echo ""
echo "⏳ Esperando 10 segundos para que el servicio inicie..."
sleep 10

echo ""
echo "✅ REPARACIÓN COMPLETADA"
echo ""
echo "Ahora puedes intentar chatear de nuevo en la interfaz web."
echo "Si el problema persiste, ejecuta: docker-compose logs core --tail=50"
