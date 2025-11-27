#!/bin/bash

echo "=== DIAGNÓSTICO DE CONFIGURACIÓN LLM ==="
echo ""

echo "1. Verificando configuración de modelos..."
docker exec kognito_core python -c "from core.config import settings; print(f'LLM_MODEL: {settings.llm_model}'); print(f'FAST_LLM_MODEL: {settings.fast_llm_model}')" 2>&1

echo ""
echo "2. Verificando API Keys..."
docker exec kognito_core python -c "import os; from core.config import settings; print(f'GOOGLE_API_KEY: {\"Configurada\" if settings.google_api_key else \"NO CONFIGURADA\"}'); print(f'OPENROUTER_API_KEY: {\"Configurada\" if os.getenv(\"OPENROUTER_API_KEY\") else \"NO CONFIGURADA\"}')" 2>&1

echo ""
echo "3. Verificando versiones de LangChain..."
docker exec kognito_core pip show langchain-core langchain-google-genai litellm 2>&1 | grep -E "Name:|Version:"

echo ""
echo "4. Últimos 30 logs del contenedor..."
docker-compose logs core --tail=30 2>&1

echo ""
echo "=== FIN DEL DIAGNÓSTICO ==="
echo ""
echo "Por favor, comparte TODA esta salida para recibir ayuda."
