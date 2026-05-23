import requests
import json
import os
from dotenv import load_dotenv

load_dotenv("/home/whoshotu/Documents/buddy-relay-care/.env")

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}",
    "Content-Type": "application/json"
}
payload = {
    "model": os.environ.get("OPENROUTER_MODEL"),
    "messages": [
        {
            "role": "user",
            "content": "If you built the world's tallest skyscraper, what would you name it?"
        }
    ]
}

response = requests.post(url, headers=headers, json=payload)
print(response.status_code)
print(response.text[:800])
