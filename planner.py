"""
RAE Hive Planner CLI.
Entry point for the user to delegate work to the agent hive.
"""

import argparse
import asyncio
import os
import uuid
import yaml
import httpx
from datetime import datetime

def load_config():
    config_path = "agent_hive/config/hive_protocol.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

async def add_objective(goal: str, priority: int = 1):
    config = load_config()
    base_url = os.getenv("RAE_API_URL", config["memory"]["api_url"])
    tenant_id = config["memory"]["tenant_id"]
    project_id = config["memory"].get("project_id", "RAE-Hive")
    api_key = os.getenv("RAE_API_KEY", "dev-key")

    headers = {
        "X-API-Key": api_key,
        "X-Tenant-Id": tenant_id,
        "Content-Type": "application/json"
    }

    payload = {
        "content": goal,
        "layer": "semantic",
        "project": project_id,
        "tags": ["hive_objective", "pending"],
        "importance": priority / 10.0,
        "metadata": {
            "objective_id": str(uuid.uuid4()),
            "type": "user_delegation",
            "created_at": datetime.now().isoformat()
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/v2/memories/",
            headers=headers,
            json=payload
        )
        if response.status_code == 200:
            data = response.json()
            print(f"🚀 Objective added successfully! ID: {data['memory_id']}")
        else:
            print(f"❌ Failed to add objective: {response.text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAE Hive Planner - Delegate work to agents.")
    parser.add_argument("goal", type=str, help="The high-level goal or task for the agents.")
    parser.add_argument("--priority", type=int, default=5, help="Priority from 1 to 10.")
    
    args = parser.parse_args()
    
    asyncio.run(add_objective(args.goal, args.priority))
