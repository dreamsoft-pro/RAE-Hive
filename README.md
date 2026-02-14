# RAE Hive: Autonomous Agent Swarm

RAE Hive is a multi-agent system designed to perform autonomous engineering tasks (coding, auditing, and planning) by utilizing **RAE (Reflective Agentic-Memory Engine)** as a shared context and coordination mechanism.

## 🏗️ Architecture
The system consists of three core agent roles, each running in an isolated Docker container on Node 1 (Lumina):

1.  **Orchestrator (`qwen2.5:14b`):** Plans and deconstructs high-level objectives into atomic tasks.
2.  **Builder (`deepseek-coder-v2:16b`):** Implements code changes and applies improvements to the codebase.
3.  **Auditor (`llama3.1:8b`):** Verifies implementation quality and runs automated tests.

## 🧠 Shared Hive Mind
Communication between agents is strictly decoupled and happens via RAE Memory layers:
- **Semantic Layer:** Stores Objectives (`hive_objective`) and Tasks (`hive_task`).
- **Episodic Layer:** Stores granular activity logs (`hive_log`) for auditability.
- **Reflective Layer:** Stores cross-agent insights and meta-cognitive reflections.

## 🚀 Usage
To delegate a goal to the swarm, use the Planner CLI:
```bash
python3 planner.py "Implement a new feature or fix a bug" --priority 10
```

## 🛠️ Deployment
Ensure RAE API is running, then start the hive:
```bash
docker compose -f docker-compose.hive.yml up -d
```
