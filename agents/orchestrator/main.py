"""
RAE Hive Orchestrator & Autonomous L2/L3 Expert.
Plans new objectives AND resolves loops flagged by the Semantic Watchdog.
"""

import asyncio
import os
import structlog
from base_agent.connector import HiveMindConnector

logger = structlog.get_logger(__name__)

async def handle_new_objectives(connector: HiveMindConnector):
    """Processes brand new user objectives into tasks."""
    objectives = await connector.list_memories(layer="semantic", tags=["hive_objective", "pending"], limit=5)
    for objective in objectives:
        obj_id = objective["id"]
        content = objective["content"]
        logger.info("processing_new_objective", id=obj_id)
        
        plan = await connector.think(f"Deconstruct this into a task: {content}")
        
        await connector.add_memory(
            content=plan,
            layer="semantic",
            tags=["hive_task", "builder", "pending"],
            metadata={"task_id": f"task_{obj_id[:8]}", "assignee": "builder", "status": "pending"}
        )
        await connector.add_memory(
            content=f"Objective {obj_id} delegated.", layer="semantic", tags=["hive_objective_processed"]
        )

async def resolve_expert_escalations(connector: HiveMindConnector):
    """Acts as L2/L3 Council to break semantic loops flagged by Watchdog."""
    # We query all semantic tasks looking for escalation flags in metadata
    tasks = await connector.query_memories(query="*", layers=["semantic"], tags=["hive_task"], k=20)
    
    for t_wrapper in tasks:
        # Depending on query return format, metadata might be nested
        task = t_wrapper if isinstance(t_wrapper, dict) else t_wrapper.__dict__
        meta = task.get("metadata", {})
        task_id = meta.get("task_id", task.get("id"))
        
        if meta.get("requires_expert") is True or meta.get("status") == "BLOCKED_L3":
            logger.warning("autonomous_intervention_triggered", task_id=task_id, level=meta.get("escalation_level", "L3"))
            
            # Fetch the rejection history from episodic memory
            history = await connector.query_memories(query=f"task_id:{task_id}", layers=["episodic"], tags=["audit_rejection"], k=5)
            error_context = "\n".join([h.get("content", "") for h in history])
            
            # L2/L3 Diagnostic Prompt
            prompt = f"""
            You are the L2 Expert Council. The L1 Builder is stuck in an infinite loop on task: {task_id}.
            
            HISTORY OF FAILURES:
            {error_context}
            
            YOUR JOB:
            1. Diagnose WHY the builder keeps failing (e.g., missing dependencies, wrong assumptions).
            2. Provide an EXACT code snippet or hard directive that the Builder MUST use to break the loop.
            """
            
            solution = await connector.think(prompt)
            
            # Inject the solution as Evidence
            await connector.add_memory(
                content=f"EXPERT INTERVENTION (L2/L3): {solution}",
                layer="working",
                tags=["evidence_injection", "expert_guidance"],
                metadata={"related_task_id": task_id, "instruction": "STOP LOOPING. USE THIS EXPERT CODE."}
            )
            
            # Reset task state to force Builder to retry with new evidence
            # We clear the requires_expert flag so we don't loop the intervention
            new_meta = {**meta, "requires_expert": False, "status": "pending", "fail_count": 0}
            # Note: We simulate the update via connector logging for now, 
            # real implementation would use the PATCH endpoint.
            await connector.update_task(task_id, status="pending", result="Intervention applied.")
            logger.info("intervention_applied", task_id=task_id)


async def orchestrator_loop():
    connector = HiveMindConnector(agent_role="orchestrator")
    logger.info("orchestrator_started", status="online")
    await connector.log_activity("Autonomous L2 Expert online.")

    while True:
        try:
            await handle_new_objectives(connector)
            await resolve_expert_escalations(connector)
        except Exception as e:
            logger.error("orchestrator_error", error=str(e))
            
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(orchestrator_loop())
