import google.generativeai as genai
from flask import Flask, request, jsonify
import requests
import os

# --- 1. CONFIGURATION ---
TEACHER_NUMBER = "254112196147" 
wa_token = os.environ.get("WA_TOKEN")
genai.configure(api_key=os.environ.get("GEN_API"))
phone_id = os.environ.get("PHONE_ID")

# --- 2. THE AI BRAIN SETUP ---
SYSTEM_RULES = "You are the Khalifa High School Result Agent. Look at result photos and answer students about grades."

# Using the most stable model name available
model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash"
)

MASTER_RESULTS = "No results have been uploaded by the teacher yet."
app = Flask(__name__)

def send_wa(recipient, answer):
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {'Authorization': f'Bearer {wa_token}', 'Content-Type': 'application/json'}
    data = {"messaging_product": "whatsapp", "to": f"{recipient}", "type": "text", "text": {"body": str(answer)}}
    requests.post(url, headers=headers, json=data)

@app.route("/", methods=["GET", "POST"])
def index():
    return "Khalifa Bot Active"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    global MASTER_RESULTS
    if request.method == "GET":
        if request.args.get("hub.verify_token") == "BOT":
            return request.args.get("hub.challenge")
        return "Failed", 403

    try:
        data = request.get_json()
        msg = data['entry'][0]['changes'][0]['value']['messages'][0]
        from_num = msg['from']

        if "image" in msg:
            if from_num == TEACHER_NUMBER:
                send_wa(from_num, "⏳ Reading...")
                media_id = msg["image"]["id"]
                media_url = requests.get(f"https://graph.facebook.com/v18.0/{media_id}/", headers={"Authorization": f"Bearer {wa_token}"}).json()["url"]
                img_data = requests.get(media_url, headers={"Authorization": f"Bearer {wa_token}"}).content
                
                # Simplified content generation
                response = model.generate_content([
                    "List names and grades from this photo.",
                    {"mime_type": "image/jpeg", "data": img_data}
                ])
                MASTER_RESULTS = response.text
                send_wa(from_num, "✅ Results memorized!")
            return "OK"

        query = msg['text']['body']
        ai_query = f"Data: {MASTER_RESULTS}. Answer student: {query}"
        response = model.generate_content(ai_query)
        send_wa(from_num, response.text)

    except Exception as e:
        print(f"Error: {e}")
            
    return "OK"

if __name__ == "__main__":
    app.run(debug=True, port=8000)
