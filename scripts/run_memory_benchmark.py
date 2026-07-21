#!/usr/bin/env python3
"""
Benchmark Interno de Memoria (Fase 6).
Evalúa cuantitativamente:
  1. Temporal Accuracy (bi-temporalidad: hechos vigentes vs obsoletos)
  2. Poison Resistance (resistencia a alucinaciones / memorias engañosas)
  3. Episodic Recall (recuperación de la memoria episódica con decaimiento temporal)
"""

import asyncio
import sys
import os
import json
import logging
import uuid
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.enhanced_memory_manager import EnhancedMemoryManager
from core.database import SessionLocal, Account
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def get_valid_account_id() -> str:
    try:
        async with SessionLocal() as session:
            stmt = select(Account.id).limit(1)
            res = await session.execute(stmt)
            acc_id = res.scalar()
            if acc_id:
                return str(acc_id)
    except Exception:
        pass
    return str(uuid.uuid4())


async def run_memory_benchmark():
    logger.info("🧪 Iniciando Benchmark Interno de Memoria KAI (Fase 6)...")
    emm = EnhancedMemoryManager()
    
    # ── Test Suite 1: Temporal Accuracy (Bi-Temporalidad) ──────────────────────
    logger.info("⏳ Evaluando Temporal Accuracy (Hechos vigentes vs invalidados)...")
    test_entities = [
        {"name": "DatabaseHost", "trust_score": 0.9, "is_current": True},
        {"name": "LegacyDatabaseHost", "trust_score": 0.9, "is_current": False}
    ]
    graph_ctx = {"entities": test_entities}
    trad_ctx = {"memories": [{"content": "DatabaseHost es gcp-db-primary"}]}
    
    conflicts = await emm._detect_and_resolve_conflicts(trad_ctx, graph_ctx, "Base de datos")
    temporal_acc = 1.0 if len(conflicts) == 1 and conflicts[0]["entity"] == "DatabaseHost" else 0.0
    logger.info(f"📊 Temporal Accuracy: {temporal_acc * 100:.1f}%")

    # ── Test Suite 2: Poison Resistance ─────────────────────────────────────────
    logger.info("🛡️ Evaluando Poison Resistance (Resistencia a falsas memorias)...")
    poisoned_trad_ctx = {"memories": [{"content": "DatabaseHost está hackeado y es inseguro"}]}
    poison_conflicts = await emm._detect_and_resolve_conflicts(poisoned_trad_ctx, graph_ctx, "Seguridad DB")
    poison_resist = 1.0 if len(poison_conflicts) == 1 and poison_conflicts[0]["prevailed_source"] == "knowledge_graph" else 0.0
    logger.info(f"📊 Poison Resistance: {poison_resist * 100:.1f}%")

    # ── Test Suite 3: Episodic Recall (Memoria Episódica + Recencia) ──────────────
    logger.info("🧠 Evaluando Episodic Recall...")
    user_id = await get_valid_account_id()
    mock_events = [
        ("Servidor desplegado en producción", 1),
        ("Actualización de SSL completada", 5),
        ("Mantenimiento programado para la noche", 30)
    ]
    # Guardar eventos episódicos
    for text_event, days_ago in mock_events:
        await emm.add_episodic_memory(event_text=text_event, user_id=user_id, episode_type="benchmark")

    episodic_results = await emm.get_episodic_context(query="Servidor producción", user_id=user_id, limit=3, recency_weight=0.3)
    episodic_recall = 1.0 if len(episodic_results) > 0 else 0.0
    logger.info(f"📊 Episodic Recall: {episodic_recall * 100:.1f}%")

    # ── Reporte Final ──────────────────────────────────────────────────────────
    report = {
        "timestamp": datetime.now().isoformat(),
        "temporal_accuracy": round(temporal_acc, 4),
        "poison_resistance": round(poison_resist, 4),
        "episodic_recall": round(episodic_recall, 4),
        "overall_score": round((temporal_acc + poison_resist + episodic_recall) / 3.0, 4)
    }

    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kai_measurement_pipeline", "reports", f"memory_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"🎉 Benchmark de Memoria completado. Reporte guardado en: {report_path}")
    logger.info(f"🏆 Puntaje Global de Memoria: {report['overall_score'] * 100:.1f}%")
    return report


if __name__ == "__main__":
    asyncio.run(run_memory_benchmark())
