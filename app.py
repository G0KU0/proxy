import os
import requests
import threading
import time
from flask import Flask
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# --- BEÁLLÍTÁSOK (38.000 proxyhoz optimalizálva) ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
INPUT_FILE = "proxy.txt"
RESULT_FILE = "mukodo_proxyk.txt"

THREADS = 20    # Kevesebb szál = nagyobb stabilitás a Renderen
TIMEOUT = 5     # 5 másodpercnél többet nem várunk
REPORT_EVERY = 50 # Sűrűbb jelentés, hogy lásd, ha halad

processed_count = 0
working_proxies = []
lock = threading.Lock()

def send_discord_msg(text):
    if DISCORD_WEBHOOK_URL:
        try:
            # Rövid timeout, hogy ne blokkolja a scriptet
            requests.post(DISCORD_WEBHOOK_URL, json={"content": text}, timeout=5)
        except:
            pass

def check_logic():
    global processed_count
    if not os.path.exists(INPUT_FILE):
        print("Hiba: proxy.txt nem található!")
        return

    # Fájl beolvasása
    with open(INPUT_FILE, "r") as f:
        proxies = list(set([l.strip() for l in f if l.strip()]))

    total = len(proxies)
    # AZONNALI ÜZENET: Ha ezt megkapod, a webhook jól működik!
    send_discord_msg(f"✅ **Szerver elindult!** 38k proxy ellenőrzése kezdődik (20 szálon).")

    def validate(addr):
        global processed_count
        # Csak HTTP és SOCKS5-öt nézünk az erőforrások kímélése miatt
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
            # Render logba minden 10 után írunk
            if processed_count % 10 == 0:
                print(f"Haladás: {processed_count}/{total}")
            
            # Discordra REPORT_EVERY (50) után küldünk
            if processed_count % REPORT_EVERY == 0:
                send_discord_msg(f"⏳ {processed_count}/{total} kész. (Működő: {len(working_proxies)})")

    # Szálkezelő indítása
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(validate, proxies)

    # Végső fájl küldése a legvégén
    if working_proxies:
        with open(RESULT_FILE, "w") as f:
            f.write("\n".join(working_proxies))
        with open(RESULT_FILE, "rb") as f:
            requests.post(DISCORD_WEBHOOK_URL, 
                          data={"content": "🏁 **VÉGEZTEM!** Itt a teljes lista:"}, 
                          files={"file": (RESULT_FILE, f, "text/plain")}, timeout=10)
    else:
        send_discord_msg("❌ Lefutott, de nem találtam működő proxyt.")

@app.route('/')
def home():
    # Ez a válasz kell a Rendernek, hogy tudja: él a szerver
    return f"ONLINE - Ellenőrizve: {processed_count}"

if __name__ == "__main__":
    # Azonnal indítjuk a háttérszálat
    t = threading.Thread(target=check_logic)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
