# MCP Package for MicroPython
import sys

# Import key components to make them available at the package level
from .types import (
    create_error_response,
    create_success_response,
)  # Removed JSONRPCMessage, SessionMessage
from .stdio_server import stdio_server

__all__ = [
    # "JSONRPCMessage", # Removed
    # "SessionMessage", # Removed
    "create_error_response",
    "create_success_response",
    "stdio_server",
]

print("MCP MicroPython SDK initialized", file=sys.stderr)
