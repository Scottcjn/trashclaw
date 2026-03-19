import json
import urllib.request
import urllib.parse

TOOL_DEF = {
    "name": "get_weather",
    "description": "Get current weather for a specified location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city name to get weather for, e.g., Tokyo or Paris"
            }
        },
        "required": ["location"]
    }
}

def execute(kwargs):
    location = kwargs.get("location", "")
    if not location:
        return "Please specify a location."

    try:
        # First, geocode the location to get latitude and longitude
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(location)}&count=1&format=json"
        geo_req = urllib.request.Request(geo_url, headers={'User-Agent': 'TrashClawPlugin/1.0'})
        with urllib.request.urlopen(geo_req) as response:
            geo_data = json.loads(response.read().decode('utf-8'))
            
        if not geo_data.get('results'):
            return f"Could not find coordinates for {location}"
            
        lat = geo_data['results'][0]['latitude']
        lon = geo_data['results'][0]['longitude']
        resolved_name = geo_data['results'][0]['name']
        
        # Then, fetch the current weather using the coordinates
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_req = urllib.request.Request(weather_url, headers={'User-Agent': 'TrashClawPlugin/1.0'})
        with urllib.request.urlopen(weather_req) as response:
            weather_data = json.loads(response.read().decode('utf-8'))
            
        current = weather_data.get('current_weather', {})
        temp = current.get('temperature', 'unknown')
        wind = current.get('windspeed', 'unknown')
        
        return f"Current weather in {resolved_name}: {temp}°C, Wind speed: {wind} km/h."
    except Exception as e:
        return f"Failed to fetch weather: {e}"
