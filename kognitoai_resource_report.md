# 📊 Informe de Gasto de Recursos - KognitoAI

## 🖥️ **Estado del Sistema**

| Recurso | Total | Usado | Disponible | % Uso | Estado |
|---------|-------|-------|------------|-------|--------|
| **RAM** | 62.0 GB | 46.0 GB | 16.0 GB | **74%** | ⚠️ Moderado |
| **Swap** | 18.0 GB | 16.0 GB | 2.5 GB | **89%** | 🔴 CRÍTICO |
| **Disco** | 295 GB | 280 GB | 273 MB | **100%** | 🔴 CRÍTICO |

---

## 🐳 **Gasto de Recursos - Contenedores Docker**

| Contenedor | CPU % | RAM Usada | % RAM | I/O Disco | Estado |
|------------|-------|-----------|-------|-----------|--------|
| **kognito_neo4j** | 0.45% | 1.643 GiB | 2.62% | 9.58 GB / 5.99 GB | ✅ Activo |
| **kognito_db** | 0.00% | 168.2 MiB | 0.26% | 7.51 GB / 896 MB | ✅ Activo |
| **kognito_redis** | 0.12% | 1.172 MiB | 0.00% | 259 MB / 2.14 MB | ✅ Activo |
| **kokoro-tts** | 0.13% | 20.3 MiB | 0.03% | 1.09 GB / 255 MB | 🔴 Unhealthy |

---

## 💻 **Gasto de Recursos - Procesos Locales (start_local.sh)**

| Proceso | PID | CPU % | RAM Usada | % RAM | Función |
|---------|-----|-------|-----------|-------|---------|
| **Backend (run_api.py)** | 2988524 | 3.3% | 2.40 GiB | 3.7% | API FastAPI |
| **Telegram Gateway** | 2988526 | 0.6% | 827 MiB | 1.2% | Bot de Telegram |
| **Frontend (Next.js)** | 2988555 | 2.1% | 821 MiB | 1.2% | Dashboard Next.js |

---

## 📈 **Resumen Total de KognitoAI**

| Métrica | Docker | Locales | **Total KognitoAI** |
|---------|--------|---------|---------------------|
| **RAM** | 1.83 GiB | 4.05 GiB | **5.88 GiB** |
| **CPU** | 0.7% | 6.0% | **6.7%** |
| **Disco** | 18.2 GB | ~1 GB | **~19.2 GB** |

---

## 📊 **Desglose por Componente**

```
KognitoAI Resource Usage (Total: 5.88 GiB RAM, 6.7% CPU)
├── LOCAL - Backend (run_api.py)
│   ├── RAM: 2.40 GiB (41% del total)
│   ├── CPU: 3.3%
│   └── Puerto: 8889
│
├── DOCKER - Neo4j
│   ├── RAM: 1.64 GiB (28% del total)
│   ├── CPU: 0.45%
│   └── Disco: 9.58 GB
│
├── LOCAL - Frontend (Next.js)
│   ├── RAM: 821 MiB (14% del total)
│   ├── CPU: 2.1%
│   └── Puerto: 3002
│
├── LOCAL - Telegram Gateway
│   ├── RAM: 827 MiB (14% del total)
│   ├── CPU: 0.6%
│   └── Puerto: 9091
│
├── DOCKER - PostgreSQL
│   ├── RAM: 168 MiB (3% del total)
│   ├── CPU: 0.00%
│   └── Disco: 7.51 GB
│
└── DOCKER - Kokoro-TTS
    ├── RAM: 20 MiB (0.3% del total)
    └── Estado: ❌ unhealthy
```

---

## ⚠️ **Problemas Identificados**

1. **🔴 Kokoro-TTS unhealthy** - Servicio de síntesis de voz con problemas
2. **⚠️ Alto consumo del backend** - 2.40 GiB RAM (41% del total de KognitoAI)
3. **⚠️ Alto consumo del frontend** - 821 MiB RAM
4. **🔴 Disco 100% lleno** - El sistema no tiene espacio para operar correctamente
5. **🔴 Alto uso de swap** - El sistema está usando memoria de intercambio intensamente

---

## 🚨 **Acciones Recomendadas**

### Prioridad: 🔴 CRÍTICA
1. **Liberar espacio en disco**
   ```bash
   docker container prune -f
   docker image prune -f
   docker volume prune -f
   ```

### Prioridad: ⚠️ ALTA
2. **Verificar estado de kokoro-tts**
   ```bash
   docker logs kokoro-tts
   ```

3. **Revisar logs del backend**
   ```bash
   tail -f logs/backend.log
   ```

### Prioridad: ℹ️ MEDIA
4. **Optimizar consumo de memoria**
   - El backend local consume 2.40 GiB RAM
   - Considerar ajustar límites de memoria

---

## 📈 **Comparación con Sistema Completo**

| Componente | RAM | % del Sistema |
|------------|-----|---------------|
| **KognitoAI (total)** | **5.88 GiB** | **~10% del sistema** |
| Sistema completo | 62.0 GiB | 100% |
| Otros proyectos | ~56 GiB | ~90% |

---

## 📅 **Fecha del Reporte**

**Generado:** $(date)

**Máquina:** $(hostname)

**Usuario:** $(whoami)

---

## 📋 **Comandos Útiles**

```bash
# Ver todos los contenedores
docker ps

# Ver recursos de KognitoAI
docker stats --no-stream | grep kognito

# Ver procesos locales
ps aux | grep -E "run_api|run_telegram|next"

# Ver logs locales
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/telegram_gateway.log

# Ver uso del sistema
free -h
df -h /
```