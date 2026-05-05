import ollama
import json
import os

class Refiner:
    def __init__(self):
        self.input_dir = "outputs/raw_web"
        self.output_dir = "outputs/refined"
        os.makedirs(self.output_dir, exist_ok=True)
        self.model = "llama3.2:3b"

        self.categories = [
            "Panificatie & Dulciuri",
            "Carne & Mezeluri",
            "Lactate & Oua",
            "Legume & Fructe",
            "Bauturi",
            "Bacanie & Alimente de baza",
            "Ingrijire & Curatenie",
            "Casa & Diverse"
        ]

    def refine_batch(self, batch):
        mini_batch = [{"raw_name": x.get("raw_name")} for x in batch]
        prompt = f"""Esti expert in retail. Task: Extrage BRANDUL si CATEGORIA.
### CATEGORII PERMISE: {self.categories}
### REGULI:
1. BRAND: Doar numele propriu (ex: Milka, Napolact). Daca nu e clar, pune "Generic".
2. NUME_CURAT: Numele produsului fara brand.
3. FORMAT JSON: {{ "produse": [ {{ "nume_curat": "...", "brand": "...", "categorie": "..." }} ] }}
DATA: {json.dumps(mini_batch, ensure_ascii=False)}"""

        try:
            response = ollama.generate(model=self.model, prompt=prompt, format="json", options={"temperature": 0.1})
            return json.loads(response['response']).get("produse", [])
        except:
            return []

    def apply_emergency_rules(self, cat, raw_name):
        rn = raw_name.lower()

        if any(x in rn for x in ["bere", "suc", "apa", "vin", "pepsi", "cola", "santal", "nestea", "cafea", "nescafe", "jacobs", "3 in 1"]):
            return "Bauturi"

        if any(x in rn for x in ["detergent", "sapun", "pasta dinti", "absorbante", "gel de dus", "sampon", "pampers", "servetele umede", "protex", "colgate", "ariel", "vopsea oua"]):
            return "Ingrijire & Curatenie"

        if any(x in rn for x in ["iaurt", "lapte", "branza", "unt", "smantana", "kefir", "cascaval", "telemea", "danonino", "omu", "albalact"]):
            return "Lactate & Oua"

        if any(x in rn for x in ["salam", "parizer", "cremwursti", "sunca", "mici", "carnati", "scarita", "pate", "pui", "porc", "cotlet", "aripi", "mezel"]):
            return "Carne & Mezeluri"

        if any(x in rn for x in ["paine", "croissant", "chifla", "bagheta", "pernuta", "gogoasa", "ciocolata", "biscuiti", "eugenia", "napolitane", "bomboane", "milka", "oreo"]):
            return "Panificatie & Dulciuri"

        if any(x in rn for x in ["jucarie", "figurine", "audi", "excavator", "sosete", "pungi", "folie", "hartie copt", "prosop hartie", "caini", "pisici", "hrana animal"]):
            return "Casa & Diverse"

        if any(x in rn for x in ["ceapa", "mango", "cartofi", "mere", "banane", "rosii", "vinete", "varza", "legume", "fructe"]):
            return "Legume & Fructe"

        if any(x in rn for x in ["ulei", "faina", "zahar", "orez", "malai", "pasta tomate", "mustar", "ketchup", "conserve", "fasole"]):
            return "Bacanie & Alimente de baza"

        return cat if cat in self.categories else "Casa & Diverse"

    def process_file(self, filename):
        file_path = os.path.join(self.input_dir, filename)
        output_path = os.path.join(self.output_dir, f"refined_{filename}")
        if not os.path.exists(file_path): return

        print(f"Procesare: {filename}")
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        refined_store_data = []
        batch_size = 5

        for i in range(0, len(raw_data), batch_size):
            batch = raw_data[i:i+batch_size]
            ai_results = self.refine_batch(batch)

            for original, res in zip(batch, ai_results):
                raw_n = original.get("raw_name", "")

                temp_cat = res.get("categorie") or res.get("category") or "Casa & Diverse"
                final_cat = self.apply_emergency_rules(temp_cat, raw_n)

                ai_brand = res.get("brand")
                if ai_brand is None:
                    final_brand = "Generic"
                else:
                    final_brand = str(ai_brand).strip()

                if final_brand != "Generic" and " " in final_brand:
                    final_brand = final_brand.split()[0]

                refined_item = {
                    "store": original.get("store"),
                    "name": res.get("nume_curat") or raw_n,
                    "brand": final_brand,
                    "category": final_cat,
                    "price_new": original.get("price_new"),
                    "price_old": original.get("price_old"),
                    "discount": original.get("discount"),
                    "image_local": original.get("local_image_path") or original.get("image_local"),
                    "requires_card": original.get("requires_card", False),
                    "raw_name": raw_n
                }
                refined_store_data.append(refined_item)

            print(f"Status {filename}: {len(refined_store_data)}/{len(raw_data)}", end="\r")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(refined_store_data, f, indent=4, ensure_ascii=False)
        print(f"\nFinalizat: {output_path}")

if __name__ == "__main__":
    Refiner().process_file("data_profi.json")