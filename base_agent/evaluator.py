# base_agent/evaluator.py
import time
import os
from typing import Dict, Any

class HiveExecutionEvaluator:
    """Mikro-Evaluator dla modułu Hive (Execution)."""
    
    def __init__(self):
        self.start_time = 0
        self.end_time = 0

    def start_monitoring(self):
        self.start_time = time.time()

    def stop_monitoring(self, exit_code: int, logs: str) -> Dict[str, Any]:
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        # Prosta ocena na podstawie kodu wyjścia i logów
        success = exit_code == 0
        score = 1.0 if success else 0.0
        
        # Szukanie błędów w logach (heurystyka)
        if not success:
            if "MemoryError" in logs: category = "OOM"
            elif "Timeout" in logs: category = "Timeout"
            else: category = "LogicError"
        else:
            category = "Perfect"

        return {
            "score": score,
            "duration": duration,
            "exit_code": exit_code,
            "category": category,
            "efficiency_score": 1.0 / (duration + 1) # Prosta metryka Lean
        }

    def report_to_lab(self, task_id: str, results: Dict[str, Any]):
        print(f"🛠️ Hive Result: Task {task_id} finished with status {results['category']}")
        # Tu zapis do RAE-Lab
