from core.logging_config import scheduler_logger
import httpx
import traceback
from typing import Optional, Dict, Any


def run_scheduled_task(func_name: str):
    if func_name == "scheduler":
        scheduler_worker()
    else:
        raise ValueError(f"Unknown function name: {func_name}")


def scheduler_worker():
    try:
        scheduler_logger.info("Menjalankan scheduler_worker...")
    except Exception as e:
        scheduler_logger.info(f"Error dalam scheduler_worker: {e}")
        traceback.print_exc()