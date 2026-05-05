import requests
import re
import json
import os
import time

def penny_precision_extractor(token):
    store_name = "Penny"
    output_dir = "outputs/raw_web"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/data_penny.json"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Rsc": "1",
        "Referer": "https://zgarcit.ro/"
    }

    all_products = []
    print(f"📡 Scanare de precizie pentru {store_name}...")

    # Penny are de obicei între 20 și 40 de pagini
    for page in range(1, 68):
        url = f"https://zgarcit.ro/?providers=Penny&page={page}&_rsc={token}"

        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code != 200: break

            raw_text = res.text.replace('\\"', '"').replace('\\/', '/')

            # Tăiem fluxul RSC în bucăți per produs
            chunks = re.split(r'(?="title":)', raw_text)

            page_items = 0
            for chunk in chunks[1:]:
                title_m = re.search(r'"title":"([^"]+)"', chunk)
                new_price_m = re.search(r'"newPrice":([\d\.]+)', chunk)
                old_price_m = re.search(r'"oldPrice":([\d\.]+)', chunk)
                img_m = re.search(r'"src":"([^"]+)"', chunk)
                card_m = re.search(r'"requiresVendorCard":(true|false)', chunk)

                if title_m and new_price_m and img_m:
                    name = title_m.group(1).replace('È™', 'ș').replace('È›', 'ț').replace('Ã®', 'î').replace('Ã¢', 'â').replace('u0026', '&')

                    p_new = float(new_price_m.group(1))
                    p_old = float(old_price_m.group(1)) if old_price_m else None

                    # Calcul discount
                    discount_val = 0
                    if p_old and p_old > p_new:
                        discount_val = round(1 - (p_new / p_old), 2)

                    img_url = img_m.group(1)
                    if "tabler" in img_url.lower() or "logo" in img_url.lower():
                        continue

                    all_products.append({
                        "store": store_name,
                        "raw_name": name,
                        "price_new": p_new,
                        "price_old": p_old,
                        "discount": discount_val,
                        "requires_card": card_m.group(1) == "true" if card_m else False,
                        "image_url": img_url,
                        "local_image_path": f"data/images/penny/{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}.jpg"
                    })
                    page_items += 1

            if page_items == 0: break
            print(f"📦 P{page} | Total {store_name}: {len(all_products)}", end="\r")
            time.sleep(0.5)

        except Exception as e:
            print(f"\n❌ Eroare: {e}")
            break

    if all_products:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(all_products, f, indent=4, ensure_ascii=False)
        print(f"\n\n✨ SUCCES! Fișier creat: {filename} ({len(all_products)} produse)")
    else:
        print("\n💀 Token expirat sau Penny nu a returnat date. Dă un refresh în Opera!")

if __name__ == "__main__":
    TOKEN = "1godm"
    penny_precision_extractor(TOKEN)