import json
import os
import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor

# 1. Configurare Căi
REFINED_DIR = "outputs/refined"
RAW_DIR = "outputs/raw_web"
TARGET_BASE_DIR = "outputs/data/images_fixed"
MISSING_LOG = "missing_images.txt"

def slugify(text):
    if not text: return "produs_fara_nume"
    text = text.lower()
    # Păstrăm caracterele românești dacă vrei, sau le curățăm complet:
    text = re.sub(r'[^a-z0-9]+', '_', text).strip('_')
    return text[:60]

def download_image(url, target_path):
    """Funcție separată pentru descărcare cu retry logic."""
    if os.path.exists(target_path):
        return True # Deja există

    try:
        # User-Agent-ul păcălește site-urile care blochează scripturile simple
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            with open(target_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False

def sync_store_images(file_name):
    store_name = file_name.replace("refined_data_", "").replace(".json", "")
    refined_path = os.path.join(REFINED_DIR, file_name)
    raw_path = os.path.join(RAW_DIR, f"data_{store_name}.json")
    target_store_dir = os.path.join(TARGET_BASE_DIR, store_name)

    os.makedirs(target_store_dir, exist_ok=True)

    print(f"\n🚀 Start: {store_name.upper()}")

    with open(refined_path, "r", encoding="utf-8") as f:
        refined_products = json.load(f)

    # Lookup rapid în datele brute
    raw_lookup = {}
    if os.path.exists(raw_path):
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            for p in raw_data:
                name = p.get('raw_name', '')
                url = p.get('image_url') or p.get('image')
                if name and url: raw_lookup[name] = url

    download_count = 0

    for prod in refined_products:
        url = prod.get("image_url") or raw_lookup.get(prod.get('raw_name', ''), None)

        if not url:
            with open(MISSING_LOG, "a", encoding="utf-8") as err_file:
                err_file.write(f"Store: {store_name} | Product: {prod['name']}\n")
            continue

        clean_filename = f"{slugify(prod['name'])}.jpg"
        target_path = os.path.join(target_store_dir, clean_filename)

        # Actualizăm calea relativă pentru baza de date
        prod['image_local'] = f"data/images_fixed/{store_name}/{clean_filename}"

        if download_image(url, target_path):
            download_count += 1
            if download_count % 10 == 0:
                print(f"  📦 {store_name}: {download_count} poze procesate...", end="\r")

    # Salvăm JSON-ul ACTUALIZAT cu noile căi locale
    with open(refined_path, "w", encoding="utf-8") as f:
        json.dump(refined_products, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Finalizat {store_name}: {download_count} imagini salvate.")

def run():
    if not os.path.exists(REFINED_DIR):
        print("❌ Folderul refined nu există!")
        return

    if os.path.exists(MISSING_LOG): os.remove(MISSING_LOG) # Reset log

    files = [f for f in os.listdir(REFINED_DIR) if f.startswith("refined_data_") and f.endswith(".json")]

    for f in files:
        sync_store_images(f)

if __name__ == "__main__":
    run()