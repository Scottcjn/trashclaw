import urllib.request
import urllib.parse

TOOL_DEF = {
    "name": "get_weather",
    "description": "Get the current weather for a specified location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city or location to get the weather for."
            }
        },
        "required": ["location"]
    }
}

def execute(kwargs):
    location = kwargs.get("location", "")
    if not location:
        return "Please provide a location."
    
    try:
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=3"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            weather = response.read().decode('utf-8').strip()
            return weather
    except Exception as e:
        return f"Failed to get weather for {location}: {str(e)}"
