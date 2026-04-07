from flask import Flask, request
import requests
import os
import time
from datetime import datetime
import google.generativeai as genai

app = Flask(__name__)

# Configurație
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
    except:
        pass

def analyze_with_ai(token_data):
    prompt = f"""
    Analizează acest memecoin nou de pe Solana și spune dacă merită atenție.

    Nume: {token_data.get('name', 'Unknown')}
    Simbol: {token_data.get('symbol', 'N/A')}
    MCAP: {token_data.get('mcap', 'N/A')}
    Volum 5m: {token_data.get('volume5m', 'N/A')}
    Volum 1h: {token_data.get('volume1h', 'N/A')}

    Răspunde scurt în română:
    - Are potențial de 2x sau mai mult? (DA/NU + motiv)
    - Risc scam? (DA/NU)
    - Scor general 1-10:
    """

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "Eroare la analiză AI."

@app.route('/')
def home():
    return "Botul rulează! Verifică la fiecare 15 minute."

@app.route('/scan')
def scan():
    try:
        response = requests.get("https://api.dexscreener.com/latest/dex/search?q=solana")
        data = response.json()

        pairs = data.get("pairs", [])[:10]  # luăm primele 10 pentru viteză

        for pair in pairs:
            if not pair or not pair.get("baseToken"):
                continue

            fdv = pair.get("fdv") or pair.get("marketCap") or 0
            volume5m = pair.get("volume", {}).get("m5", 0)
            volume1h = pair.get("volume", {}).get("h1", 0)

            if fdv >= 8000 and fdv <= 300000 and (volume5m > 1500 or volume1h > 8000):
                token_data = {
                    "name": pair["baseToken"].get("name", "Unknown"),
                    "symbol": pair["baseToken"].get("symbol", "N/A"),
                    "mcap": round(fdv / 1000),
                    "volume5m": round(volume5m / 1000),
                    "volume1h": round(volume1h / 1000),
                    "url": f"https://dexscreener.com/solana/{pair.get('pairAddress', '')}"
                }

                ai_analysis = analyze_with_ai(token_data)

                message = f"""🚨 <b>AI Semnal Memecoin Solana</b>

{token_data['name']} ({token_data['symbol']})
MCAP: ~{token_data['mcap']}k
Volum 5m: ~{token_data['volume5m']}k
Volum 1h: ~{token_data['volume1h']}k

AI Analiză:
{ai_analysis}

🔗 {token_data['url']}

DYOR! Nu e sfat financiar."""

                send_telegram_message(message)
                time.sleep(2)  # pauză între mesaje

        return "Scan completat."
    except Exception as e:
        return f"Eroare: {str(e)}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
