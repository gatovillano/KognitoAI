#!/usr/bin/env python3
"""
Script para pre-descargar solo los modelos pequeños necesarios durante el build de Docker.
Evita descargas grandes y problemas de timeout.
"""

import os
import sys
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_spacy_small():
    """Descarga modelo pequeño de spaCy para español."""
    try:
        import spacy
        from spacy.cli import download

        # Usar modelo en español (pequeño)
        model_name = "es_core_news_sm"  # ~15MB, español
        logger.info(f"📥 Descargando spaCy modelo pequeño (español): {model_name}")

        try:
            # Intentar cargar primero
            spacy.load(model_name)
            logger.info(f"✅ {model_name} ya está disponible")
        except OSError:
            # Si no existe, descargarlo
            download(model_name)
            logger.info(f"✅ {model_name} descargado correctamente")

    except Exception as e:
        logger.warning(f"⚠️ Error descargando spaCy español: {e}")
        return False
    return True

def download_sentence_transformer_small():
    """Descarga modelo pequeño de SentenceTransformers multilingüe."""
    try:
        from sentence_transformers import SentenceTransformer

        # Usar modelo multilingüe pequeño que funciona bien con español
        model_name = "paraphrase-multilingual-MiniLM-L12-v2"  # ~420MB pero multilingüe
        cache_dir = "/app/.cache/sentence_transformers"

        logger.info(f"📥 Descargando SentenceTransformer multilingüe: {model_name}")

        # Crear directorio de cache
        os.makedirs(cache_dir, exist_ok=True)

        # Descargar modelo
        model = SentenceTransformer(
            model_name,
            cache_folder=cache_dir,
            device='cpu'
        )

        # Verificar que funciona con español
        test_embedding = model.encode("Esta es una oración de prueba en español")
        logger.info(f"✅ {model_name} descargado y verificado con español (tamaño embedding: {len(test_embedding)})")

    except Exception as e:
        logger.warning(f"⚠️ Error descargando SentenceTransformers multilingüe: {e}")
        return False
    return True

def main():
    """Función principal."""
    logger.info("🚀 Iniciando descarga de modelos pequeños...")
    
    success_count = 0
    total_models = 2
    
    # Descargar spaCy
    if download_spacy_small():
        success_count += 1
    
    # Descargar SentenceTransformers
    if download_sentence_transformer_small():
        success_count += 1
    
    # Resumen
    logger.info(f"📊 Descarga completada: {success_count}/{total_models} modelos")
    
    if success_count == total_models:
        logger.info("✅ Todos los modelos descargados correctamente")
        return 0
    else:
        logger.warning("⚠️ Algunos modelos fallaron, pero el contenedor puede continuar")
        return 0  # No fallar el build por esto

if __name__ == "__main__":
    sys.exit(main())
