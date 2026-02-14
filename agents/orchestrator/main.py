"""
RAE Hive Orchestrator.
Main entry point for the agent that plans and delegates tasks.
Revised: Now uses Semantic 'hive_objective' for steering.
"""

import asyncio
import os
import structlog
from base_agent.connector import HiveMindConnector

logger = structlog.get_logger(__name__)

async def orchestrator_loop():
    connector = HiveMindConnector(agent_role="orchestrator")
    logger.info("orchestrator_started", status="online")
    
    # Register self in episodic memory
    await connector.log_activity("Orchestrator online and watching Semantic Objectives.")

    while True:
        try:
            # 1. Check for high-level User Objectives in Semantic Layer
            # We look for memories tagged 'hive_objective' with status 'pending'
            objectives = await connector.list_memories(
                layer="semantic",
                tags=["hive_objective", "pending"],
                limit=5
            )

            for objective in objectives:
                obj_id = objective["id"]
                content = objective["content"]
                logger.info("processing_objective", id=obj_id, content=content)
                
                # 2. Use RAE to "think" about deconstructing this objective
                # Actively queries source code and memory to build a plan
                thought_prompt = f"""
                User Objective: {content}
                
                Your Task:
                1. Analyze the current codebase state via RAE Memory.
                2. Deconstruct this objective into specific, atomic tasks for the BUILDER.
                3. Each task must include: target files, logic to implement, and verification steps.
                
                Output your plan as a list of tasks.
                """
                
                plan = await connector.think(thought_prompt)
                await connector.log_activity(f"Deconstructed objective {obj_id} into plan.")

                # 3. Create real tasks for the Builder in Semantic Layer
                # In a more advanced version, we'd parse the 'plan' into multiple memories.
                # For now, we delegate the whole plan as Task 1.
                await connector.add_memory(
                    content=plan,
                    layer="semantic",
                    tags=["hive_task", "builder", "pending"],
                    metadata={
                        "task_id": f"task_{obj_id[:8]}",
                        "assignee": "builder",
                        "status": "pending",
                        "objective_ref": str(obj_id)
                    }
                )
                
                # 4. Mark objective as 'processed' to avoid duplicate planning
                # We do this by adding an update or changing tags if the API supported it.
                # For now, we add a memory signifying the objective is being handled.
                await connector.add_memory(
                    content=f"Objective {obj_id} is now being handled by the Hive.",
                    layer="semantic",
                    tags=["hive_objective_processed"],
                    metadata={"related_objective_id": obj_id}
                )
                
                await connector.log_activity(f"Delegated tasks for objective {obj_id} to Builder.")

        except Exception as e:
            logger.error("orchestrator_error", error=str(e))
            
        await asyncio.sleep(30) # Poll every 30 seconds

if __name__ == "__main__":
    asyncio.run(orchestrator_loop())
