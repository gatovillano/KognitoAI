#!/bin/bash
# Script robusto para instalar dependencias de Python con múltiples reintentos

set -e

echo "🔧 Configurando pip para mayor estabilidad..."

# Configurar pip con múltiples mirrors y configuraciones robustas
pip config set global.timeout 300
pip config set global.retries 5
pip config set global.trusted-host "$TRUSTED_HOSTS"

# Lista de mirrors de PyPI para probar (ordenados por estabilidad)
MIRRORS=(
    "https://pypi.douban.com/simple/"
    "https://mirrors.aliyun.com/pypi/simple/"
    "https://pypi.tuna.tsinghua.edu.cn/simple/"
    "https://mirrors.cloud.tencent.com/pypi/simple/"
    "https://pypi.org/simple/"
    "https://pypi.python.org/simple/"
)

# Configurar trusted hosts para todos los mirrors
TRUSTED_HOSTS="pypi.douban.com mirrors.aliyun.com pypi.tuna.tsinghua.edu.cn mirrors.cloud.tencent.com pypi.org pypi.python.org files.pythonhosted.org"

# Función para instalar paquetes individualmente
install_individual_packages() {
    local requirements_file=$1
    echo "🔧 Instalando paquetes individualmente desde $requirements_file"

    while IFS= read -r line; do
        # Saltar líneas vacías y comentarios
        if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi

        # Extraer nombre del paquete (antes de ==, >=, etc.)
        package=$(echo "$line" | sed 's/[>=<].*//' | sed 's/\[.*\]//')

        echo "📦 Instalando: $package"

        for mirror in "${MIRRORS[@]}"; do
            pip config set global.index-url "$mirror"

            if pip install --no-cache-dir \
                --timeout 300 \
                --retries 5 \
                --disable-pip-version-check \
                "$line"; then
                echo "✅ $package instalado exitosamente"
                break
            else
                echo "❌ Falló con $mirror, probando siguiente..."
            fi
        done
    done < "$requirements_file"
}

# Función para instalar con reintentos
install_with_retries() {
    local requirements_file=$1
    local max_attempts=2

    for mirror in "${MIRRORS[@]}"; do
        echo "🌐 Intentando con mirror: $mirror"
        pip config set global.index-url "$mirror"

        for attempt in $(seq 1 $max_attempts); do
            echo "📦 Intento $attempt/$max_attempts para $requirements_file"

            if pip install --no-cache-dir \
                --timeout 180 \
                --retries 3 \
                --default-timeout 180 \
                --disable-pip-version-check \
                -r "$requirements_file"; then
                echo "✅ Instalación exitosa con $mirror"
                return 0
            else
                echo "❌ Intento $attempt falló"
                if [ $attempt -lt $max_attempts ]; then
                    echo "⏳ Esperando 15 segundos antes del siguiente intento..."
                    sleep 15
                fi
            fi
        done

        echo "⚠️ Todos los intentos fallaron con $mirror, probando siguiente mirror..."
    done

    echo "⚠️ Instalación masiva falló, intentando instalación individual..."
    install_individual_packages "$requirements_file"
}

echo "🚀 Actualizando pip..."
pip install --upgrade pip

echo "🔨 Instalando dependencias de compilación..."
install_with_retries "requirements-build.txt"

echo "📚 Instalando dependencias principales..."
install_with_retries "requirements.txt"

echo "🎉 ¡Todas las dependencias instaladas exitosamente!"
