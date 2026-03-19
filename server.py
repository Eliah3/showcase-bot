#!/usr/bin/env python3
"""
Lokaler Proxy Server fuer NVIDIA API + Website Demo
====================================================
Installation:
    pip install flask requests flask-cors

Verwendung:
    python server.py
    
Dann im Browser:
    http://localhost:5000
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# API Key aus Umgebungsvariable (sicher fuer GitHub/Render)
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "NVIDIA_API_KEY_HIER")

SYSTEM_PROMPT = """Du bist der KI-Assistent von ZahlenGrafik (zahlengrafik.de), Experte fuer JTL-Schnittstellen.
Produkte: JTL-Connectoren (Shopify, Billbee, WooCommerce, Otto, Zalando, Temu, Allegro, Galaxus u.v.m.), JTL-FFN Fulfillment, JTL-SCX.
Preise: Light 19EUR/Monat, Standard 69EUR, Premium 99EUR, Premium Plus 249EUR, Enterprise auf Anfrage.
Kontakt: +49 7221 92275-10, sales@zahlengrafik.io.
Antworte auf Deutsch, kurz (2-3 Saetze) und freundlich."""


@app.route("/")
def index():
    return send_file("demo_iframe.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_message = data.get("message", "")
        history = data.get("history", [])

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += history
        messages.append({"role": "user", "content": user_message})

        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {NVIDIA_API_KEY}"
            },
            json={
                "model": "meta/llama-3.1-70b-instruct",
                "max_tokens": 400,
                "messages": messages
            },
            timeout=30
        )

        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})

    except Exception as e:
        print(f"Fehler: {e}")
        return jsonify({"reply": "Fehler beim Verarbeiten. Bitte erneut versuchen."}), 500


if __name__ == "__main__":
    print("\n✅ Server läuft!")
    print("👉 Öffne im Browser: http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
