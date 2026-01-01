import os
import requests
import threading
import time
from flask import Flask
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# --- BEÁLLÍTÁSOK ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
INPUT_FILE = "proxy.txt"
RESULT_FILE = "mukodo_proxyk.txt"
THREADS = 50   # Kevesebb szál, hogy stabilabb legyen Renderen
TIMEOUT = 5    
REPORT_EVERY = 100 # Sűrűbb jelentés, hogy lásd a haladást

processed_count = 0
working_proxies = []
lock = threading.Lock()

def send_discord_msg(text):
    if DISCORD_WEBHOOK_URL:
        try: requests.post(DISCORD_WEBHOOK_URL, json={"content": text}, timeout=5)
        except: pass

def check_logic():
    global processed_count
    if not os.path.exists(INPUT_FILE):
        send_discord_msg("❌ Hiba: proxy.txt nem található a GitHubon!")
        return

    with open(INPUT_FILE, "r") as f:
        proxies = list(set([l.strip() for l in f if l.strip()]))

    total = len(proxies)
    send_discord_msg(f"🚀 **Ellenőrzés elindult!** (Összesen: {total} proxy)")

    def validate(addr):
        global processed_count
        for proto in ["http", "https", "socks5", "socks4"]:
            url = f"{proto}://{addr}"
            try:
                r = requests.get("https://httpbin.org/ip", proxies={"http": url, "https": url}, timeout=TIMEOUT)
                if r.status_code == 200:
                    with lock: working_proxies.append(addr)
                    break
            except: continue
        
        with lock:
            processed_count += 1
            # Discord jelentés 100-asával
            if processed_count % REPORT_EVERY == 0:
                send_discord_msg(f"⏳ **Haladás:** {processed_count}/{total} kész. (Talált: {len(working_proxies)})")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(validate, proxies)

    # Végső fájl küldése
    if working_proxies:
        with open(RESULT_FILE, "w") as f: f.write("\n".join(working_proxies))
        with open(RESULT_FILE, "rb") as f:
            requests.post(DISCORD_WEBHOOK_URL, data={"content": "✅ **KÉSZ!**"}, files={"file": (RESULT_FILE, f, "text/plain")})
    else:
        send_discord_msg("❌ Vége, nem találtam semmit.")

@app.route('/')
def home():
    return f"Dolgozom... {processed_count} ellenőrizve."

if __name__ == "__main__":
    threading.Thread(target=check_logic, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
