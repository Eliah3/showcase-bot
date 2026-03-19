# 🤖 KI-Bot System

Ein Server für beliebig viele Kunden-Bots.

## Repository Struktur

```
ki-bots/
├── server.py              ← Haupt-Server (einmalig)
├── requirements.txt       ← Python Pakete (einmalig)
├── render.yaml            ← Render Konfiguration (einmalig)
├── neuer_kunde.py         ← Script für neue Kunden
└── kunden/
    ├── zahlengrafik/
    │   ├── infos.txt      ← Firmen-Infos (hier anpassen!)
    │   └── demo.html      ← Demo-Seite
    ├── mueller-gmbh/
    │   ├── infos.txt
    │   └── demo.html
    └── ...
```

## Neuen Kunden hinzufügen

```bash
python neuer_kunde.py --url https://www.kunde.de --name "Müller GmbH" --render-url https://showcase-bot.onrender.com
```

→ Erstellt automatisch `kunden/mueller-gmbh/` mit `infos.txt` und `demo.html`
→ Auf GitHub pushen → Render deployed automatisch

## Demo-URLs

```
https://showcase-bot.onrender.com/                  → Übersicht
https://showcase-bot.onrender.com/zahlengrafik       → ZahlenGrafik Demo
https://showcase-bot.onrender.com/mueller-gmbh       → Müller GmbH Demo
```

## Setup

1. Dieses Repo auf GitHub hochladen
2. Auf render.com als Web Service verbinden
3. `NVIDIA_API_KEY` als Umgebungsvariable setzen
4. Deploy!
