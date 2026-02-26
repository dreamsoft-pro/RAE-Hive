import asyncio
import os
import httpx
import structlog
import json

# RAE-Suite: Tactical Semantic Watchdog v2.2
# Implements Hierarchical 3-Layered Reflection (L1/L2/L3 Integrity).

logger = structlog.get_logger("TacticalWatchdog")

API_URL = os.getenv("RAE_API_URL", "http://localhost:8001")
HEADERS = {
    "X-API-Key": os.getenv("RAE_API_KEY", "dev-key"),
    "X-Tenant-Id": "00000000-0000-0000-0000-000000000000"
}
PROJECT_ID = "RAE-Hive"

# Escalation Thresholds
SWAP_THRESHOLD = 2    # L1: Model Swap
L2_THRESHOLD = 4      # L2: Expert Review
L3_THRESHOLD = 6      # L3: Supreme Circuit Break

async def update_task_metadata(client: httpx.AsyncClient, task_id: str, metadata_updates: dict):
    """Updates task metadata in RAE-Core."""
    response = await client.get(f"{API_URL}/v2/memories/{task_id}", headers=HEADERS)
    if response.status_code == 200:
        current_task = response.json()
        new_metadata = {**current_task.get("metadata", {}), **metadata_updates}
        await client.patch(f"{API_URL}/v2/memories/{task_id}", json={"metadata": new_metadata}, headers=HEADERS)

async def store_reflection(client: httpx.AsyncClient, tier: str, content: str, task_id: str):
    """Stores a hierarchical reflection (L1, L2, or L3 tier)."""
    payload = {
        "content": content,
        "layer": "reflective",
        "project": PROJECT_ID,
        "importance": 0.5 if tier == "L1" else 0.8 if tier == "L2" else 1.0,
        "tags": ["reflection", tier, f"task_{task_id}"],
        "metadata": {
            "task_id": task_id,
            "reflection_tier": tier, # Hierarchical partitioning
            "audit_standard": "ISO-42001" if tier == "L3" else "Technical"
        }
    }
    await client.post(f"{API_URL}/v2/memories/", json=payload, headers=HEADERS)

async def check_semantic_loops():
    """Scans tasks and applies hierarchical tactical corrections."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_URL}/v2/memories/query", 
                                   json={"query": "*", "tags": ["hive_task", "in_progress", "review"], "k": 50}, 
                                   headers=HEADERS)
        
        if response.status_code != 200: return
        tasks = response.json().get("results", [])
        
        for task in tasks:
            task_id = task.get("id")
            meta = task.get("metadata", {})
            fail_count = meta.get("fail_count", 0)
            
            if fail_count >= L3_THRESHOLD:
                await update_task_metadata(client, task_id, {"status": "BLOCKED_L3"})
                await store_reflection(client, "L3", f"CRITICAL: Task {task_id} failed after full L2 guidance. Requires Contract/Graph refactor.", task_id)
                
            elif fail_count >= L2_THRESHOLD and meta.get("escalation_level") != "L2":
                await update_task_metadata(client, task_id, {"escalation_level": "L2", "requires_expert": True})
                await store_reflection(client, "L2", f"EXPERT: L1 Model Swap failed for task {task_id}. Initiating Expert Dialectic Audit.", task_id)
                
            elif fail_count >= SWAP_THRESHOLD and not meta.get("roles_swapped"):
                await update_task_metadata(client, task_id, {"roles_swapped": True})
                await store_reflection(client, "L1", f"WORKING: Cognitive bias detected in L1 for task {task_id}. Swapping Builder/Auditor.", task_id)

async def watchdog_loop():
    logger.info("Tactical Semantic Watchdog v2.2 (3-Layer Reflection) active.")
    while True:
        await check_semantic_loops()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(watchdog_loop())
