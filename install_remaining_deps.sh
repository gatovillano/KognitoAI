#!/bin/bash
# Script para instalar las dependencias restantes de forma progresiva

echo "🚀 Instalando dependencias restantes de forma progresiva..."

# Función para instalar con reintentos
install_group() {
    local group_name=$1
    shift
    local packages=("$@")
    
    echo "📦 Instalando grupo: $group_name"
    for package in "${packages[@]}"; do
        echo "  - Instalando: $package"
        if pip install --no-cache-dir "$package"; then
            echo "    ✅ $package instalado exitosamente"
        else
            echo "    ❌ Error instalando $package, continuando..."
        fi
    done
    echo ""
}

# Grupo 1: Dependencias de datos y análisis
install_group "Análisis de datos" \
    "numpy" \
    "pandas" \
    "scikit-learn" \
    "matplotlib" \
    "seaborn"

# Grupo 2: Dependencias de IA/ML
install_group "Machine Learning" \
    "torch" \
    "transformers" \
    "sentence-transformers" \
    "chromadb"

# Grupo 3: Dependencias de procesamiento de texto
install_group "Procesamiento de texto" \
    "spacy" \
    "nltk" \
    "textstat" \
    "python-docx"

# Grupo 4: Dependencias de web y APIs
install_group "Web y APIs" \
    "requests" \
    "beautifulsoup4" \
    "selenium" \
    "playwright"

# Grupo 5: Dependencias de bases de datos
install_group "Bases de datos" \
    "redis" \
    "pymongo" \
    "elasticsearch"

# Grupo 6: Dependencias de desarrollo
install_group "Desarrollo" \
    "pytest" \
    "black" \
    "flake8" \
    "mypy"

echo "🎉 Instalación progresiva completada!"
echo "📋 Para ver qué paquetes se instalaron exitosamente:"
echo "   pip list"
