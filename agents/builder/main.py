"""
RAE Hive Builder (Autonomous Coder).
Executes coding tasks by using RAE as context and memory.
"""

import asyncio
import os
import structlog
from base_agent.connector import HiveMindConnector

logger = structlog.get_logger(__name__)

async def builder_loop():
    connector = HiveMindConnector(agent_role="builder")
    logger.info("builder_started", status="online")
    
    await connector.log_activity("Builder ready to improve codebase.")

    while True:
        try:
            # 1. Fetch assigned tasks
            tasks = await connector.get_tasks(status="pending")

            for task in tasks:
                task_id = task["metadata"].get("task_id")
                objective = task["content"]
                logger.info("executing_coding_task", task_id=task_id, objective=objective)
                
                await connector.update_task(task["id"], status="in_progress")
                await connector.log_activity(f"Working on: {objective}")

                # 1. Fetch evidence for this task (L2 Directives)
                evidence_resp = await connector.query_memories(
                    query=f"related_task_id:{task_id}",
                    project="RAE-Hive",
                    layers=["working", "semantic"],
                    tags=["evidence_injection"]
                )
                evidence_context = ""
                if evidence_resp and evidence_resp.get("results"):
                    evidence_context = "\n### CRITICAL EVIDENCE (Legacy Source & Directives):\n"
                    for res in evidence_resp["results"]:
                        evidence_context += f"- {res.get('content')}\n"

                # 2. Use RAE to "think" about the implementation
                thought_prompt = f"""
                Objective: {objective}
                {evidence_context}
                
                Instructions:
                1. Use the CRITICAL EVIDENCE provided above (Legacy Source).
                2. DO NOT create more plans. Write the full TypeScript code NOW.
                3. Follow the contract strictly.
                """
                
                plan = await connector.think(thought_prompt)
                
                # 3. Apply changes (Simulated for safety, but can be real FS write)
                # For now, we write to a result file, but the infrastructure allows writing to /app/src
                result_filename = f"implementation_{task_id}.py"
                with open(os.path.join("/app/work_dir", result_filename), "w") as f:
                    f.write(plan)
                
                await connector.update_task(task["id"], status="review", result=result_filename)
                await connector.log_activity(f"Proposed implementation for {task_id} ready for audit.")

        except Exception as e:
            logger.error("builder_error", error=str(e))
            
        await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(builder_loop())
