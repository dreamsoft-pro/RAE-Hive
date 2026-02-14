"""
RAE Hive Auditor.
Main entry point for the agent that verifies results and ensures quality.
"""

import asyncio
import os
import structlog
from base_agent.connector import HiveMindConnector

logger = structlog.get_logger(__name__)

async def auditor_loop():
    connector = HiveMindConnector(agent_role="auditor")
    audit_dir = "/app/to_audit"
    logger.info("auditor_started", status="online", audit_dir=audit_dir)
    
    await connector.log_activity("Auditor online and checking for reviews.")

    while True:
        try:
            # 1. Fetch tasks waiting for review
            reviews = await connector.get_tasks(status="review")

            for task in reviews:
                task_id = task["metadata"].get("task_id")
                # Find the update memory that contains the result filename
                # (Simulated simple search)
                filename = f"{task_id}_result.txt"
                file_path = os.path.join(audit_dir, filename)
                
                logger.info("auditing_task", task_id=task_id, file=filename)

                # 2. Check if file exists and has content
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        content = f.read()
                    
                    if len(content) > 10:
                        # Success
                        await connector.update_task(task["id"], status="done", result="Audit PASSED")
                        await connector.log_activity(f"Audit PASSED for task {task_id}")
                    else:
                        await connector.update_task(task["id"], status="failed", result="File too short")
                        await connector.log_activity(f"Audit FAILED for task {task_id}: Content too short")
                else:
                    await connector.update_task(task["id"], status="failed", result="File not found")
                    await connector.log_activity(f"Audit FAILED for task {task_id}: Result file missing")

        except Exception as e:
            logger.error("auditor_error", error=str(e))
            
        await asyncio.sleep(25)

if __name__ == "__main__":
    asyncio.run(auditor_loop())
