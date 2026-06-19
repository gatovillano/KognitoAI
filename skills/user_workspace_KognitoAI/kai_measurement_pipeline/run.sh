#!/bin/bash
# KAI Measurement Pipeline Runner

echo "🚀 Starting KAI Measurement Pipeline..."
echo "========================================"

cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "/tmp/kai_measurement_venv" ]; then
    echo "📦 Setting up environment..."
    python3 -m venv /tmp/kai_measurement_venv
fi

source /tmp/kai_measurement_venv/bin/activate 2>/dev/null || true
pip install aiohttp -q

# Run pipeline
echo ""
python3 scripts/run_measurements.py

echo ""
echo "✅ Pipeline completed!"
