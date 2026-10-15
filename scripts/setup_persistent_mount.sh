#!/usr/bin/env bash
set -e

# Comprobar privilegios de root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Por favor, ejecuta este script con sudo: sudo bash $0"
  exit 1
fi

UUID="DCEE2811EE27E30E"
MOUNT_POINT="/mnt/Almacenamiento"
LEGACY_LINK_DIR="/run/media/gato"
LEGACY_LINK="/run/media/gato/Almacenamiento"

echo "=== Configurando montaje persistente para Almacenamiento ($UUID) ==="

# 1. Crear punto de montaje fijo
mkdir -p "$MOUNT_POINT"
echo "✅ Directorio $MOUNT_POINT preparado."

# 2. Configurar /etc/fstab si no está presente
FSTAB_ENTRY="UUID=$UUID $MOUNT_POINT ntfs3 defaults,uid=1000,gid=1000,nofail,x-systemd.device-timeout=10 0 0"

if grep -q "$UUID" /etc/fstab; then
    echo "ℹ️  La entrada con UUID $UUID ya existe en /etc/fstab."
else
    echo "Agregando entrada a /etc/fstab..."
    echo "" >> /etc/fstab
    echo "# Disco Almacenamiento (Base de datos KognitoAI)" >> /etc/fstab
    echo "$FSTAB_ENTRY" >> /etc/fstab
    echo "✅ /etc/fstab actualizado exitosamente."
fi

# 3. Crear regla en tmpfiles.d para garantizar el enlace en /run/media/gato/Almacenamiento en cada arranque
mkdir -p /etc/tmpfiles.d
cat << 'TMPCONF' > /etc/tmpfiles.d/almacenamiento.conf
d /run/media 0755 root root -
d /run/media/gato 0755 gato gato -
L+ /run/media/gato/Almacenamiento - - - - /mnt/Almacenamiento
TMPCONF
echo "✅ Regla /etc/tmpfiles.d/almacenamiento.conf creada."

# 4. Detener temporalmente kognito_db para cambiar el montaje limpiamente
echo "Verificando si kognito_db está corriendo..."
if docker ps -q --filter "name=kognito_db" | grep -q .; then
    echo "Deteniendo kognito_db brevemente..."
    docker stop kognito_db || true
fi

# 5. Si actualmente está montado en /run/media/gato/Almacenamiento, desmontarlo y montarlo en /mnt/Almacenamiento
if mountpoint -q /run/media/gato/Almacenamiento; then
    echo "Desmontando de la ruta temporal..."
    umount /run/media/gato/Almacenamiento || true
fi

# Montar según fstab
echo "Montando $MOUNT_POINT desde fstab..."
systemctl daemon-reload
mount -a

# Asegurar symlink actual
mkdir -p "$LEGACY_LINK_DIR"
ln -sfn "$MOUNT_POINT" "$LEGACY_LINK"

# 6. Levantar kognito_db
echo "Reiniciando kognito_db..."
docker start kognito_db || true

echo ""
echo "=== Verificación ==="
findmnt "$MOUNT_POINT" || echo "⚠️  Revisa el montaje"
ls -la "$LEGACY_LINK" || true

echo ""
echo "🎉 ¡Configuración completada con éxito! El disco ahora se montará automáticamente antes de los servicios al encender la PC."
