import requests
import threading
from concurrent.futures import ThreadPoolExecutor

# --- BEÁLLÍTÁSOK ---
INPUT_FILE = "proxy.txt"
OUTPUT_FILE = "working.txt"
TIMEOUT = 7                   # Kicsit emeltem az időn a HTTPS/SSL kézfogás miatt
THREADS = 30                  # Szálak száma
TEST_URL = "https://httpbin.org/ip" # HTTPS-t tesztelünk!

# Az összes protokoll, amit végigpróbálunk
PROTOCOLS_TO_TRY = ["http", "https", "socks5", "socks4"]

def check_proxy(raw_line):
    line = raw_line.strip()
    if not line:
        return

    # 1. Protokoll és cím szétválasztása
    if "://" in line:
        protocol_part, address = line.split("://")
        types_to_test = [protocol_part]
    else:
        address = line
        types_to_test = PROTOCOLS_TO_TRY

    # 2. Végigpróbáljuk a típusokat (HTTP, HTTPS, SOCKS stb.)
    for proto in types_to_test:
        proxy_url = f"{proto}://{address}"
        
        # A requests-nek megadjuk, hogy mindkét típusú forgalmat ezen küldje
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        try:
            # Megpróbáljuk elérni a HTTPS teszt oldalt
            response = requests.get(TEST_URL, proxies=proxies, timeout=TIMEOUT)
            
            if response.status_code == 200:
                print(f"[+] MŰKÖDIK ({proto.upper()}): {address}")
                with open(OUTPUT_FILE, "a") as f:
                    f.write(address + "\n")
                return # Ha találtunk működő protokollt, nem próbáljuk a többit
        except:
            continue # Ha nem sikerült, jöhet a következő protokoll a listából

    print(f"[-] NEM MŰKÖDIK: {address}")

def main():
    # Előző eredmények törlése
    open(OUTPUT_FILE, "w").close()

    try:
        with open(INPUT_FILE, "r") as f:
            # Beolvasás és duplikátumok eltávolítása
            lines = list(set([l.strip() for l in f if l.strip()]))
    except FileNotFoundError:
        print(f"Hiba: A '{INPUT_FILE}' fájl nem található! Hozz létre egyet az IP-kkel.")
        return

    print(f"--- Ellenőrzés indítása: {len(lines)} IP tesztelése ---")
    print(f"Tesztelt típusok: {', '.join(PROTOCOLS_TO_TRY).upper()}")
    
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        executor.map(check_proxy, lines)

    print(f"\n--- Kész! A működő proxyk elmentve: {OUTPUT_FILE} ---")

if __name__ == "__main__":
    main()