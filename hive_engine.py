# hive_engine.py
import os
import subprocess
from fastapi import FastAPI, Request
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.sse import SseServerTransport
import uvicorn

# Import z naszego twardego jądra
from rae_core.utils.enterprise_guard import RAE_Enterprise_Foundation, audited_operation

class HiveExecutionSwarm:
    def __init__(self):
        # 1. Twardy wymóg inicjalizacji fundamentu Enterprise
        self.enterprise_foundation = RAE_Enterprise_Foundation(module_name="rae-hive")

    @audited_operation(operation_name="execute_system_command", impact_level="high")
    def run_command(self, command: str) -> dict:
        """Executes a system command within the swarm environment."""
        self.enterprise_foundation.logger.info(f"🛠️ [Hive Execution] Command: {command}")
        
        # Wbudowany Guard: Zakaz usuwania całego systemu
        if "rm -rf /" in command:
            raise PermissionError("Attempted execution of a critically destructive command.")

        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
        except Exception as e:
            return {"error": str(e)}

# Inicjalizacja usług
swarm = HiveExecutionSwarm()
mcp_server = Server("rae-hive")

@mcp_server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="execute_swarm_task",
            description="Executes a system command within the swarm environment. Full audit trail is generated.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"}
                },
                "required": ["command"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "execute_swarm_task":
        cmd = arguments.get("command")
        # Wywołanie chronionej metody
        result = swarm.run_command(cmd)
        
        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]
            
        return [TextContent(type="text", text=f"Exit: {result['exit_code']}\nOut: {result['stdout']}")]
    raise ValueError(f"Unknown tool: {name}")

app = FastAPI()
sse = SseServerTransport("/mcp/messages")

@app.get("/mcp/sse")
async def mcp_sse_endpoint(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
