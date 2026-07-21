import asyncio
import pytest
from scripts.run_memory_benchmark import run_memory_benchmark


def test_run_memory_benchmark():
    report = asyncio.run(run_memory_benchmark())
    assert report is not None
    assert "temporal_accuracy" in report
    assert "poison_resistance" in report
    assert "episodic_recall" in report
    assert report["overall_score"] >= 0.8
