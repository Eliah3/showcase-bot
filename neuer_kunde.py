#!/usr/bin/env python3
"""
🤖 KI-Chatbot Generator
========================
Erstellt automatisch einen KI-Chatbot für jede Website.

Installation:
    pip install requests beautifulsoup4

Verwendung:
    python neuer_kunde.py --url https://www.beispiel.de --name "Müller GmbH"

Was passiert automatisch:
    1. Website wird gescrapt
    2. Relevante Infos werden extrahiert
    3. infos.txt wird generiert
    4. server.py wird angepasst
    5. Alles wird in einen Ordner gepackt → fertig zum Upload auf GitHub
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os, re, argparse, time, shutil

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

# ============================================================
# SCHRITT 1 — Website scrapen
# ============================================================

def scrape_page(url):
    """Lädt eine einzelne Seite und extrahiert sauberen Text."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        # CSS, JS, Scripts entfernen
        for tag in soup(['script', 'style', 'nav', 'footer', 'head', 'noscript', 'iframe']):
            tag.decompose()

        # Nur relevante Tags nehmen
        texts = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'td', 'th', 'span', 'div']):
            text = tag.get_text(separator=' ', strip=True)
            # Nur sinnvolle Texte (min. 20 Zeichen, kein reiner CSS-Müll)
            if len(text) > 20 and not text.startswith(('.', '#', '@', '{')):
                texts.append(text)

        # Duplikate entfernen
        seen = set()
        unique = []
        for t in texts:
            if t not in seen:
                seen.add(t)
                unique.append(t)

        return '\n'.join(unique[:200])  # Max 200 Absätze

    except Exception as e:
        print(f"   ⚠️  Fehler beim Laden von {url}: {e}")
        return ""


def find_subpages(base_url, soup):
    """Findet relevante Unterseiten (Kontakt, Preise, Über uns etc.)."""
    keywords = ['kontakt', 'contact', 'preise', 'pricing', 'uber-uns', 'about',
                'leistungen', 'services', 'produkte', 'products', 'faq', 'impressum']
    
    links = set()
    domain = urlparse(base_url).netloc

    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        
        # Nur interne Links
        if parsed.netloc != domain:
            continue
        
        path = parsed.path.lower()
        if any(kw in path for kw in keywords):
            links.add(full_url)

    return list(links)[:5]  # Max 5 Unterseiten


def extract_contact_info(text):
    """Extrahiert Kontaktdaten per Regex."""
    info = {}

    # Telefon
    tel = re.findall(r'(?:\+49|0)[0-9\s\-\/]{8,20}', text)
    if tel:
        info['telefon'] = tel[0].strip()

    # E-Mail
    email = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    if email:
        info['email'] = email[0]

    # Adresse (PLZ + Stadt)
    adresse = re.findall(r'\d{5}\s+[A-ZÄÖÜ][a-zäöüß\s\-]+', text)
    if adresse:
        info['ort'] = adresse[0].strip()

    return info


# ============================================================
# SCHRITT 2 — infos.txt generieren
# ============================================================

def generate_infos(firma_name, url, scraped_text, contact_info):
    """Erstellt eine strukturierte infos.txt aus den gescrapten Daten."""

    kontakt_block = f"""## KONTAKT
Website: {url}"""
    
    if 'telefon' in contact_info:
        kontakt_block += f"\nTelefon: {contact_info['telefon']}"
    if 'email' in contact_info:
        kontakt_block += f"\nE-Mail: {contact_info['email']}"
    if 'ort' in contact_info:
        kontakt_block += f"\nOrt: {contact_info['ort']}"

    infos = f"""# FIRMEN-INFORMATIONEN FÜR DEN KI-ASSISTENTEN
# Firma: {firma_name}
# Website: {url}
# Automatisch generiert — bitte überprüfen und ergänzen!
# =============================================

## ÜBER UNS
{firma_name} ist ein Unternehmen mit folgenden Schwerpunkten:

{kontakt_block}

## WEBSITE-INHALT
{scraped_text[:6000]}

## ANWEISUNGEN FÜR DEN ASSISTENTEN
- Beantworte nur Fragen die mit {firma_name} zusammenhängen
- Verweise bei komplexen Fragen auf den direkten Kontakt
- Antworte immer freundlich und auf Deutsch
- Halte Antworten kurz (2-3 Sätze)
"""
    return infos


# ============================================================
# SCHRITT 3 — Projektordner erstellen
# ============================================================

SERVER_PY = '''#!/usr/bin/env python3
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
""".format(firma="{firma_name}", infos=load_infos())


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
    print("\\n✅ Server läuft auf http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
'''

DEMO_HTML = '''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{firma_name} – KI Demo</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ overflow: hidden; }}
  #site-frame {{ width: 100vw; height: 100vh; border: none; display: block; }}
  #zg-btn {{
    position: fixed; bottom: 28px; right: 28px; width: 62px; height: 62px;
    background: linear-gradient(135deg, #5b7fff, #7c9fff); border-radius: 50%;
    border: none; cursor: pointer; box-shadow: 0 4px 24px rgba(91,127,255,0.55);
    z-index: 2147483647; display: flex; align-items: center; justify-content: center;
    transition: transform 0.2s; animation: popIn 0.5s cubic-bezier(.34,1.56,.64,1) 1s both;
  }}
  @keyframes popIn {{ from{{transform:scale(0);opacity:0}} to{{transform:scale(1);opacity:1}} }}
  #zg-btn:hover {{ transform: scale(1.1); }}
  .notif {{ position: absolute; top: 3px; right: 3px; width: 13px; height: 13px; background: #ff6b6b; border-radius: 50%; border: 2px solid white; }}
  #zg-win {{
    position: fixed; bottom: 106px; right: 28px; width: 360px; height: 520px;
    background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.2);
    z-index: 2147483646; display: flex; flex-direction: column; overflow: hidden;
    transform: scale(0.85) translateY(20px); transform-origin: bottom right;
    opacity: 0; pointer-events: none;
    transition: transform 0.3s cubic-bezier(.34,1.3,.64,1), opacity 0.25s;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  #zg-win.open {{ transform: scale(1) translateY(0); opacity: 1; pointer-events: all; }}
  .zh {{ background: linear-gradient(135deg, #1a1a3e, #2d2d6e); padding: 16px; display: flex; align-items: center; gap: 12px; flex-shrink: 0; }}
  .zh-av {{ width: 40px; height: 40px; border-radius: 12px; background: linear-gradient(135deg, #5b7fff, #7c9fff); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.78rem; color: white; flex-shrink: 0; }}
  .zh-name {{ color: white; font-weight: 600; font-size: 0.9rem; }}
  .zh-status {{ display: flex; align-items: center; gap: 5px; margin-top: 3px; }}
  .zh-dot {{ width: 6px; height: 6px; background: #4ade80; border-radius: 50%; animation: blink 2s infinite; }}
  @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.3}} }}
  .zh-status span {{ font-size: 0.7rem; color: #a0b0d0; }}
  #zg-msgs {{ flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; background: #f8f9fc; scroll-behavior: smooth; }}
  #zg-msgs::-webkit-scrollbar {{ width: 3px; }}
  #zg-msgs::-webkit-scrollbar-thumb {{ background: #d0d0e0; border-radius: 2px; }}
  .zm {{ display: flex; gap: 8px; animation: slideUp 0.25s ease; }}
  @keyframes slideUp {{ from{{opacity:0;transform:translateY(8px)}} to{{opacity:1;transform:translateY(0)}} }}
  .zm.user {{ flex-direction: row-reverse; }}
  .zm-av {{ width: 28px; height: 28px; border-radius: 8px; background: linear-gradient(135deg,#5b7fff,#7c9fff); display: flex; align-items: center; justify-content: center; font-size: 0.6rem; font-weight: 700; color: white; flex-shrink: 0; align-self: flex-end; }}
  .zm.user .zm-av {{ background: #e0e0f0; color: #888; }}
  .zm-bubble {{ max-width: 80%; padding: 10px 13px; border-radius: 16px; font-size: 0.83rem; line-height: 1.55; }}
  .zm.bot .zm-bubble {{ background: white; color: #1a1a2e; border: 1px solid #e8e8f0; border-bottom-left-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
  .zm.user .zm-bubble {{ background: linear-gradient(135deg,#5b7fff,#7c9fff); color: white; border-bottom-right-radius: 4px; }}
  .typing-dots {{ display: flex; gap: 4px; align-items: center; }}
  .typing-dots span {{ width: 6px; height: 6px; background: #c0c0d0; border-radius: 50%; animation: dot 1.2s infinite; }}
  .typing-dots span:nth-child(2){{animation-delay:.15s}} .typing-dots span:nth-child(3){{animation-delay:.3s}}
  @keyframes dot {{ 0%,80%,100%{{transform:translateY(0)}} 40%{{transform:translateY(-6px)}} }}
  .zi {{ display: flex; align-items: center; gap: 8px; padding: 11px 13px; background: white; border-top: 1px solid #eee; flex-shrink: 0; }}
  .zi input {{ flex: 1; border: 1px solid #e0e0ea; border-radius: 22px; padding: 9px 15px; font-size: 0.83rem; outline: none; color: #1a1a2e; background: #f8f9fc; font-family: inherit; transition: border-color 0.2s; }}
  .zi input:focus {{ border-color: #5b7fff; background: white; }}
  .zi input::placeholder {{ color: #b0b0c8; }}
  .zi button {{ width: 36px; height: 36px; border-radius: 50%; border: none; background: linear-gradient(135deg,#5b7fff,#7c9fff); cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.15s; }}
  .zi button:hover {{ transform: scale(1.1); }}
  .zi button:disabled {{ opacity: 0.4; cursor: not-allowed; transform: none; }}
  .zb {{ text-align: center; padding: 5px; font-size: 0.6rem; color: #c0c0d0; background: white; flex-shrink: 0; }}
</style>
</head>
<body>
<iframe id="site-frame" src="{website_url}" title="{firma_name}"></iframe>
<button id="zg-btn" onclick="zgToggle()">
  <div class="notif"></div>
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
</button>
<div id="zg-win">
  <div class="zh">
    <div class="zh-av">KI</div>
    <div>
      <div class="zh-name">{firma_name} Assistent</div>
      <div class="zh-status"><div class="zh-dot"></div><span>Online · KI-Assistent</span></div>
    </div>
  </div>
  <div id="zg-msgs">
    <div class="zm bot">
      <div class="zm-av">KI</div>
      <div class="zm-bubble">Hallo! 👋 Ich bin der KI-Assistent von <b>{firma_name}</b>.<br><br>Wie kann ich Ihnen helfen?</div>
    </div>
  </div>
  <div class="zi">
    <input id="zg-inp" type="text" placeholder="Frage stellen …">
    <button id="zg-send">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
    </button>
  </div>
  <div class="zb">Powered by KI · {firma_name}</div>
</div>
<script>
  var isOpen = false, isLoading = false, chatHistory = [];
  function zgToggle() {{
    isOpen = !isOpen;
    document.getElementById("zg-win").classList.toggle("open", isOpen);
    if (isOpen) {{
      document.querySelector(".notif").style.display = "none";
      setTimeout(function() {{ document.getElementById("zg-inp").focus(); }}, 300);
    }}
  }}
  function addMsg(role, text) {{
    var c = document.getElementById("zg-msgs");
    var d = document.createElement("div");
    d.className = "zm " + role;
    d.innerHTML = "<div class=\\"zm-av\\">" + (role === "bot" ? "KI" : "Sie") + "</div>" +
      "<div class=\\"zm-bubble\\">" + text.replace(/\\n/g, "<br>") + "</div>";
    c.appendChild(d); c.scrollTop = c.scrollHeight;
  }}
  function addTyping() {{
    var c = document.getElementById("zg-msgs");
    var d = document.createElement("div");
    d.className = "zm bot"; d.id = "typing";
    d.innerHTML = "<div class=\\"zm-av\\">KI</div><div class=\\"zm-bubble\\"><div class=\\"typing-dots\\"><span></span><span></span><span></span></div></div>";
    c.appendChild(d); c.scrollTop = c.scrollHeight;
  }}
  async function sendMsg() {{
    var inp = document.getElementById("zg-inp");
    var text = inp.value.trim();
    if (!text || isLoading) return;
    isLoading = true;
    document.getElementById("zg-send").disabled = true;
    inp.value = "";
    addMsg("user", text);
    addTyping();
    try {{
      var res = await fetch("{render_url}/{slug}/chat", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ message: text, history: chatHistory }})
      }});
      var data = await res.json();
      var t = document.getElementById("typing"); if (t) t.remove();
      var reply = data.reply || "Bitte kontaktieren Sie uns direkt.";
      chatHistory.push({{ role: "user", content: text }});
      chatHistory.push({{ role: "assistant", content: reply }});
      addMsg("bot", reply);
    }} catch(e) {{
      var t = document.getElementById("typing"); if (t) t.remove();
      addMsg("bot", "⚠️ Server nicht erreichbar.");
    }}
    isLoading = false;
    document.getElementById("zg-send").disabled = false;
    inp.focus();
  }}
  document.getElementById("zg-send").addEventListener("click", sendMsg);
  document.getElementById("zg-inp").addEventListener("keydown", function(e) {{ if (e.key === "Enter") sendMsg(); }});
</script>
</body>
</html>'''

REQUIREMENTS = "flask\nflask-cors\nrequests\ngunicorn\n"

RENDER_YAML = """services:
  - type: web
    name: {slug}-bot
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn server:app --bind 0.0.0.0:$PORT
    envVars:
      - key: NVIDIA_API_KEY
        sync: false
"""

README = """# 🤖 KI-Chatbot für {firma_name}

Demo-URL: {render_url}

## Setup

1. Diesen Ordner auf GitHub hochladen
2. Auf render.com als Web Service verbinden
3. NVIDIA_API_KEY als Umgebungsvariable setzen
4. demo.html auf GitHub Pages hosten

## Infos anpassen

Einfach `infos.txt` bearbeiten — der Bot nutzt automatisch die neuen Infos
nach dem nächsten Deploy.
"""


def create_project(firma_name, url, render_url):
    """Erstellt den kompletten Projektordner."""
    
    # Ordnername aus Firmenname
    slug = re.sub(r'[^a-z0-9]', '-', firma_name.lower()).strip('-')
    folder = f"kunden/{slug}"
    
    os.makedirs(folder, exist_ok=True)
    
    print(f"\n📁 Erstelle Kundenordner: {folder}/")

    # 1. Website scrapen
    print(f"\n🌐 Scrape {url} ...")
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')
    main_text = scrape_page(url)
    
    # Unterseiten scrapen
    subpages = find_subpages(url, soup)
    all_text = main_text
    for sub_url in subpages:
        print(f"   📄 Scrape Unterseite: {sub_url}")
        all_text += "\n\n" + scrape_page(sub_url)
        time.sleep(0.5)

    # Kontaktdaten extrahieren
    contact = extract_contact_info(all_text)
    print(f"   📞 Gefunden: {contact}")

    # 2. infos.txt generieren
    infos = generate_infos(firma_name, url, all_text, contact)
    with open(f"{folder}/infos.txt", 'w', encoding='utf-8') as f:
        f.write(infos)
    print(f"   ✅ infos.txt erstellt")

    # 3. demo.html (goes in kunden folder)
    # 4. demo.html
    demo_code = DEMO_HTML.format(
        firma_name=firma_name,
        website_url=url,
        render_url=render_url
    )
    with open(f"{folder}/demo.html", 'w', encoding='utf-8') as f:
        f.write(demo_code)
    print(f"   ✅ demo.html erstellt")

    # Render URL in demo.html uses /<slug>/chat route


    # 5. requirements.txt
    with open("requirements.txt", 'w') as f:
        f.write(REQUIREMENTS)

    # 6. render.yaml
    render_yaml = RENDER_YAML.format(slug=slug)
    with open("render.yaml", 'w') as f:
        f.write(render_yaml)

    # 7. README
    readme = README.format(firma_name=firma_name, render_url=render_url)
    with open(f"{folder}/README.md", 'w', encoding='utf-8') as f:
        f.write(readme)

    print(f"\n{'='*50}")
    print(f"✅ FERTIG! Projektordner: {folder}/")
    print(f"\nDateien:")
    for f in os.listdir(folder):
        size = os.path.getsize(f"{folder}/{f}")
        print(f"   📄 kunden/{slug}/{f} ({size:,} Bytes)")
    print(f"\n📋 NÄCHSTE SCHRITTE:")
    print(f"   1. infos.txt prüfen und ggf. ergänzen")
    print(f"   2. Ordner '{folder}' auf GitHub hochladen")
    print(f"   3. Auf Render.com deployen")
    print(f"   4. NVIDIA_API_KEY in Render setzen")
    print(f"   5. demo.html auf GitHub Pages hosten")
    print(f"\n🔗 Demo-URL wird sein: {render_url}")
    print(f"{'='*50}\n")


# ============================================================
# HAUPTPROGRAMM
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KI-Chatbot Generator für Websites")
    parser.add_argument("--url",        required=True,  help="Website URL (z.B. https://www.kunde.de)")
    parser.add_argument("--name",       required=True,  help="Firmenname (z.B. 'Müller GmbH')")
    parser.add_argument("--render-url", default="https://DEIN-SERVICE.onrender.com", help="Render.com URL")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════╗
║     🤖 KI-Chatbot Generator          ║
╚══════════════════════════════════════╝
  Firma:  {args.name}
  URL:    {args.url}
  Render: {args.render_url}
""")

    create_project(
        firma_name=args.name,
        url=args.url,
        render_url=args.render_url
    )
