"""MCP tool wrapper with structured isError handling.

This module wraps MCP tool calls so that tool-level errors are returned
as structured results (isError: True) rather than crashing the agent.
The orchestrator can then decide to retry, repair arguments, or degrade.
"""
import asyncio
from typing import Any, Dict, Optional


class MCPToolResult:
    def __init__(
        self,
        content: Any,
        is_error: bool = False,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.content = content
        self.is_error = is_error
        self.error_type = error_type  # transport | protocol | application
        self.error_message = error_message

    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "isError": self.is_error,
            "errorType": self.error_type,
            "errorMessage": self.error_message,
        }


async def call_mcp_tool(
    tool_name: str,
    arguments: Dict,
    server_url: str,
    max_repair_attempts: int = 2,
) -> MCPToolResult:
    """Call an MCP tool and return a structured result.

    On transport failure (server down), returns isError=True with type=transport.
    On protocol/validation error, returns isError=True with type=protocol.
    On application error from the tool itself, returns isError=True with type=application.
    On success, returns the tool content with isError=False.
    """
    import httpx

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    for attempt in range(max_repair_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(server_url, json=payload)

                # Transport-level HTTP error
                if r.status_code >= 500:
                    return MCPToolResult(
                        content=None,
                        is_error=True,
                        error_type="transport",
                        error_message=f"MCP server returned HTTP {r.status_code}",
                    )

                data = r.json()

                # JSON-RPC protocol error
                if "error" in data:
                    err = data["error"]
                    return MCPToolResult(
                        content=None,
                        is_error=True,
                        error_type="protocol",
                        error_message=f"{err.get('code')}: {err.get('message')}",
                    )

                result = data.get("result", {})

                # Application-level tool error (MCP spec: isError in result)
                if result.get("isError"):
                    if attempt < max_repair_attempts:
                        # Give the caller a chance to repair arguments
                        # For now, just retry the same call (caller can intercept)
                        await asyncio.sleep(0.5)
                        continue
                    return MCPToolResult(
                        content=result.get("content"),
                        is_error=True,
                        error_type="application",
                        error_message="Tool returned isError=true after max repair attempts",
                    )

                return MCPToolResult(content=result.get("content"), is_error=False)

        except httpx.ConnectError:
            return MCPToolResult(
                content=None,
                is_error=True,
                error_type="transport",
                error_message=f"MCP server unreachable at {server_url}",
            )
        except Exception as e:
            return MCPToolResult(
                content=None,
                is_error=True,
                error_type="transport",
                error_message=str(e),
            )

    return MCPToolResult(
        content=None,
        is_error=True,
        error_type="application",
        error_message="Max repair attempts exceeded",
    )
