#!/usr/bin/env bash
# scripts/rotate_jwt_secret.sh
# Rotación segura de JWT_SECRET_KEY sin downtime para KognitoAI

set -euo pipefail

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Error: Archivo de entorno $ENV_FILE no encontrado."
  exit 1
fi

echo "🔄 Iniciando rotación de JWT_SECRET_KEY..."

# Generar nueva clave segura
NEW_SECRET=$(openssl rand -hex 32)
CURRENT_SECRET=$(grep -E "^JWT_SECRET_KEY=" "$ENV_FILE" | cut -d '=' -f 2- || true)

if [ -z "$CURRENT_SECRET" ]; then
  echo "⚠️ No se encontró JWT_SECRET_KEY previa. Asignando nueva clave directa..."
  echo "JWT_SECRET_KEY=${NEW_SECRET}" >> "$ENV_FILE"
else
  echo "🔑 Almacenando clave previa en JWT_SECRET_KEY_OLD para compatibilidad de 24h..."
  # Eliminar JWT_SECRET_KEY_OLD previa si existía
  sed -i '/^JWT_SECRET_KEY_OLD=/d' "$ENV_FILE"
  # Mover actual a OLD y actualizar JWT_SECRET_KEY con NEW
  sed -i "s/^JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${NEW_SECRET}\nJWT_SECRET_KEY_OLD=${CURRENT_SECRET}/" "$ENV_FILE"
fi

echo "✅ Clave JWT rotada exitosamente."
echo "ℹ️ Recuerde remover JWT_SECRET_KEY_OLD tras 24 horas."
