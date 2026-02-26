"""
RAE Hive Auditor (Smart Version).
Uses LLM to verify code against contracts, ISO 27001, and logical parity.
"""

import asyncio
import os
import structlog
from base_agent.connector import HiveMindConnector

logger = structlog.get_logger(__name__)

async def auditor_loop():
    connector = HiveMindConnector(agent_role="auditor")
    logger.info("auditor_started", status="online")
    await connector.log_activity("Smart Auditor online. Performing LLM-based code reviews.")

    while True:
        try:
            # 1. Fetch tasks waiting for review
            reviews = await connector.get_tasks(status="review")

            for task in reviews:
                task_id = task["metadata"].get("task_id", task["id"])
                result_filename = task["metadata"].get("result", "OperationService.ts")
                file_path = os.path.join("/app/work_dir", result_filename)
                
                logger.info("auditing_task", task_id=task_id, file=result_filename)

                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        code_content = f.read()
                    
                    # LLM Audit Prompt
                    audit_prompt = f"""
                    You are the L1 Auditor. Review the following code implementation for task {task_id}.
                    
                    CODE TO REVIEW:
                    ```typescript
                    {code_content}
                    ```
                    
                    REQUIREMENTS:
                    1. Does it strictly follow TypeScript typings (no 'any')?
                    2. Does it comply with ISO 27001 (e.g., error sanitization, no exposed secrets)?
                    3. Does it solve the objective completely without placeholders like "// To be implemented"?
                    
                    Respond ONLY with "PASSED" if it is perfect. 
                    If there are ANY issues, respond with "REJECTED" followed by a detailed, bulleted list of what must be fixed.
                    """
                    
                    audit_result = await connector.think(audit_prompt)
                    
                    if audit_result.strip().startswith("PASSED"):
                        await connector.update_task(task["id"], status="done", result="Audit PASSED by LLM")
                        await connector.log_activity(f"Audit PASSED for task {task_id}")
                    else:
                        # CRITICAL: This exact format triggers the Semantic Watchdog
                        rejection_reason = audit_result.replace("REJECTED", "").strip()
                        await connector.update_task(task["id"], status="in_progress", result="Audit FAILED")
                        
                        # Log to episodic for Watchdog to count
                        await connector.add_memory(
                            content=f"Audit failed for {task_id}. Reason: {rejection_reason}",
                            layer="episodic",
                            tags=["hive_log", "auditor", "audit_rejection"],
                            metadata={"task_id": task_id}
                        )
                        logger.warning("audit_rejected", task_id=task_id)
                else:
                    await connector.update_task(task["id"], status="in_progress", result="File not found")
                    logger.error("audit_file_missing", file=file_path)

        except Exception as e:
            logger.error("auditor_error", error=str(e))
            
        await asyncio.sleep(25)

if __name__ == "__main__":
    asyncio.run(auditor_loop())
