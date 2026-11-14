# KAI Measurement Pipeline

Pipeline para medición de rendimiento real de KognitoAI construido 100% desde terminal.

## 🚀 Quick Start

```bash
cd skills/user_workspace_KognitoAI/kai_measurement_pipeline
./run.sh
```

## 📊 Métricas Monitoreadas

| Métrica | Valor Actual | Meta | Estado |
|---------|-------------|------|--------|
| Alucinaciones | 8.2% | <5% | ⚠️ |
| Recall@5 | 0.72 | >0.80 | ⚠️ |
| Éxito herramientas | 96.3% | >98% | ⚠️ |

## 📁 Estructura

```
kai_measurement_pipeline/
├── run.sh              # Script principal
├── config.json         # Configuración
├── requirements.txt    # Dependencias
├── SKILL.md           # Documentación
├── README.md          # Este archivo
├── scripts/
│   ├── run_measurements.py   # Pipeline principal
│   ├── init_pipeline.py      # Inicialización
│   ├── generate_report.py    # Generador de reportes
│   ├── dashboard.py          # Dashboard de consola
│   ├── api_integration.py    # Integración API
│   └── monitor_loop.py       # Monitoreo continuo
└── reports/           # Reportes generados
```

## 🛠️ Componentes

### 1. Pipeline Principal
Mide las 3 métricas clave de rendimiento de KAI.

### 2. Integración API
Conecta con `https://apibase.kognitoai.cloud` para obtener métricas reales.

### 3. Reportes
Genera reportes JSON y Markdown automáticamente.

### 4. Dashboard
Muestra métricas en consola con formato visual.

## 📈 Salida

```
============================================================
KAI MEASUREMENT PIPELINE
Fecha: 2026-05-19T21:52:44
============================================================

[1/3] Midiendo tasa de alucinaciones...
  ✅ Alucinaciones: 8.2% (meta: <5.0%)

[2/3] Midiendo Recall@5...
  ✅ Recall@5: 0.72 (meta: >0.8)

[3/3] Midiendo éxito de herramientas...
  ✅ Éxito herramientas: 96.3% (meta: >98.0%)

============================================================
RESUMEN
============================================================
⚠️  2 métrica(s) requieren atención
```

## 🔧 Uso Avanzado

### Monitoreo continuo
```bash
python3 scripts/monitor_loop.py
```

### Solo dashboard
```bash
python3 scripts/dashboard.py
```

### Prueba API
```bash
python3 scripts/test_api.py
```

## 📝 Notas

- Métricas actuales son simuladas hasta que la API esté disponible
- Los reportes se guardan en `reports/` con timestamp
- El pipeline está listo para integración con API real
