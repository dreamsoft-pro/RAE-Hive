"""
RAE Hive Connector.
Standardized interface for agents to interact with RAE Memory API v2.
"""

import os
import yaml
import httpx
import structlog
from typing import Any, Dict, List, Optional

logger = structlog.get_logger(__name__)

class HiveMindConnector:
    def __init__(self, agent_role: str):
        self.role = agent_role
        self.config = self._load_config()
        
        self.base_url = os.getenv("RAE_API_URL", self.config["memory"]["api_url"])
        self.api_key = os.getenv("RAE_API_KEY", "dev-key")
        self.tenant_id = self.config["memory"]["tenant_id"]
        self.project_id = self.config["memory"].get("project_id", "RAE-Hive")
        
        self.headers = {
            "X-API-Key": self.api_key,
            "X-Tenant-Id": self.tenant_id,
            "Content-Type": "application/json"
        }

    def _load_config(self) -> Dict[str, Any]:
        config_path = os.getenv("HIVE_CONFIG_PATH", "/app/config/hive_protocol.yaml")
        if not os.path.exists(config_path):
            # Fallback for local testing
            config_path = "agent_hive/config/hive_protocol.yaml"
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    async def list_memories(self, layer: str = None, tags: List[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List memories from a specific layer."""
        params = {"limit": limit, "project": self.project_id}
        if layer:
            params["layer"] = layer
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v2/memories/",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            
            # Client-side tag filtering if tags provided
            if tags:
                filtered = []
                for m in results:
                    m_tags = m.get("tags", [])
                    if any(t in m_tags for t in tags):
                        filtered.append(m)
                return filtered
            return results

    async def add_memory(self, content: str, layer: str, tags: List[str] = None, metadata: Dict[str, Any] = None):
        """Add a new memory to RAE."""
        payload = {
            "content": content,
            "layer": layer,
            "project": self.project_id,
            "tags": tags or [],
            "metadata": metadata or {},
            "source": self.role
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/memories/",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def query_memories(self, query: str, k: int = 5, layers: List[str] = None) -> List[Dict[str, Any]]:
        """Query memories using hybrid search."""
        payload = {
            "query": query,
            "project": self.project_id,
            "k": k,
            "layers": layers
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/memories/query",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json().get("results", [])

    async def log_activity(self, content: str, level: str = "info"):
        """Log agent activity to episodic memory."""
        await self.add_memory(
            content=f"[{self.role.upper()}] {content}",
            layer="episodic",
            tags=["hive_log", self.role, level],
            metadata={"role": self.role, "level": level}
        )

    async def get_tasks(self, status: str = "pending") -> List[Dict[str, Any]]:
        """Fetch tasks assigned to this role or general pending tasks."""
        # Use list_memories from semantic layer
        memories = await self.list_memories(layer="semantic", limit=100)
        
        tasks = []
        for m in memories:
            meta = m.get("metadata", {})
            # Match task_id and status, and assignee if not orchestrator
            if "task_id" in meta and meta.get("status") == status:
                if self.role == "orchestrator" or meta.get("assignee") == self.role:
                    tasks.append(m)
        return tasks

    async def update_task(self, memory_id: str, status: str, result: str = ""):
        """Update a task's status (by adding a new update memory)."""
        await self.add_memory(
            content=f"Task Update for {memory_id}: {status}",
            layer="semantic",
            tags=["hive_task_update", status],
            metadata={
                "related_task_id": memory_id, 
                "status": status, 
                "result": result,
                "task_id": "UNKNOWN" # We'd need to fetch original task to propagate task_id
            }
        )
        logger.info("task_updated", memory_id=memory_id, status=status)

    async def think(self, prompt: str) -> str:
        """Use RAE's agent execution API to think and generate a response."""
        payload = {
            "tenant_id": self.tenant_id,
            "project": self.project_id,
            "prompt": f"Acting as {self.role.upper()}. {prompt}"
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            # We use /v2/agent/execute which is the RAE High-Level Agent API
            response = await client.post(
                f"{self.base_url}/v2/agent/execute",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            answer = data.get("answer", "No answer generated.")
            
            # Log thinking process to episodic memory
            await self.log_activity(f"Thinking result: {answer[:100]}...", level="debug")
            return answer

    def read_source_file(self, file_path: str) -> str:
        """Read a file from the mounted source directory."""
        # Source is mounted at /app/src
        full_path = os.path.join("/app/src", file_path)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                return f.read()
        raise FileNotFoundError(f"Source file {file_path} not found")

    def write_source_file(self, file_path: str, content: str):
        """Write/Modify a file in the source directory."""
        full_path = os.path.join("/app/src", file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        logger.info("file_written", path=file_path)
