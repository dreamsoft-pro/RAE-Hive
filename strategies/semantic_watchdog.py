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
    """Aggressive time-window based loop detection."""
    async with httpx.AsyncClient() as client:
        # 1. Fetch all tasks that are currently 'in_progress' or 'review'
        resp = await client.get(f"{API_URL}/v2/memories/?project={PROJECT_ID}&layer=semantic&limit=50", headers=HEADERS)
        if resp.status_code != 200: return
        tasks = resp.json().get("results", [])

        for task in tasks:
            task_id = task.get("id")
            content = task.get("content", "").lower()
            
            # 2. Check recent rejections for this specific task in episodic memory
            # We look for the literal string "Audit failed" which the Auditor writes
            rej_resp = await client.post(f"{API_URL}/v2/memories/query", 
                                       json={
                                           "query": f"Audit failed for {task_id}", 
                                           "project": PROJECT_ID,
                                           "layers": ["episodic"],
                                           "k": 5
                                       }, headers=HEADERS)
            
            rejections = rej_resp.json().get("results", []) if rej_resp.status_code == 200 else []
            
            # 3. If we see more than 2 rejections, we don't wait. We CRASH the loop.
            if len(rejections) >= 2:
                logger.critical("aggressive_break_triggered", task_id=task_id, count=len(rejections))
                
                # Emit a status update that Orkiestrator will see
                await update_task_metadata(client, task_id, {
                    "status": "BLOCKED_L3", 
                    "requires_expert": True,
                    "escalation_level": "L3",
                    "reason": "Rapid rejections detected. L1/L2 cannot reach consensus."
                })
                
                await store_reflection(client, "L3", f"SYSTEMIC FAILURE: Task {task_id} is in a high-frequency rejection loop. Breaking loop and requesting L3 snippet injection.", task_id)

async def watchdog_loop():
    logger.info("Tactical Semantic Watchdog v2.2 (3-Layer Reflection) active.")
    while True:
        await check_semantic_loops()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(watchdog_loop())
