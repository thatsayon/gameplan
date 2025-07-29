import requests
import json

# URL of your FastAPI app
url = "http://127.0.0.1:8000/chat"

# Define the test payload (JSON data) for the first message
payload = {
    "user_id": "12345",
    "message": "Hello, assistant!",  # First user message
    "chat_history": []  # Empty history for the first message
}

# Set headers
headers = {
    "Content-Type": "application/json"
}

# Send POST request for the first message
response = requests.post(url, data=json.dumps(payload), headers=headers)

# Check if the request was successful
if response.status_code == 200:
    print("Response 1 from API:", response.json())
else:
    print(f"Request failed with status code {response.status_code}")
    print("Response content:", response.text)

# Simulate the second turn of the conversation (multi-turn chat)
payload["message"] = "What is the weather like today?"  # Second user message
payload["chat_history"].append({
    "user_message": "Hello, assistant!",
    "bot_message": response.json()["response"]  # Use the first response from the bot
})

# Send POST request for the second message
response = requests.post(url, data=json.dumps(payload), headers=headers)

# Check if the request was successful
if response.status_code == 200:
    print("Response 2 from API:", response.json())
else:
    print(f"Request failed with status code {response.status_code}")
    print("Response content:", response.text)

# Simulate a third turn of the conversation
payload["message"] = "Can you tell me the news?"  # Third user message
payload["chat_history"].append({
    "user_message": "What is the weather like today?",
    "bot_message": response.json()["response"]  # Use the second response from the bot
})

# Send POST request for the third message
response = requests.post(url, data=json.dumps(payload), headers=headers)

# Check if the request was successful
if response.status_code == 200:
    print("Response 3 from API:", response.json())
else:
    print(f"Request failed with status code {response.status_code}")
    print("Response content:", response.text)
