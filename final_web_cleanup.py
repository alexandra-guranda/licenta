import json
import glob
import os
import re

def fix_romanian_encoding(text):
    if not text:
        return ""

    # Dicționar de reparație pentru mojibake (UTF-8 interpretat greșit)
    # Acoperă toate variantele: raÈ›Äƒ, pÃ¢ine, Î®nchis, etc.
    replacements = {
        # Litere mici
        'Äƒ': 'ă', 'Ãă': 'ă', 'Âă': 'ă', 'Ä\x83': 'ă',
        'Ã¢': 'â', 'Ââ': 'â', 'Î¶': 'â',
        'Ã®': 'î', 'Âî': 'î', 'Î®': 'î',
        'È™': 'ș', 'Âș': 'ș', 'Ãș': 'ș', 'Å\x9f': 'ș',
        'È›': 'ț', 'Âț': 'ț', 'Ãț': 'ț', 'Å£': 'ț',

        # Litere mari
        'Ä\x82': 'Ă', 'Ã\x82': 'Â', 'Ã\x8e': 'Î',
        'È\x98': 'Ș', 'È\x9a': 'Ț',

        # Caractere speciale și HTML entities
        'u0026': '&', '&amp;': '&', 'Ã\x97': '×',
        'Â': '', # De multe ori 'Â' apare ca prefix parazit
    }

    for wrong, right in replacements.items():
        text = text.replace(wrong, right)

    # Eliminăm spațiile multiple și curățăm capetele
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def merge_and_clean():
    input_folder = "outputs/raw_web/*.json"
    files = glob.glob(input_folder)

    all_products = []
    report = {}

    print("🚀 Pornim curățarea generală...")

    for file_path in files:
        # Extragem numele magazinului din numele fișierului
        store_key = os.path.basename(file_path).replace("data_", "").replace(".json", "")

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for item in data:
                    # REPARAȚIA NUMELUI
                    item['raw_name'] = fix_romanian_encoding(item['raw_name'])

                    # ASIGURARE DISCOUNT (dacă a scăpat vreunul cu 0)
                    if item.get('price_old') and item['price_old'] > item['price_new']:
                        item['discount'] = round(1 - (item['price_new'] / item['price_old']), 2)

                    all_products.append(item)

                report[store_key.capitalize()] = len(data)
                print(f"✅ {store_key.capitalize()}: {len(data)} produse procesate.")
            except Exception as e:
                print(f"❌ Eroare la {file_path}: {e}")

    # Salvarea bazei de date finale
    output_path = "outputs/BAZA_DATE_FINALA_LICENTA.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=4, ensure_ascii=False)

    print("\n" + "="*40)
    print(f"🎉 FINALIZAT! Baza de date este gata.")
    print(f"📁 Fișier: {output_path}")
    print(f"📦 Total produse unificate: {len(all_products)}")
    print("="*40)
    for store, count in report.items():
        print(f"📍 {store:12} | {count:>5} produse")

if __name__ == "__main__":
    merge_and_clean()