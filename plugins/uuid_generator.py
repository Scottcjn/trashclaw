"""
TrashClaw Plugin — UUID Generator

Generates UUIDs for various use cases.
"""

import uuid

TOOL_DEF = {
    "name": "uuid_generator",
    "description": "Generates distinct UUIDs. Supports versions 1, 3, 4, and 5.",
    "parameters": {
        "type": "object",
        "properties": {
            "version": {
                "type": "integer",
                "description": "UUID version to generate (1, 3, 4, or 5). Default is 4."
            },
            "count": {
                "type": "integer",
                "description": "Number of UUIDs to generate. Default is 1."
            },
            "namespace": {
                "type": "string",
                "description": "Required for versions 3 and 5. Accepts 'dns', 'url', 'oid', 'x500', or a valid UUID string."
            },
            "name": {
                "type": "string",
                "description": "Required string name for versions 3 and 5."
            }
        },
        "required": []
    }
}

def run(version: int = 4, count: int = 1, namespace: str = "", name: str = "", **kwargs) -> str:
    """Generate UUIDs."""
    try:
        count = max(1, min(count, 1000)) # limit to 1000
        
        ns_obj = None
        if version in (3, 5):
            if not name:
                return "Error: param 'name' is required for UUID versions 3 and 5."
            if namespace.lower() == "dns":
                ns_obj = uuid.NAMESPACE_DNS
            elif namespace.lower() == "url":
                ns_obj = uuid.NAMESPACE_URL
            elif namespace.lower() == "oid":
                ns_obj = uuid.NAMESPACE_OID
            elif namespace.lower() == "x500":
                ns_obj = uuid.NAMESPACE_X500
            else:
                try:
                    ns_obj = uuid.UUID(namespace)
                except ValueError:
                    return f"Error: Invalid namespace '{namespace}'. Use 'dns', 'url', 'oid', 'x500', or a valid UUID."
        
        results = []
        for _ in range(count):
            if version == 1:
                u = uuid.uuid1()
            elif version == 3:
                u = uuid.uuid3(ns_obj, name)
            elif version == 4:
                u = uuid.uuid4()
            elif version == 5:
                u = uuid.uuid5(ns_obj, name)
            else:
                return f"Error: Unsupported UUID version: {version}"
            results.append(str(u))
            
        return "\n".join(results)
    except Exception as e:
        return f"UUID generation failed: {e}"
