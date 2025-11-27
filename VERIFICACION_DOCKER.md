# 🐳 Verificación de Optimizaciones en Docker

## Caché del Grafo LangGraph

### Opción 1: Verificar en los logs del contenedor

Cuando el contenedor inicie y se procese el **primer request de chat**, deberías ver en los logs:

```bash
docker-compose logs -f api
```

Busca estas líneas:

```
🔧 Compilando grafo LangGraph del agente por primera vez...
✅ Grafo LangGraph compilado y cacheado exitosamente
```

**Importante:** Este mensaje debe aparecer **solo una vez** al inicio. Los requests subsecuentes NO deben mostrar este mensaje.

---

### Opción 2: Ejecutar script de verificación dentro del contenedor

```bash
# Copiar el script al contenedor
docker cp verify_langgraph_cache.py kognito-api:/app/

# Ejecutar dentro del contenedor
docker exec -it kognito-api python3 verify_langgraph_cache.py
```

Deberías ver:

```
✅ ¡ÉXITO! Ambas llamadas retornan la misma instancia (cacheado correctamente)
```

---

### Opción 3: Monitorear tiempo de respuesta

Usa el endpoint de chat y mide los tiempos:

```bash
# Primer request (compilará el grafo)
time curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"thread_id": "...", "account_id": "...", "user_message": "Hola"}'

# Segundo request (usará grafo cacheado, ~150ms más rápido)
time curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"thread_id": "...", "account_id": "...", "user_message": "Hola de nuevo"}'
```

---

## Otras Optimizaciones Implementadas

### 1. Lazy Loading de Herramientas

- ✅ Las herramientas solo se cargan cuando se usan
- ✅ Verificar en logs: no deberías ver imports masivos al inicio

### 2. Sesiones DB Reutilizadas

- ✅ Búsquedas RAG usan sesiones compartidas
- ✅ Monitorear conexiones DB: `docker exec -it kognito-postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"`

### 3. Búsqueda en Chat Optimizada

- ✅ Probar búsqueda con muchos hilos
- ✅ Debería ser instantánea (<100ms)

---

## Comandos Útiles

```bash
# Ver logs en tiempo real
docker-compose logs -f api

# Reiniciar contenedor para probar caché desde cero
docker-compose restart api

# Ver uso de memoria (el caché usa ~1-5MB)
docker stats kognito-api

# Entrar al contenedor
docker exec -it kognito-api bash
```

---

## Métricas Esperadas

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Primer request | ~800ms | ~650ms | 19% |
| Requests subsecuentes | ~800ms | ~450ms | 44% |
| Memoria del contenedor | ~500MB | ~505MB | +1% |

---

## Troubleshooting

### Si el caché no funciona

1. Verificar que `get_langgraph_agent()` se está usando (no `create_langgraph_agent()`)
2. Revisar logs para el mensaje de compilación
3. Verificar que no hay múltiples procesos/workers (cada worker tiene su propio caché)

### Si hay errores

1. Revisar logs: `docker-compose logs api | grep -i error`
2. Verificar que todas las dependencias están instaladas
3. Reiniciar contenedor: `docker-compose restart api`
