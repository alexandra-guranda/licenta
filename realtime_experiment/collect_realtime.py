"""
Experiment real-time — colectare date cu token RSC proaspat.
Salveaza rezultatele in realtime_experiment/outputs/ fara sa atinga datele principale.

Utilizare:
    python collect_realtime.py https://zgarcit.ro/?_rsc=p37cr
    python collect_realtime.py p37cr          # doar tokenul direct
"""

import sys
import re
import requests
import json
import os
import time
from pathlib import Path

# --- Configurare paths locale (nu atingem outputs/ din radacina proiectului) ---
BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "outputs" / "raw_web"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Rsc": "1",
    "Referer": "https://zgarcit.ro/",
}

STORES = {
    "Kaufland":    ("Kaufland",    120),
    "Lidl":        ("Lidl",         80),
    "Auchan":      ("Auchan",       80),
    "Mega Image":  ("Mega+Image",   60),
    "Penny":       ("Penny",        60),
    "Carrefour":   ("Carrefour",    60),
    "Profi":       ("Profi",        40),
}


def extract_token(arg: str) -> str:
    """Extrage tokenul din URL complet sau il returneaza direct daca e deja un token."""
    match = re.search(r'_rsc=([a-z0-9]+)', arg)
    if match:
        return match.group(1)
    # Daca nu gasim _rsc= in arg, presupunem ca e direct tokenul
    if re.fullmatch(r'[a-z0-9]+', arg):
        return arg
    raise ValueError(f"Nu am putut extrage tokenul din: {arg}")


def verify_token(token: str) -> bool:
    url = f"https://zgarcit.ro/?providers=Penny&page=1&_rsc={token}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return r.status_code == 200 and '"title"' in r.text
    except Exception:
        return False


def collect_store(store_name: str, provider_slug: str, max_pages: int, token: str) -> list:
    products = []
    slug = store_name.lower().replace(" ", "_")
    print(f"\n📡 Colectare {store_name}...")

    for page in range(1, max_pages + 1):
        url = f"https://zgarcit.ro/?providers={provider_slug}&page={page}&_rsc={token}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                break

            raw = r.text.replace('\\"', '"').replace('\\/', '/')
            chunks = re.split(r'(?="title":)', raw)

            page_items = 0
            for chunk in chunks[1:]:
                title_m    = re.search(r'"title":"([^"]+)"', chunk)
                new_price_m = re.search(r'"newPrice":([\d\.]+)', chunk)
                old_price_m = re.search(r'"oldPrice":([\d\.]+)', chunk)
                img_m      = re.search(r'"src":"([^"]+)"', chunk)
                card_m     = re.search(r'"requiresVendorCard":(true|false)', chunk)

                if not (title_m and new_price_m and img_m):
                    continue

                img_url = img_m.group(1)
                if "tabler" in img_url.lower() or "logo" in img_url.lower():
                    continue

                name  = title_m.group(1).replace('u0026', '&')
                p_new = float(new_price_m.group(1))
                p_old = float(old_price_m.group(1)) if old_price_m else None
                discount = round(1 - p_new / p_old, 2) if p_old and p_old > p_new else 0

                clean = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
                products.append({
                    "store":      store_name,
                    "raw_name":   name,
                    "price_new":  p_new,
                    "price_old":  p_old,
                    "discount":   discount,
                    "requires_card": card_m.group(1) == "true" if card_m else False,
                    "image_url":  img_url,
                    "image_local": f"data/images/{slug}/{clean}.jpg",
                })
                page_items += 1

            if page_items == 0:
                break
            print(f"  P{page}: {page_items} produse | Total: {len(products)}", end="\r")
            time.sleep(0.4)

        except Exception as e:
            print(f"\n  ❌ Eroare P{page}: {e}")
            break

    print(f"\n  {store_name}: {len(products)} produse")
    return products


def main():
    if len(sys.argv) < 2:
        print("Utilizare: python collect_realtime.py <URL_RSC_sau_token>")
        print("Exemplu:   python collect_realtime.py https://zgarcit.ro/?_rsc=p37cr")
        print("           python collect_realtime.py p37cr")
        sys.exit(1)

    try:
        token = extract_token(sys.argv[1])
    except ValueError as e:
        print(f" {e}")
        sys.exit(1)

    print(f"🔑 Token extras: {token}")

    if not verify_token(token):
        print("Tokenul nu functioneaza. Copiaza un URL proaspat din DevTools → Network → Rsc:1.")
        sys.exit(1)

    print("✅ Token valid!\n")

    # Colectare per magazin
    for store_name, (provider_slug, max_pages) in STORES.items():
        products = collect_store(store_name, provider_slug, max_pages, token)
        if products:
            slug = store_name.lower().replace(" ", "_")
            out_file = OUT_DIR / f"data_{slug}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(products, f, indent=4, ensure_ascii=False)
            print(f"  💾 Salvat: {out_file}")

    print(f"\n Gata! Jsonurile sunt in: {OUT_DIR}")
    print("Compara cu outputs/raw_web/ din radacina proiectului pentru a vedea diferentele.")


if __name__ == "__main__":
    main()
