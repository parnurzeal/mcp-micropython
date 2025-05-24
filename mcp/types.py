# mcp/types.py
# Helper functions for creating JSON-RPC 2.0 responses.

# Removed unused JSONRPCMessage and SessionMessage classes as the server
# currently uses dictionaries for message handling and these helper functions
# for response creation, which is more lightweight for MicroPython.


def create_error_response(req_id, code, message, data=None):
    err_obj = {"code": code, "message": message}
    if data:
        err_obj["data"] = data

    resp = {"jsonrpc": "2.0", "id": req_id, "error": err_obj}
    return resp


def create_success_response(req_id, result_data):
    resp = {"jsonrpc": "2.0", "id": req_id, "result": result_data}
    return resp
