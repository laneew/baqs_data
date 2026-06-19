import requests
import base64
from datetime import datetime

# ===== CONFIG =====
TOKEN = "PASTE_YOUR_TOKEN_HERE"
USERNAME = "YOUR_GITHUB_USERNAME"
REPO = "baqs_data"
FILE_PATH = "data.json"

# ===== CREATE DATA =====
data = {
    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

content = str(data).replace("'", '"')  # simple JSON string

# GitHub requires base64 encoding
encoded = base64.b64encode(content.encode()).decode()

url = f"https://api.github.com/repos/{USERNAME}/{REPO}/contents/{FILE_PATH}"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Check if file already exists (needed for update)
r = requests.get(url, headers=headers)
sha = r.json().get("sha") if r.status_code == 200 else None

payload = {
    "message": "Auto update data.json",
    "content": encoded,
}

if sha:
    payload["sha"] = sha

response = requests.put(url, json=payload, headers=headers)

print(response.status_code)
print(response.json())
