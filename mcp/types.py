# Placeholder for MCP message types
# In a real implementation, these would define
# the expected structures for requests and responses.


class JSONRPCMessage:
    def __init__(self, id, method, params=None, jsonrpc="2.0"):
        self.jsonrpc = jsonrpc
        self.id = id
        self.method = method
        self.params = params if params is not None else {}
        self.result = None
        self.error = None

    def to_dict(self):
        data = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
            "params": self.params,
        }
        # For responses, method is not present, result or error is.
        # This class is a simplification for now.
        if hasattr(self, "result"):
            data["result"] = self.result
            del data["method"]
            del data["params"]
        if hasattr(self, "error"):
            data["error"] = self.error
            del data["method"]
            del data["params"]
        return data

    @classmethod
    def from_dict(cls, data):
        msg = cls(
            id=data.get("id"), method=data.get("method"), params=data.get("params")
        )
        if "result" in data:
            msg.result = data["result"]
        if "error" in data:
            msg.error = data["error"]
        return msg


class SessionMessage:
    def __init__(self, message: JSONRPCMessage):
        self.message = message

    def to_dict(self):
        return self.message.to_dict()

    @classmethod
    def from_dict(cls, data):
        return cls(JSONRPCMessage.from_dict(data))


def create_error_response(req_id, code, message, data=None):
    err_obj = {"code": code, "message": message}
    if data:
        err_obj["data"] = data

    resp = {"jsonrpc": "2.0", "id": req_id, "error": err_obj}
    return resp


def create_success_response(req_id, result_data):
    resp = {"jsonrpc": "2.0", "id": req_id, "result": result_data}
    return resp
