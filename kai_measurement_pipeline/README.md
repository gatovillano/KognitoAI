# KAI Measurement Pipeline

Pipeline de medición de rendimiento y monitoreo del sistema KAI.

## 📋 Propósito

- Medir tiempos de respuesta de endpoints críticos
- Verificar disponibilidad de la API
- Generar reportes de rendimiento
- Monitorear métricas del sistema

## 🚀 Uso

```bash
# Ejecutar pipeline completo
./run.sh

# O directamente con Python
python3 scripts/run_measurements.py

# Generar reporte HTML
python3 generate_report.py
```

## 📊 Métricas Recolectadas

| Métrica | Descripción |
|---------|-------------|
| Health Check | Disponibilidad de la API |
| Response Time | Tiempo de respuesta de endpoints |
| Chat Test | Prueba de generación de texto |
| System Metrics | Métricas del sistema |

## 📁 Estructura

```
kai_measurement_pipeline/
├── run.sh                    # Script principal
├── generate_report.py        # Genera reporte HTML
├── scripts/
│   └── run_measurements.py   # Mediciones principales
└── reports/                  # Resultados (generados)
    ├── measurement_*.json    # Datos crudos
    └── report.html           # Reporte visual
```

## ⚙️ Configuración

- `KAI_API_BASE`: URL de la API (default: http://localhost:8889)

## 📅 Fecha

Generado: 19 de mayo de 2026
