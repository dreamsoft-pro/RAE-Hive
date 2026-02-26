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

    async def add_memory(self, content: str, layer: str, tags: List[str] = None, metadata: Dict[str, Any] = None, project: str = None):
        """Add a new memory to RAE."""
        payload = {
            "content": content,
            "layer": layer,
            "project": project or self.project_id,
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

    async def query_memories(self, query: str, k: int = 5, layers: List[str] = None, project: str = None, tags: List[str] = None) -> List[Dict[str, Any]]:
        """Query memories using hybrid search."""
        payload = {
            "query": query,
            "project": project or self.project_id,
            "k": k,
            "layers": layers,
            "tags": tags
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
        """Fetch tasks using multiple fallback strategies (Tags -> Metadata -> Content)."""
        async with httpx.AsyncClient() as client:
            # 1. Try to get all memories for the project from semantic layer (Postgres fallback)
            params = {"project": self.project_id, "layer": "semantic", "limit": 100}
            resp = await client.get(f"{self.base_url}/v2/memories/", headers=self.headers, params=params)
            
            if resp.status_code != 200:
                logger.error("failed_to_fetch_base_memories", status=resp.status_code)
                return []
                
            all_memories = resp.json().get("results", [])
            
            # 2. Identify base tasks and updates
            base_tasks = []
            updates = []
            for m in all_memories:
                content = m.get("content", "").lower()
                tags = m.get("tags", [])
                meta = m.get("metadata", {})
                
                # Identify updates
                if "hive_task_update" in tags or "task update" in content:
                    updates.append(m)
                # Identify base tasks (by tag or by metadata pattern)
                elif "hive_task" in tags or "task_id" in meta or "objective_ref" in meta:
                    base_tasks.append(m)

            # 3. Map latest status by related_task_id
            latest_status_map = {}
            for up in sorted(updates, key=lambda x: x.get("timestamp") or "", reverse=False):
                u_meta = up.get("metadata", {})
                t_id = u_meta.get("related_task_id")
                if t_id:
                    latest_status_map[t_id] = u_meta.get("status")

            # 4. Filter by status and assignee
            final_tasks = []
            for task in base_tasks:
                t_id = task.get("id")
                meta = task.get("metadata", {})
                
                # Derive current status
                current_status = latest_status_map.get(t_id, meta.get("status", "pending"))
                
                if current_status == status:
                    # Role check
                    if self.role == "orchestrator" or meta.get("assignee") == self.role or self.role == "auditor":
                        task["current_status"] = current_status
                        final_tasks.append(task)
            
            return final_tasks

    async def update_task(self, memory_id: str, status: str, result: str = ""):
        """Update a task's status via Event Sourcing (append-only log)."""
        await self.add_memory(
            content=f"Task Update for {memory_id}: {status}",
            layer="semantic",
            tags=["hive_task_update", status],
            metadata={
                "related_task_id": memory_id, 
                "status": status, 
                "result": result
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
