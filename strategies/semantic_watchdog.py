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
    """Updates task metadata by emitting a new event."""
    payload = {
        "content": f"Watchdog update for {task_id}",
        "layer": "semantic",
        "project": PROJECT_ID,
        "tags": ["hive_task_update"],
        "metadata": {
            "related_task_id": task_id,
            **metadata_updates
        }
    }
    await client.post(f"{API_URL}/v2/memories/", json=payload, headers=HEADERS)

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
    """Scans tasks and applies hierarchical tactical corrections using Event Sourcing."""
    async with httpx.AsyncClient() as client:
        # Fetch base tasks
        base_resp = await client.post(f"{API_URL}/v2/memories/query", 
                                   json={"query": "*", "tags": ["hive_task"], "k": 100}, 
                                   headers=HEADERS)
        
        # Fetch updates
        update_resp = await client.post(f"{API_URL}/v2/memories/query", 
                                   json={"query": "*", "tags": ["hive_task_update"], "k": 500}, 
                                   headers=HEADERS)
        
        if base_resp.status_code != 200 or update_resp.status_code != 200: return
        
        tasks = base_resp.json().get("results", [])
        updates = update_resp.json().get("results", [])
        
        # Aggregate latest state
        latest_state = {}
        for up in sorted(updates, key=lambda x: x.get("timestamp", "")):
            meta = up.get("metadata", {})
            t_id = meta.get("related_task_id")
            if t_id:
                if t_id not in latest_state:
                    latest_state[t_id] = {}
                latest_state[t_id].update(meta)
        
        for task in tasks:
            task_id = task.get("id")
            current_meta = task.get("metadata", {})
            
            # Merge original meta with latest updates
            if task_id in latest_state:
                current_meta.update(latest_state[task_id])
                
            status = current_meta.get("status", "")
            
            if status not in ["in_progress", "review"]:
                continue
                
            # Count audit rejections from episodic
            rej_resp = await client.post(f"{API_URL}/v2/memories/query", 
                                       json={"query": f"task_id:{task_id}", "layers": ["episodic"], "tags": ["audit_rejection"], "k": 50}, 
                                       headers=HEADERS)
            
            rejections = rej_resp.json().get("results", []) if rej_resp.status_code == 200 else []
            fail_count = len(rejections)
            
            if fail_count >= L3_THRESHOLD:
                await update_task_metadata(client, task_id, {"status": "BLOCKED_L3"})
                await store_reflection(client, "L3", f"CRITICAL: Task {task_id} failed after full L2 guidance. Requires Contract/Graph refactor.", task_id)
                
            elif fail_count >= L2_THRESHOLD and current_meta.get("escalation_level") != "L2":
                await update_task_metadata(client, task_id, {"escalation_level": "L2", "requires_expert": True})
                await store_reflection(client, "L2", f"EXPERT: L1 Model Swap failed for task {task_id}. Initiating Expert Dialectic Audit.", task_id)
                
            elif fail_count >= SWAP_THRESHOLD and not current_meta.get("roles_swapped"):
                await update_task_metadata(client, task_id, {"roles_swapped": True})
                await store_reflection(client, "L1", f"WORKING: Cognitive bias detected in L1 for task {task_id}. Swapping Builder/Auditor.", task_id)

async def watchdog_loop():
    logger.info("Tactical Semantic Watchdog v2.2 (3-Layer Reflection) active.")
    while True:
        await check_semantic_loops()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(watchdog_loop())
