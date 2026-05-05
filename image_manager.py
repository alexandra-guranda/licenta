import requests
import json
import os
import re
from tqdm import tqdm

class ImageManager:
    def __init__(self):
        self.output_dir = "outputs"
        self.image_base_path = "outputs/data/images"
        # Mapare logouri pentru produsele din PDF/OCR unde nu avem poze individuale
        self.placeholders = {
            "penny": "assets/logos/penny.png",
            "auchan": "assets/logos/auchan.png",
            "kaufland": "assets/logos/kaufland.png",
            "carrefour": "assets/logos/carrefour.png",
            "profi": "assets/logos/profi.png"
        }

        if not os.path.exists(self.image_base_path):
            os.makedirs(self.image_base_path)

    def slugify(self, text):
        return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')

    def download_image(self, url, product_name, store_name):
        """Descarcă pozele de pe Web (Zgârcit.ro)"""
        if not url or not url.startswith("http"):
            return None

        store_dir = os.path.join(self.image_base_path, store_name.lower())
        os.makedirs(store_dir, exist_ok=True)

        file_name = f"{self.slugify(product_name)}.jpg"
        local_path = os.path.join(store_dir, file_name)

        if os.path.exists(local_path):
            return local_path

        try:
            r = requests.get(url, timeout=10, stream=True)
            if r.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(r.content)
                return local_path
        except:
            return None
        return None

    def process_all_files(self):
        files = [f for f in os.listdir(self.output_dir) if f.endswith('_final_refined.json')]

        print(f"📸 Încep gestionarea imaginilor pentru {len(files)} fișiere...")

        for file_name in files:
            file_path = os.path.join(self.output_dir, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                products = json.load(f)

            print(f"📂 Procesez: {file_name}")
            for item in tqdm(products):
                store = item.get("store", "generic").lower()

                # 1. Dacă e produs de pe Web și are image_url, o descărcăm
                if "image_url" in item and item["image_url"]:
                    local = self.download_image(item["image_url"], item["raw_name"], store)
                    item["local_image_path"] = local if local else self.placeholders.get(store, "assets/no_image.png")

                # 2. Dacă e produs din PDF/OCR, îi punem direct logoul magazinului
                else:
                    item["local_image_path"] = self.placeholders.get(store, "assets/no_image.png")

            # Suprascriem fișierul cu noile căi locale de imagini
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(products, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    manager = ImageManager()
    manager.process_all_files()