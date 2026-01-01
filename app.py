import os
import requests
import threading
import time
from flask import Flask
from concurrent.futures import ThreadPoolExecutor

# --- KONFIGURÁCIÓ ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
INPUT_FILE = "proxy.txt"
RESULT_FILE = "mukodo_proxyk.txt"

# Beállítások nagy mennyiséghez
THREADS = 100  
TIMEOUT = 5    
REPORT_EVERY = 1000 # Most már minden 1000. proxy után küld jelentést Discordra

app = Flask(__name__)

# Számlálók és szálkezelés
processed_count = 0
working_proxies = []
lock = threading.Lock()

def send_discord_msg(text):
    if DISCORD_WEBHOOK_URL:
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": text})
        except: 
            pass

def send_discord_file():
    if not DISCORD_WEBHOOK_URL or not working_proxies:
        return
    try:
        # Fájl létrehozása a talált jó proxykkal
        with open(RESULT_FILE, "w") as f:
            f.write("\n".join(working_proxies))
        
        # Fájl és kísérő üzenet küldése
        with open(RESULT_FILE, "rb") as f:
            requests.post(DISCORD_WEBHOOK_URL, 
                          data={"content": f"✅ **KÉSZ!** Az összes proxy ellenőrizve.\nÖsszesen talált működő: **{len(working_proxies)}**"},
                          files={"file": (RESULT_FILE, f, "text/plain")})
        
        # Ideiglenes fájl törlése
        if os.path.exists(RESULT_FILE):
            os.remove(RESULT_FILE)
    except Exception as e:
        print(f"Hiba a fájlküldésnél: {e}")

def check_logic():
    global processed_count
    if not os.path.exists(INPUT_FILE):
        print(f"Hiba: {INPUT_FILE} nem található!")
        return

    with open(INPUT_FILE, "r") as f:
        proxies = list(set([l.strip() for l in f if l.strip()]))

    total = len(proxies)
    send_discord_msg(f"🚀 **Ellenőrzés elindult!**\nÖsszesen: {total} proxy\nBeállítás: 100 szál, jelentés minden 1000 után.")

    def validate(addr):
        global processed_count
        for proto in ["http", "https", "socks5", "socks4"]:
            url = f"{proto}://{addr}"
            try:
                # HTTPS tesztelés
                r = requests.get("https://httpbin.org/ip", proxies={"http": url, "https": url}, timeout=TIMEOUT)
                if r.status_code == 200:
                    with lock:
                        working_proxies.append(addr)
                    break # Ha találtunk működő protokollt, nem próbáljuk a többit
            except:
                continue
        
        with lock:
            processed_count += 1
            # Render log (konzol) frissítése minden 100 után
            if processed_count % 100 == 0:
                print(f"[PROGRESS] {processed_count}/{total} kész. ({len(working_proxies)} jó)")
            
            # Discord jelentés minden 1000 után
            if processed_count % REPORT_EVERY == 0:
                send_discord_msg(f"⏳ **Állapot:** {processed_count}/{total} ellenőrizve. (Eddig **{len(working_proxies)}** működőt találtam)")

    # Többszálú futtatás
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(validate, proxies)

    # A legvégén a teljes fájl küldése
    send_discord_file()

@app.route('/')
def health():
    return f"A rendszer dolgozik. Eddig lefutott: {processed_count} proxy."

def start_process():
    time.sleep(10) # Rövid várakozás az indítás után
    check_logic()

if __name__ == "__main__":
    # A fő folyamat külön szálon fut, hogy a Flask szerver ne blokkolódjon
    threading.Thread(target=start_process, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
