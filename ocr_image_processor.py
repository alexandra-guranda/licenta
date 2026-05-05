import easyocr
import json
import os
import time
import re

class OCRImageProcessor:
    def __init__(self):
        print("🔄 Inițializare EasyOCR (Romanian)...")
        # Folosim detail=1 pentru a primi coordonatele textului în pagină
        self.reader = easyocr.Reader(['ro'])
        self.input_folder = "inputs"
        self.output_folder = "outputs"

        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def clean_price(self, price_str):
        # Transformă "17,59" sau "17.59" în float 17.59
        price_str = price_str.replace(',', '.')
        try:
            return float(re.sub(r'[^\d.]', '', price_str))
        except:
            return 0.0

    def process_images(self):
        final_results = []
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
        files = [f for f in os.listdir(self.input_folder) if f.lower().endswith(valid_extensions)]

        if not files:
            print(f"⚠️ Folderul '{self.input_folder}' este gol.")
            return

        for file_name in files:
            print(f"📸 Procesare Standalone OCR: {file_name}...")
            file_path = os.path.join(self.input_folder, file_name)

            # Citim textul cu detalii (coordonate)
            # result arată așa: [([[x,y], [x,y]...], 'text', probabilitate), ...]
            result = self.reader.readtext(file_path)

            for i, (bbox, text, prob) in enumerate(result):
                # Căutăm ceva ce seamănă a preț (ex: 12,99 sau 5.49)
                if re.search(r'\d+[\.,]\d{2}', text):
                    price_new = self.clean_price(text)

                    # Pentru numele produsului, ne uităm la textul de deasupra sau din stânga
                    # (În OCR brut, de obicei e elementul anterior din listă)
                    raw_name = result[i-1][1] if i > 0 else "Produs Necunoscut"

                    # Logică simplă pentru preț vechi (dacă există un alt număr înainte)
                    price_old = 0.0
                    if i > 1 and re.search(r'\d+[\.,]\d{2}', result[i-1][1]):
                        price_old = price_new
                        price_new = self.clean_price(result[i-1][1])
                        raw_name = result[i-2][1] if i > 1 else "Produs"

                    # Calculăm restul câmpurilor pentru a respecta formatul
                    discount = round(1 - (price_new / price_old), 2) if price_old > 0 else 0.0

                    # Detectăm cardul după cuvinte cheie în textul brut
                    requires_card = any(word in raw_name.lower() or word in text.lower()
                                        for word in ["card", "club", "connect", "plus"])

                    item = {
                        "store": file_name.split('_')[0].split('.')[0].capitalize(),
                        "raw_name": raw_name.strip(),
                        "price_new": price_new,
                        "price_old": price_old if price_old > 0 else price_new, # Fallback
                        "discount": discount,
                        "requires_card": requires_card,
                        "captured_at": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    final_results.append(item)

        # Salvăm fișierul EXACT în formatul de pe site
        output_path = os.path.join(self.output_folder, "standalone_ocr_results.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_results, f, indent=4, ensure_ascii=False)

        print(f"📂 GATA! Fișierul pentru comparație a fost creat: {output_path}")

if __name__ == "__main__":
    processor = OCRImageProcessor()
    processor.process_images()