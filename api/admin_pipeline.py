# api/admin_pipeline.py

import logging
import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from core.database import Account
from core.dependencies import get_db_session
from api.admin_llm import get_current_admin_account

logger = logging.getLogger(__name__)

router = APIRouter()

# Paths
PIPELINE_REPORTS_DIR = Path(__file__).parent.parent / "skills/user_workspace_KognitoAI/kai_measurement_pipeline/reports"
PIPELINE_SCRIPT = Path(__file__).parent.parent / "skills/user_workspace_KognitoAI/kai_measurement_pipeline/scripts/run_and_save.py"

# Global runner state (in-memory, reset on restart)
runner_state: Dict[str, Any] = {
    "is_running": False,
    "last_run_time": None,
    "error": None,
    "started_at": None,
}


async def execute_pipeline_task():
    global runner_state
    runner_state["is_running"] = True
    runner_state["error"] = None
    runner_state["started_at"] = datetime.now().isoformat()

    # Pass current environment vars so the script gets INTERNAL_API_KEY_FOR_BOT etc.
    env = os.environ.copy()

    try:
        logger.info(f"Starting real KAI measurement pipeline: {PIPELINE_SCRIPT}")
        process = await asyncio.create_subprocess_exec(
            "python3", str(PIPELINE_SCRIPT),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=str(PIPELINE_SCRIPT.parent),
        )

        # Wait up to 10 minutes (real LLM queries can take a while)
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600
            )
        except asyncio.TimeoutError:
            process.kill()
            runner_state["error"] = "Pipeline timeout (>10 min). Revisa que el backend esté respondiendo."
            logger.error("Pipeline execution timed out after 10 minutes")
            return

        stdout_text = stdout.decode("utf-8", errors="ignore")
        stderr_text = stderr.decode("utf-8", errors="ignore")

        if process.returncode != 0:
            error_msg = stderr_text[:500] if stderr_text else f"exit code {process.returncode}"
            logger.error(f"Pipeline failed: {error_msg}")
            runner_state["error"] = error_msg
        else:
            logger.info(f"Pipeline completed successfully:\n{stdout_text[-800:]}")
            runner_state["last_run_time"] = datetime.now().isoformat()

    except Exception as e:
        logger.error(f"Error executing pipeline: {e}", exc_info=True)
        runner_state["error"] = str(e)
    finally:
        runner_state["is_running"] = False


@router.get(
    "/admin/pipeline/results",
    summary="Obtener resultados del pipeline de medición (solo admin)"
)
async def get_pipeline_results(
    admin_account: Account = Depends(get_current_admin_account)
):
    """
    Devuelve el JSON más reciente + historial de hasta 10 ejecuciones + estado del runner.
    """
    try:
        PIPELINE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        latest_metrics = None
        latest_file = PIPELINE_REPORTS_DIR / "metrics.json"

        if latest_file.exists():
            try:
                with open(latest_file, "r", encoding="utf-8") as f:
                    latest_metrics = json.load(f)
            except Exception as e:
                logger.error(f"Error loading metrics.json: {e}")

        # Load history
        history = []
        files = sorted(
            PIPELINE_REPORTS_DIR.glob("metrics_*.json"),
            key=os.path.getmtime,
            reverse=True
        )
        for file in files[:10]:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    history.append({
                        "filename": file.name,
                        "timestamp": data.get("timestamp"),
                        "metrics": data.get("metrics"),
                        "summary": data.get("summary"),
                        "execution_time_seconds": data.get("execution_time_seconds"),
                        "is_real": data.get("is_real", False),
                    })
            except Exception as e:
                logger.error(f"Error loading history file {file.name}: {e}")

        return {
            "latest": latest_metrics,
            "history": history,
            "status": {
                "is_running": runner_state["is_running"],
                "last_run_time": runner_state["last_run_time"],
                "started_at": runner_state["started_at"],
                "error": runner_state["error"],
            }
        }
    except Exception as e:
        logger.error(f"Error retrieving pipeline results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/admin/pipeline/run",
    summary="Ejecutar el pipeline de medición REAL (solo admin)"
)
async def run_pipeline(
    background_tasks: BackgroundTasks,
    admin_account: Account = Depends(get_current_admin_account)
):
    """
    Inicia el pipeline de medición real en segundo plano.
    El pipeline envía queries reales al LLM y puede tardar 1-5 minutos.
    """
    if runner_state["is_running"]:
        started = runner_state.get("started_at", "desconocido")
        return {
            "message": f"El pipeline ya se está ejecutando (iniciado: {started}).",
            "is_running": True
        }

    if not PIPELINE_SCRIPT.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Script del pipeline no encontrado: {PIPELINE_SCRIPT}"
        )

    background_tasks.add_task(execute_pipeline_task)
    return {
        "message": (
            "Pipeline de medición REAL iniciado. "
            "Envía queries reales al LLM — puede tardar 1-5 minutos. "
            "Recarga los resultados en un momento."
        ),
        "is_running": True,
        "total_queries": 13,  # 5 hallucination + 5 recall + 3 tool
    }
