import os
import re
import random
import requests
import json
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get tokens from environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

app = App(token=SLACK_BOT_TOKEN)

# --- Message-based responses for specific commands ---
# These functions will fire only if the message matches the keyword or pattern

# Respond to "hello" or "hi"
@app.message(re.compile(r"^(hello|hi)\b", re.IGNORECASE))
def message_hello(message, say):
    user = message['user']
    say(f"Hello, <@{user}>! 👋")

# Respond to "how are you"
@app.message(re.compile(r"how are you\??", re.IGNORECASE))
def message_status(message, say):
    user = message['user']
    say(f"I'm doing great, <@{user}>! Thanks for asking.")

# Respond to "ping"
@app.message("ping")
def ping_pong(message, say):
    say("pong")

# Respond to "thanks" or "thank you"
@app.message(re.compile(r"thanks|thank you", re.IGNORECASE))
def thank_you_response(message, say):
    user = message['user']
    say(f"You're welcome, <@{user}>!")

# Respond to "give me a tip"
@app.message("give me a tip")
def give_tip(message, say):
    tips = [
        "Remember to stretch before coding.",
        "Take a short break every hour.",
        "Stay hydrated!"
    ]
    say(random.choice(tips))

# Respond to "bye" or "goodbye"
@app.message(re.compile(r"^(bye|goodbye)\b", re.IGNORECASE))
def message_bye(message, say):
    user = message['user']
    say(f"Goodbye, <@{user}>! Hope to talk to you again soon.")

# Respond when a member joins a channel
@app.event("member_joined_channel")
def welcome_new_member(event, say):
    user_id = event["user"]
    say(f"Welcome, <@{user_id}>! I'm glad you're here.")

# --- Conversational fallback with Gemini API ---
# This function will handle all messages that don't match a specific command.
@app.event("message")
def handle_general_message(event, say):
    # Ignore messages from bots to prevent an infinite loop
    if "bot_id" in event:
        return

    text = event.get("text")
    user_id = event["user"]

    # We check if the message is a direct mention and if it contains a question,
    # or if the message is a direct message to the bot.
    if re.search(r"<@\w+>", text) or event.get("channel_type") == "im":
        # The `re.sub` cleans up the text by removing the bot's mention, so the LLM gets a clean prompt.
        cleaned_text = re.sub(r"<@\w+>", "", text).strip()
        
        # Get a response from the Gemini API
        response_text = get_gemini_response(cleaned_text)
        say(f"{response_text}")

# Define a function to get a response from the Gemini API
def get_gemini_response(prompt):
    """
    Sends a prompt to the Gemini API and returns the generated text.
    """
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY is not set.")
        return "I can't answer that right now. My AI brain is offline."

    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    # NOTE: The model name has been changed back to gemini-pro, which is a conversational model.
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

    try:
        response = requests.post(api_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # This will raise an HTTPError for bad responses
        result = response.json()
        text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'No response found.')
        return text
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return "I'm having trouble connecting to my knowledge base right now. Please try again later."


if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()