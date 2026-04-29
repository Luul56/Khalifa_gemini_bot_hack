import os
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- 1. CONFIG & SECURITY ---
# Your Number (The Teacher)
TEACHER_NUMBER = "254112196147"

# API Setup
genai.configure(api_key=os.environ.get("GEN_API"))
WA_TOKEN = os.environ.get("WA_TOKEN")
PHONE_ID = os.environ.get("PHONE_ID")

# Using 'gemini-1.5-pro' because it's the most stable for v20.0 Meta API
model = genai.GenerativeModel('gemini-1.5-pro')

# Our "Database"
MASTER_RESULTS = "No results have been uploaded yet."

def send_wa(to, text):
    # UPDATED to v20.0 as per Meta's new policy
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WA_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": str(text)}
    }
    requests.post(url, json=payload, headers=headers)

@app.route("/", methods=['GET'])
def home():
    return "Khalifa High School Bot: ONLINE (v20.0)"

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    global MASTER_RESULTS
    
    # Verify Webhook
    if request.method == 'GET':
        if request.args.get("hub.verify_token") == "BOT":
            return request.args.get("hub.challenge")
        return "Verify Token Mismatch", 403

    # Handle Messages
    data = request.get_json()
    try:
        entry = data['entry'][0]['changes'][0]['value']
        if 'messages' in entry:
            message = entry['messages'][0]
            from_num = message['from']
            
            # --- TEACHER SENDS PHOTO ---
            if message['type'] == 'image':
                if from_num == TEACHER_NUMBER:
                    send_wa(from_num, "🔄 Updating school results... please wait.")
                    
                    media_id = message['image']['id']
                    # Get Image URL
                    img_info = requests.get(f"https://graph.facebook.com/v20.0/{media_id}/", headers={"Authorization": f"Bearer {WA_TOKEN}"}).json()
                    img_data = requests.get(img_info['url'], headers={"Authorization": f"Bearer {WA_TOKEN}"}).content
                    
                    # AI Process
                    response = model.generate_content([
                        "Read this result sheet and list names and grades clearly.",
                        {"mime_type": "image/jpeg", "data": img_data}
                    ])
                    MASTER_RESULTS = response.text
                    send_wa(from_num, "✅ DATABASE UPDATED. Students can now check results.")
                else:
                    send_wa(from_num, "❌ Only the school admin can upload results.")

            # --- STUDENT SENDS TEXT ---
            elif message['type'] == 'text':
                query = message['text']['body']
                ai_reply = model.generate_content(f"Context: {MASTER_RESULTS}. Task: Answer student's grade question politely: {query}")
                send_wa(from_num, ai_reply.text)

    except Exception as e:
        print(f"Log: {e}")
        
    return "OK", 200

if __name__ == "__main__":
    app.run(port=5000)
