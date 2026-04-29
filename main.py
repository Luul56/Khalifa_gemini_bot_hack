import google.generativeai as genai
from flask import Flask, request, jsonify
import requests
import os

# --- 1. CONFIGURATION ---
# Replace with your phone number (Country code + number, NO + sign)
TEACHER_NUMBER = "254112196147" 

wa_token = os.environ.get("WA_TOKEN")
genai.configure(api_key=os.environ.get("GEN_API"))
phone_id = os.environ.get("PHONE_ID")

# --- 2. THE AI BRAIN SETUP ---
SYSTEM_RULES = """
You are the Khalifa High School Result Agent. 
Your job is to look at result photos uploaded by the teacher and answer students.
- Only the teacher (who sends photos) can update the database.
- Students send Admission Numbers. Look up their grades from the 'Master Results' text.
- Be professional and encouraging. If a student failed, be supportive.
"""

# UPDATED: Using the latest Gemini 3 Flash model
model = genai.GenerativeModel(
    model_name="gemini-3-flash",
    system_instruction=SYSTEM_RULES
)

# Global variable to act as the "Hard Drive" for the results
MASTER_RESULTS = "No results have been uploaded by the teacher yet."

app = Flask(__name__)

def send_wa(recipient, answer):
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    headers = {'Authorization': f'Bearer {wa_token}', 'Content-Type': 'application/json'}
    data = {
        "messaging_product": "whatsapp",
        "to": f"{recipient}",
        "type": "text",
        "text": {"body": str(answer)},
    }
    return requests.post(url, headers=headers, json=data)

@app.route("/", methods=["GET", "POST"])
def index():
    return "Khalifa Bot Active"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    global MASTER_RESULTS
    
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == "BOT":
            return challenge, 200
        return "Failed", 403

    elif request.method == "POST":
        try:
            msg_data = request.get_json()["entry"][0]["changes"][0]["value"]["messages"][0]
            from_num = msg_data["from"]
            msg_type = msg_data["type"]

            # --- CASE A: TEACHER UPLOADS PHOTO ---
            if msg_type == "image":
                if from_num == TEACHER_NUMBER:
                    send_wa(from_num, "⏳ Reading the result sheet... one moment.")
                    
                    # Get the image from Meta servers
                    media_id = msg_data["image"]["id"]
                    media_url_resp = requests.get(f'https://graph.facebook.com/v18.0/{media_id}/', headers={'Authorization': f'Bearer {wa_token}'})
                    media_url = media_url_resp.json()["url"]
                    img_bytes = requests.get(media_url, headers={'Authorization': f'Bearer {wa_token}'}).content
                    
                    # Send to Gemini to extract text
                    response = model.generate_content([
                        "Extract all student data (Names, IDs, Grades) from this image and list them clearly.", 
                        {"mime_type": "image/jpeg", "data": img_bytes}
                    ])
                    
                    MASTER_RESULTS = response.text
                    send_wa(from_num, "✅ Results memorized! Students can now check their grades.")
                else:
                    send_wa(from_num, "❌ Only the teacher can upload result sheets.")

            # --- CASE B: STUDENT SENDS TEXT (Admission Number) ---
            elif msg_type == "text":
                prompt = msg_data["text"]["body"]
                # AI looks at the master results and answers the student
                ai_query = f"System: Use these results: {MASTER_RESULTS}. Answer this student: {prompt}"
                response = model.generate_content(ai_query)
                send_wa(from_num, response.text)

        except Exception as e:
            print(f"Error: {e}")
            
        return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(debug=True, port=8000)
