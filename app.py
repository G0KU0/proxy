import os
import requests
import threading
import time
from flask import Flask
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# --- KÖRNYEZETI VÁLTOZÓ ---
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

INPUT_FILE = "proxy.txt"
RESULT_FILE = "mukodo_proxyk.txt" # Ez lesz a fájl neve Discordon
TIMEOUT = 7
THREADS = 25
TEST_URL = "https://httpbin.org/ip"
PROTOCOLS = ["http", "https", "socks5", "socks4"]

def send_file_to_discord(filepath):
    if not DISCORD_WEBHOOK_URL:
        print("❌ HIBA: A DISCORD_WEBHOOK nincs beállítva!")
        return

    try:
        # Fájl küldése a Discord Webhook-on keresztül
        with open(filepath, "rb") as f:
            files = {
                "file": (filepath, f, "text/plain")
            }
            data = {
                "content": f"✅ **Proxy ellenőrzés kész!**\nIdőpont: {time.strftime('%Y-%m-%d %H:%M:%S')}\nA működő listát csatoltam fájlban."
            }
            response = requests.post(DISCORD_WEBHOOK_URL, data=data, files=files)
            
        if response.status_code in [200, 204]:
            print("🚀 Fájl sikeresen elküldve Discordra!")
        else:
            print(f"⚠️ Hiba a küldésnél: {response.status_code}")
    except Exception as e:
        print(f"❌ Webhook hiba: {e}")

def check_all_proxies():
    if not os.path.exists(INPUT_FILE):
        print(f"Hiba: {INPUT_FILE} nem található!")
        return

    with open(INPUT_FILE, "r") as f:
        lines = list(set([l.strip() for l in f if l.strip()]))

    print(f"Ellenőrzés indítása: {len(lines)} IP...")
    working_proxies = []

    def check_single(address):
        for proto in PROTOCOLS:
            proxy_url = f"{proto}://{address}"
            try:
                r = requests.get(TEST_URL, proxies={"http": proxy_url, "https": proxy_url}, timeout=TIMEOUT)
                if r.status_code == 200:
                    working_proxies.append(address) # Csak az IP:Port kerül mentésre
                    return
            except:
                continue

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(check_single, lines)

    # Ha vannak működő proxyk, elmentjük őket egy fájlba
    if working_proxies:
        with open(RESULT_FILE, "w") as f:
            f.write("\n".join(working_proxies))
        
        # Fájl elküldése
        send_file_to_discord(RESULT_FILE)
        
        # Opcionális: töröljük a szerverről a generált fájlt küldés után
        if os.path.exists(RESULT_FILE):
            os.remove(RESULT_FILE)
    else:
        # Ha nincs találat, csak egy sima üzenetet küldünk
        requests.post(DISCORD_WEBHOOK_URL, json={"content": "❌ Az ellenőrzés lefutott, de nem találtam működő proxyt."})

@app.route('/')
def home():
    return "A szerver fut. Az eredményeket fájlban küldjük Discordra."

def run_checker():
    time.sleep(10) # Hagyjunk időt a Rendernek felállni
    check_all_proxies()

if __name__ == "__main__":
    threading.Thread(target=run_checker, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
