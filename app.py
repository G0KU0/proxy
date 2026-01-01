import os
import requests
import threading
import time
from flask import Flask
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# --- KONFIGURÁCIÓ (Gyorsított mód) ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
INPUT_FILE = "proxy.txt"
RESULT_FILE = "mukodo_proxyk.txt"

THREADS = 200      # Megduplázott sebesség (25 helyett 50)
TIMEOUT = 3       # Gyorsabb továbbugrás (5 mp helyett 3 mp)
REPORT_EVERY = 5000 

processed_count = 0
working_proxies = []
lock = threading.Lock()

def send_discord_msg(text):
    if DISCORD_WEBHOOK_URL:
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": text}, timeout=5)
        except:
            pass

def send_discord_file():
    if not DISCORD_WEBHOOK_URL or not working_proxies:
        return
    try:
        with open(RESULT_FILE, "w") as f:
            f.write("\n".join(working_proxies))
        with open(RESULT_FILE, "rb") as f:
            requests.post(DISCORD_WEBHOOK_URL, 
                          data={"content": f"🏁 **VÉGEZTEM!**\nEllenőrizve: {processed_count} proxy.\nTalált működő: **{len(working_proxies)}**"}, 
                          files={"file": (RESULT_FILE, f, "text/plain")}, timeout=15)
        if os.path.exists(RESULT_FILE):
            os.remove(RESULT_FILE)
    except Exception as e:
        print(f"Hiba a fájlküldésnél: {e}")

def check_logic():
    global processed_count
    if not os.path.exists(INPUT_FILE):
        return

    with open(INPUT_FILE, "r") as f:
        proxies = list(set([l.strip() for l in f if l.strip()]))

    total = len(proxies)
    send_discord_msg(f"⚡ **Gyorsított indítás:** {total} proxy ellenőrzése kezdődik (50 szál, 3mp timeout).")

    def validate(addr):
        global processed_count
        # Csak a két leggyakoribb típust nézzük a sebességért
        for proto in ["http", "socks5"]:
            url = f"{proto}://{addr}"
            try:
                r = requests.get("https://httpbin.org/ip", proxies={"http": url, "https": url}, timeout=TIMEOUT)
                if r.status_code == 200:
                    with lock:
                        working_proxies.append(addr)
                    break
            except:
                continue
        
        with lock:
            processed_count += 1
            if processed_count % 500 == 0: # Render logba ritkábban írunk a CPU kímélése miatt
                print(f"Haladás: {processed_count}/{total}")
            
            if processed_count % REPORT_EVERY == 0:
                send_discord_msg(f"⏳ **Állapot:** {processed_count}/{total} kész. (Eddig jó: {len(working_proxies)})")

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(validate, proxies)

    send_discord_file()

@app.route('/')
def home():
    return f"GYORSÍTOTT MÓD - {processed_count}/{processed_count if processed_count > 0 else '...'}"

if __name__ == "__main__":
    threading.Thread(target=check_logic, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
