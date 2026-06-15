import json
import requests
import xml.etree.ElementTree as ET
import time
import threading
import os 
from datetime import datetime
from zoneinfo import ZoneInfo
from cacheManagement import CacheManager

JSON_FILE_PATH = "./exchange_data/exchageRatesCached.json"
FOLDER_PATH="./exchange_data/"
CHECK_INTERVAL_SECONDS = 60 
RETRY_DELAY_SECONDS = 60
CET_TZ = ZoneInfo("Europe/Paris")
cache = CacheManager()


def get_official_ecb_rates():
    url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    try:
        response = requests.get(url, timeout=7)
        if response.status_code == 200:
            print("tryong 1 ")
            root = ET.fromstring(response.text.encode("utf-8"))
            namespaces = {
                "gesmes": "http://gesmes.org",
                "ns": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
            }

            rates = {"EUR": 1.0}
            for cube in root.findall(".//ns:Cube", namespaces):
                currency_attr = cube.get("currency")
                rate_attr = cube.get("rate")
                if currency_attr is not None and rate_attr is not None:
                    curr = currency_attr.upper().strip()
                    rates[curr] = float(rate_attr)
            if "EUR" not in rates:
                raise ValueError("Corrupted data: Missing vital currency fields.")
            if len(rates) > 1:
                current_date_str = datetime.now(CET_TZ).strftime("%Y-%m-%d")
                payload = [rates, {"last_fetched_date": current_date_str}]
                cache.setCache(payload)
                os.makedirs(os.path.dirname(FOLDER_PATH), exist_ok=True)
                temp_file_path = f"{FOLDER_PATH}.tmp"
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=4, ensure_ascii=False)
                os.replace(temp_file_path, JSON_FILE_PATH)
                return True

    except Exception as e:
        print(f"Warning: Failed to fetch official ECB rates ({e}). Using last fetched data for calculations.")
    return False 


def get_last_fetched_date():
    if not os.path.exists(JSON_FILE_PATH):
        return None
    try:
        with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 1:
                return data[1].get("last_fetched_date")
    except Exception:
        pass
    return None

def _run_daemon():
    message = False
    while True:
        now = datetime.now(CET_TZ)
        current_date_str = now.strftime("%Y-%m-%d")
        last_fetched_date = get_last_fetched_date()
        if now.hour >= 16 and now.minute >= 30 and last_fetched_date != current_date_str:
            print(f"It is past 16:00 CET. Attempting API update...")
            success = get_official_ecb_rates()
            print(f"API Fetch Status: {success}")
            
            if not success:
                print(f"Fetch failed. Retrying in {RETRY_DELAY_SECONDS/60} minutes...")
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            else:
                cache.Renew = True
        elif os.path.exists(JSON_FILE_PATH):
            continue
        else:
            pass
        if not message:
            print("Started exchange update Loop")
            message = True
            
        
        time.sleep(CHECK_INTERVAL_SECONDS)
    



def initialiseDaemon():
    print("started exchange rate grab")
    api_call = threading.Thread(target=_run_daemon, daemon=True)
    api_call.start()

