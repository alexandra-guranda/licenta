import requests
import re
import json
import os
import time
from tqdm import tqdm

def run_ultimate_scraper(pages=67):
    all_products = []
    # !!! ATENȚIE: Verifică dacă 'vusbg' mai e în Opera acum !!!
    rsc_token = "vusbg"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Rsc": "1",
        "Referer": "https://zgarcit.ro/"
    }

    print(f"📡 Mod de scanare: Deep Text Extraction...")

    for page in range(1, pages + 1):
        url = f"https://zgarcit.ro/?providers=Auchan~Lidl~Mega Image~Penny~Carrefour~Profi~Kaufland&page={page}&_rsc={rsc_token}"

        try:
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code != 200: break

            content = res.text
            # Curățăm backslash-urile care "strică" Regex-ul
            clean_content = content.replace('\\"', '"').replace('\\/', '/')

            # --- EXTRACȚIE INDIVIDUALĂ ---
            # Căutăm orice text care urmează după "title":" sau "src":"
            titles = re.findall(r'"title":"([^"]+)"', clean_content)
            images = re.findall(r'"src":"([^"]+)"', clean_content)
            prices = re.findall(r'"newPrice":([\d\.]+)', clean_content)
            stores = re.findall(r'"provider":"([^"]+)"', clean_content)

            # Curățare caractere românești
            def clean_ro(text):
                return text.replace('È™', 'ș').replace('È›', 'ț').replace('Ã®', 'î').replace('Ã¢', 'â')

            # Aliniem listele (Metoda de siguranță)
            # Luăm lungimea minimă pentru a evita decalajele la finalul paginii
            count = min(len(titles), len(images), len(prices), len(stores))

            page_items = []
            for i in range(count):
                img_url = images[i]
                if "logo" in img_url.lower() or "tabler" in img_url:
                    continue

                name = clean_ro(titles[i])
                store = stores[i]

                # Generăm calea de salvare
                store_slug = store.lower().replace(" ", "_")
                clean_filename = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
                local_path = os.path.join("outputs/data/images", store_slug, f"{clean_filename}.jpg")

                page_items.append({
                    "store": store,
                    "raw_name": name,
                    "price_new": float(prices[i]),
                    "image_url": img_url,
                    "local_image_path": local_path
                })

            if page_items:
                all_products.extend(page_items)
                print(f"✅ Pagina {page}: {len(page_items)} produse găsite. Total: {len(all_products)}", end="\r")
            else:
                # Dacă nici așa nu merge, salvăm tot textul pentru analiză
                print(f"\n⚠️ Pagina {page} nu a putut fi descifrată.")
                with open("debug_raw.txt", "w", encoding="utf-8") as f:
                    f.write(content)
                return

            time.sleep(0.5)

        except Exception as e:
            print(f"\n❌ Eroare: {e}")
            break

    # --- SALVARE ȘI DESCĂRCARE ---
    if all_products:
        os.makedirs("outputs", exist_ok=True)
        with open("outputs/web_data_final.json", "w", encoding="utf-8") as f:
            json.dump(all_products, f, indent=4, ensure_ascii=False)

        print(f"\n\n📸 Începem descărcarea a {len(all_products)} imagini...")
        for prod in tqdm(all_products):
            os.makedirs(os.path.dirname(prod["local_image_path"]), exist_ok=True)
            if not os.path.exists(prod["local_image_path"]):
                try:
                    r = requests.get(prod["image_url"], timeout=10)
                    with open(prod["local_image_path"], 'wb') as f:
                        f.write(r.content)
                except: continue
        print("✨ Gata! Verifică folderul 'data/images'.")

if __name__ == "__main__":
    run_ultimate_scraper(67)