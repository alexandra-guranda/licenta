import ollama
import json
import os
import re

INPUT_DIR  = "outputs"
OUTPUT_DIR = "outputs/refined"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MODEL = "llama3.2:3b"
BATCH_SIZE = 5

CATEGORIES = [
    "Panificatie & Dulciuri",
    "Carne & Mezeluri",
    "Lactate & Oua",
    "Legume & Fructe",
    "Bauturi",
    "Bacanie & Alimente de baza",
    "Ingrijire & Curatenie",
    "Casa & Diverse",
]

# Cuvinte care par branduri dar sunt tipuri de produs
FALSE_BRANDS = {
    "apa", "suc", "sos", "balsam", "crema", "salam", "branza", "paine",
    "lapte", "unt", "oua", "iaurt", "orez", "ulei", "zahar", "faina",
    "carne", "pui", "porc", "vita", "sunca", "parizer", "cafea", "ceai",
    "bere", "vin", "tort", "prajitura", "supa", "ciorba", "conserva",
    "capsule", "tablete", "pungi", "folie", "hartie", "prosop", "gel",
    "pasta", "sapun", "detergent", "sampon", "servetele", "scutece",
    "vaza", "perna", "halat", "baterie", "figurine", "jucarie", "sticks",
    "inghetata", "smantana", "cascaval", "telemea", "mozzarella",
}

GRAMAJ_RE = re.compile(
    r'\b\d+\s*(kg|g|ml|l|buc|bucati|role|pachete|portii|felii|litri)\b',
    re.IGNORECASE,
)


def ai_refine_batch(batch: list[dict]) -> list[dict]:
    mini = [{"raw_name": x.get("raw_name", "")} for x in batch]
    prompt = (
        f"Esti expert in retail romanesc. Extrage BRANDUL si CATEGORIA.\n"
        f"CATEGORII PERMISE: {CATEGORIES}\n"
        f"REGULI:\n"
        f"1. BRAND: Doar numele propriu al marcii (ex: Milka, Napolact, Kaufland). "
        f"Daca nu exista brand clar, pune 'Generic'.\n"
        f"2. NUME_CURAT: Numele produsului fara brand si fara gramaj.\n"
        f"3. FORMAT JSON: {{\"produse\": [{{\"nume_curat\": \"...\", \"brand\": \"...\", \"categorie\": \"...\"}}]}}\n"
        f"DATE: {json.dumps(mini, ensure_ascii=False)}"
    )
    try:
        r = ollama.generate(model=MODEL, prompt=prompt, format="json", options={"temperature": 0.1})
        return json.loads(r["response"]).get("produse", [])
    except Exception:
        return []


def fix_category(cat: str, raw_name: str) -> str:
    rn = raw_name.lower()

    if any(x in rn for x in ["bere", "suc ", "apa ", "vin ", "pepsi", "cola", "santal",
                               "cafea", "nescafe", "jacobs", "lipton", "sprite", "fanta",
                               "ceai ", "bautura", "red bull", "schweppes"]):
        return "Bauturi"
    if any(x in rn for x in ["detergent", "sapun", "pasta dinti", "absorbante", "gel de dus",
                               "sampon", "pampers", "servetele", "protex", "colgate", "ariel",
                               "balsam", "deodorant", "hartie igienica", "scutece", "tampoane",
                               "periuta", "lichid vase", "lotiune", "dezinfectant"]):
        return "Ingrijire & Curatenie"
    if any(x in rn for x in ["iaurt", "lapte ", "branza", "unt ", "smantana", "kefir",
                               "cascaval", "telemea", "oua ", "ou ", "mozzarella", "feta"]):
        return "Lactate & Oua"
    if any(x in rn for x in ["salam", "parizer", "cremwursti", "sunca", "mici ", "carnati",
                               "pate", "pui ", "porc ", "cotlet", "aripi", "vita ", "miel ",
                               "bacon", "muschi", "ceafa", "piept de", "pulpa de", "curcan",
                               "kaiser", "jambon", "mezel"]):
        return "Carne & Mezeluri"
    if any(x in rn for x in ["paine", "croissant", "chifla", "bagheta", "gogoasa", "ciocolata",
                               "biscuiti", "eugenia", "napolitane", "bomboane", "milka", "oreo",
                               "cozonac", "wafer", "halva", "prajitura", "tort", "briosa"]):
        return "Panificatie & Dulciuri"
    if any(x in rn for x in ["ceapa", "mango", "cartofi", "mere ", "banane", "rosii", "vinete",
                               "varza", "castraveti", "ardei", "usturoi", "lamaie", "portocale",
                               "capsuni", "cirese", "piersici", "pepene", "broccoli", "spanac",
                               "salata ", "legume", "fructe"]):
        return "Legume & Fructe"
    if any(x in rn for x in ["ulei", "faina", "zahar", "orez", "malai", "pasta tomate", "mustar",
                               "ketchup", "conserve", "fasole", "maioneza", "otet", "sare ",
                               "spaghete", "macaroane", "taitei", "bulion", "miere", "gem ",
                               "dulceata", "nutella", "condiment"]):
        return "Bacanie & Alimente de baza"
    if any(x in rn for x in ["jucarie", "sosete", "pungi", "folie", "hrana animal", "vaza",
                               "ghiveci", "perna", "prosop ", "halat", "baterie", "bec"]):
        return "Casa & Diverse"

    return cat if cat in CATEGORIES else "Casa & Diverse"


def fix_brand(brand: str, raw_name: str) -> str:
    if not brand:
        return "Generic"
    b = brand.strip()
    if b.lower() in FALSE_BRANDS:
        # incearca sa gaseasca primul cuvant cu majuscula care nu e tip de produs
        for word in raw_name.split():
            w = word.strip("(),.")
            if w[0:1].isupper() and w.lower() not in FALSE_BRANDS and len(w) > 2:
                return w
        return "Generic"
    # pastreaza multi-word brands cunoscute, altfel ia primul cuvant
    MULTI_WORD = {"mega image", "san fabio", "la dorna", "zu zu", "cris tim", "cris-tim",
                  "napolact", "betty blue", "gitana winery", "hanul boieresc"}
    if b.lower() in MULTI_WORD:
        return b
    if " " in b:
        return b.split()[0]
    return b


def clean_name(name: str, raw_name: str) -> str:
    if not name or len(name.strip()) < 3:
        # fallback: sterge gramajul din raw_name
        cleaned = GRAMAJ_RE.sub("", raw_name).strip(" ,.-")
        return cleaned if len(cleaned) > 2 else raw_name
    return name.strip()


def process_file(filename: str):
    store_slug = filename.replace("ocr_", "").replace(".json", "")
    input_path  = os.path.join(INPUT_DIR, filename)
    output_path = os.path.join(OUTPUT_DIR, f"refined_ocr_{store_slug}.json")

    with open(input_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if not raw_data:
        print(f"  {filename}: gol, skip.")
        return

    print(f"Procesare {filename} ({len(raw_data)} produse)...")
    refined = []

    for i in range(0, len(raw_data), BATCH_SIZE):
        batch = raw_data[i:i + BATCH_SIZE]
        ai_results = ai_refine_batch(batch)

        for j, original in enumerate(batch):
            raw_n = original.get("raw_name", "")
            res   = ai_results[j] if j < len(ai_results) else {}

            raw_cat   = res.get("categorie") or res.get("category") or "Casa & Diverse"
            final_cat = fix_category(raw_cat, raw_n)

            raw_brand   = res.get("brand") or ""
            final_brand = fix_brand(raw_brand, raw_n)

            raw_name_clean = res.get("nume_curat") or ""
            final_name     = clean_name(raw_name_clean, raw_n)

            refined.append({
                "store":         original.get("store"),
                "name":          final_name,
                "brand":         final_brand,
                "category":      final_cat,
                "price_new":     original.get("price_new"),
                "price_old":     original.get("price_old"),
                "discount":      original.get("discount"),
                "requires_card": original.get("requires_card", False),
                "raw_name":      raw_n,
                "source":        "ocr",
            })

        print(f"  {len(refined)}/{len(raw_data)}", end="\r")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(refined, f, indent=4, ensure_ascii=False)
    print(f"\n  Salvat: {output_path} ({len(refined)} produse)")


def run():
    files = [f for f in os.listdir(INPUT_DIR) if f.startswith("ocr_") and f.endswith(".json")]
    if not files:
        print("Niciun fisier ocr_*.json gasit in outputs/")
        return

    print(f"Gasit {len(files)} fisiere OCR: {files}\n")
    for fname in sorted(files):
        process_file(fname)
    print("\nGata!")


if __name__ == "__main__":
    run()
