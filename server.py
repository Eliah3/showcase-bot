#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "NVIDIA_API_KEY_HIER")

def load_infos():
    try:
        with open("infos.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Keine Firmen-Infos gefunden."

SYSTEM_PROMPT = """Du bist der freundliche KI-Assistent von {firma}.
Beantworte Fragen ausschliesslich basierend auf den folgenden Firmen-Informationen.
Antworte immer auf Deutsch, kurz (2-3 Saetze) und freundlich.
Bei Fragen ausserhalb deines Wissens verweise auf den direkten Kontakt.

FIRMEN-INFORMATIONEN:
{{infos}}
""".format(firma="Logopädie Bisch", infos=load_infos())


@app.route("/")
def index():
    return send_file("demo.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_message = data.get("message", "")
        history = data.get("history", [])

        messages = [{{"role": "system", "content": SYSTEM_PROMPT}}]
        messages += history
        messages.append({{"role": "user", "content": user_message}})

        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={{
                "Content-Type": "application/json",
                "Authorization": f"Bearer {{NVIDIA_API_KEY}}"
            }},
            json={{
                "model": "meta/llama-3.1-70b-instruct",
                "max_tokens": 400,
                "messages": messages
            }},
            timeout=30
        )

        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        return jsonify({{"reply": reply}})

    except Exception as e:
        print(f"Fehler: {{e}}")
        return jsonify({{"reply": "Fehler. Bitte versuchen Sie es erneut."}}), 500


if __name__ == "__main__":
    print("\n✅ Server läuft auf http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
