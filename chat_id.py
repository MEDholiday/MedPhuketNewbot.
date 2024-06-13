import requests
from config import token

bot_token = "YOUR_BOT_TOKEN"
response = requests.get(f"https://api.telegram.org/bot{token}/getUpdates")
data = response.json()
chat_id = data["result"][0]["message"]["chat"]["id"]

print("ID чата с ботом:", chat_id)

# 296318553
# 
