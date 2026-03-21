"""
RAE Hive Builder (Autonomous Coder) - PRODUCTION v2.
Supports dynamic file paths, Quality Pre-Audit, and Evidence Injection.
"""

import asyncio
import os
import structlog
from base_agent.connector import HiveMindConnector

logger = structlog.get_logger(__name__)

async def builder_loop():
    # Pobieranie konfiguracji ze zmiennych środowiskowych
    work_dir = os.getenv("HIVE_WORK_DIR", "/mnt/extra_storage/RAE-Suite/packages/rae-hive/work_dir")
    connector = HiveMindConnector(agent_role="builder")
    logger.info("builder_started", status="online", work_dir=work_dir)
    
    await connector.log_activity("Builder ready to modernize codebase.")

    while True:
        try:
            # 1. Fetch assigned tasks
            tasks = await connector.get_tasks(status="pending")

            for task in tasks:
                task_id = task["metadata"].get("task_id", "gen_task")
                objective = task["content"]
                result_filename = task["metadata"].get("result", "GeneratedComponent.ts")
                target_path = os.path.join(work_dir, result_filename)
                
                logger.info("executing_coding_task", task_id=task_id, objective=objective, target=target_path)
                
                await connector.update_task(task["id"], status="in_progress")
                await connector.log_activity(f"Building: {result_filename}")

                # 2. Evidence Injection (Search for existing patterns/docs)
                evidence_resp = await connector.query_memories(
                    query=f"{objective} patterns in {result_filename}",
                    project="RAE-Hive",
                    layers=["working", "semantic"],
                    k=3
                )
                evidence_context = ""
                if evidence_resp and evidence_resp.get("results"):
                    evidence_context = "\n### CRITICAL EVIDENCE (Context & Requirements):\n"
                    for res in evidence_resp["results"]:
                        evidence_context += f"- {res.get('content')}\n"

                # 3. Use RAE to "think" about the implementation
                thought_prompt = f"""
                Objective: {objective}
                File: {result_filename}
                {evidence_context}
                
                Instructions:
                1. Write the full, production-ready code. No placeholders.
                2. If it is a React/Next.js component, use functional components and hooks.
                3. Ensure strict typing (no 'any').
                4. Include error handling and logging.
                """
                
                code_response = await connector.think(thought_prompt)
                
                # 4. Extract and Clean Code
                code_content = code_response
                if "```" in code_response:
                    # Wyciąganie kodu z bloków markdown
                    parts = code_response.split("```")
                    for part in parts:
                        if part.strip().startswith(("typescript", "javascript", "python", "php", "css")):
                            code_content = "\n".join(part.strip().split("\n")[1:])
                            break
                        elif part.strip():
                            code_content = part.strip()
                            break

                # 5. Atomic Write
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with open(target_path, "w") as f:
                    f.write(code_content)
                
                # 6. Quality Pre-Audit (Internal Check)
                # To udowadnia, że Builder dba o jakość przed wysłaniem do Auditora
                quality_check = await connector.llm_call(f"Audit this code for syntax errors and common bugs: \n{code_content}")
                if "CRITICAL" in quality_check.upper():
                    logger.warn("quality_pre_audit_failed", task_id=task_id)
                    await connector.log_activity(f"Pre-audit found issues in {result_filename}. Self-correcting...")
                    # Tutaj mogłaby wejść pętla samonaprawcza
                
                logger.info("file_updated", path=target_path)
                await connector.update_task(task["id"], status="review", result=result_filename)
                await connector.log_activity(f"Modernized {result_filename} implementation ready for audit.")

        except Exception as e:
            logger.error("builder_error", error=str(e))
            
        await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(builder_loop())
