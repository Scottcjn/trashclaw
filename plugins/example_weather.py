import urllib.request
import urllib.parse
import urllib.error
import json

TOOL_DEF = {
    "name": "get_weather",
    "description": "Get the current weather conditions for a specific location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state/country, e.g., 'San Francisco, CA' or 'Paris, France'."
            }
        },
        "required": ["location"]
    }
}

def execute(kwargs):
    location = kwargs.get("location")
    if not location:
        return "Error: location parameter is required."
        
    encoded_location = urllib.parse.quote(location)
    # format=j1 returns JSON data which is easy to parse without API keys
    url = f"https://wttr.in/{encoded_location}?format=j1"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'TrashClaw/1.0 (Plugin)'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if not data.get('current_condition'):
                return f"Could not parse weather condition for {location}."
                
            current = data['current_condition'][0]
            temp_c = current['temp_C']
            temp_f = current['temp_F']
            desc = current['weatherDesc'][0]['value']
            humidity = current['humidity']
            wind_kmph = current['windspeedKmph']
            
            result = (
                f"Weather in {location}:\n"
                f"Conditions: {desc}\n"
                f"Temperature: {temp_c}°C ({temp_f}°F)\n"
                f"Humidity: {humidity}%\n"
                f"Wind Speed: {wind_kmph} km/h"
            )
            return result
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return f"Weather data not found for location: {location}"
        return f"HTTP error occurred: {e.code}"
    except urllib.error.URLError as e:
        return f"Failed to connect to weather service: {e.reason}"
    except Exception as e:
        return f"Error retrieving weather: {str(e)}"
