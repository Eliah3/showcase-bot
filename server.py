#!/usr/bin/env python3
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, os

app = Flask(__name__)
CORS(app)

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "NVIDIA_API_KEY_HIER")
KUNDEN_DIR = "kunden"

def get_kunden():
    if not os.path.exists(KUNDEN_DIR):
        return []
    return [d for d in os.listdir(KUNDEN_DIR) if os.path.isdir(f"{KUNDEN_DIR}/{d}")]

def load_infos(kunde):
    try:
        with open(f"{KUNDEN_DIR}/{kunde}/infos.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return None

def load_demo(kunde):
    try:
        with open(f"{KUNDEN_DIR}/{kunde}/demo.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return None

@app.route("/")
def index():
    kunden = get_kunden()
    links = "".join([f'<li><a href="/{k}">{k}</a></li>' for k in kunden])
    return f"""<!DOCTYPE html><html lang="de"><head><meta charset="UTF-8"><title>KI-Bot Demos</title>
    <style>body{{font-family:sans-serif;max-width:600px;margin:60px auto;padding:0 20px}}h1{{color:#5b7fff}}li{{margin:10px 0;font-size:1.1rem}}a{{color:#5b7fff}}</style>
    </head><body><h1>🤖 KI-Bot Demos</h1><p>Verfügbare Kunden:</p><ul>{links}</ul></body></html>"""

@app.route("/<kunde>")
def demo(kunde):
    html = load_demo(kunde)
    if not html:
        return f"Kunde '{kunde}' nicht gefunden.", 404
    return html

@app.route("/<kunde>/chat", methods=["POST"])
def chat(kunde):
    infos = load_infos(kunde)
    if not infos:
        return jsonify({"reply": f"Kunde '{kunde}' nicht gefunden."}), 404
    try:
        data = request.json
        user_message = data.get("message", "")
        history = data.get("history", [])
        system_prompt = f"Du bist ein freundlicher KI-Assistent. Beantworte Fragen nur basierend auf diesen Firmen-Infos. Antworte auf Deutsch, kurz und freundlich.\n\nFIRMEN-INFORMATIONEN:\n{infos}"
        messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {NVIDIA_API_KEY}"},
            json={"model": "meta/llama-3.1-70b-instruct", "max_tokens": 400, "messages": messages},
            timeout=30
        )
        reply = response.json()["choices"][0]["message"]["content"]
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"Fehler: {e}")
        return jsonify({"reply": "Fehler. Bitte erneut versuchen."}), 500

if __name__ == "__main__":
    print(f"\n✅ Server läuft: http://localhost:5000")
    for k in get_kunden():
        print(f"   → http://localhost:5000/{k}")
    app.run(host="0.0.0.0", port=5000, debug=False)
