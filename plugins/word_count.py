"""
Word Count Plugin for TrashClaw
"""

TOOL_DEF = {
    "name": "word_count",
    "description": "Count words, characters, and lines in text.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to analyze"
            }
        },
        "required": ["text"]
    }
}

def run(text: str = "", **kwargs) -> str:
    if not text:
        return "Lines: 0\nWords: 0\nCharacters: 0"
    
    lines = len(text.splitlines())
    words = len(text.split())
    chars = len(text)
    
    return f"Lines: {lines}\nWords: {words}\nCharacters: {chars}"
