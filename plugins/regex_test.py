"""
Regex Tester for TrashClaw
"""

import re

TOOL_DEF = {
    "name": "regex_test",
    "description": "Test a regular expression pattern against a test string.",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "The regular expression pattern (e.g. '^[0-9]+')"
            },
            "test_string": {
                "type": "string",
                "description": "The text to test the regex against"
            },
            "ignore_case": {
                "type": "boolean",
                "description": "Whether to ignore case (default: false)"
            }
        },
        "required": ["pattern", "test_string"]
    }
}

def run(pattern: str = "", test_string: str = "", ignore_case: bool = False, **kwargs) -> str:
    if not pattern:
        return "Error: pattern is required."
    
    flags = re.IGNORECASE if ignore_case else 0
    try:
        compiled = re.compile(pattern, flags)
        matches = compiled.finditer(test_string)
        
        results = []
        for m in matches:
            results.append(f"Match '{m.group()}' at span {m.span()}")
            
        if not results:
            return "No matches found."
            
        return "Matches found:\n" + "\n".join(results)
    except re.error as e:
        return f"Regex Error: {e}"
    except Exception as e:
        return f"Error: {e}"
