# MCP Package for MicroPython
import sys

# Import key components to make them available at the package level
from .types import (
    JSONRPCMessage,
    SessionMessage,
    create_error_response,
    create_success_response,
)
from .stdio_server import stdio_server, process_mcp_message

__all__ = [
    "JSONRPCMessage",
    "SessionMessage",
    "create_error_response",
    "create_success_response",
    "stdio_server",
    "process_mcp_message",
]

print("MCP MicroPython SDK initialized", file=sys.stderr)
