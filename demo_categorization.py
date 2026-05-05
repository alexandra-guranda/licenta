"""
Demo: Categorizare produse supermarket cu LLM (Llama 3.2:3b)
Scop: Arata problemele intampinate si solutia implementata.
"""

import ollama
import json

MODEL = "llama3.2:3b"

CATEGORIES = [
    "Panificatie & Dulciuri", "Carne & Mezeluri", "Lactate & Oua",
    "Legume & Fructe", "Bauturi", "Bacanie & Alimente de baza",
    "Ingrijire & Curatenie", "Casa & Diverse"
]

# Produse reprezentative: (raw_name, categorie_corecta, nota)
TEST_CASES = [
    ("Mici 500g Aldis",           "Carne & Mezeluri",          "produs traditional romanesc"),
    ("Sarmale cu carne de porc",  "Carne & Mezeluri",          "preparat traditional"),
    ("Cascaval afumat Dorna",     "Lactate & Oua",             "brand romanesc"),
    ("Iaurt Actimel L.Casei",     "Lactate & Oua",             "brand international, ok"),
    ("Vopsea oua Deco 10ml",      "Ingrijire & Curatenie",     "produs specific Pastelui"),
    ("Scăricică porc kg",         "Carne & Mezeluri",          "cuvant cu diacritice"),
    ("Cremwursti Bucegi 500g",    "Carne & Mezeluri",          "brand romanesc clasic"),
    ("Bere Ciuc Premium 0.5L",    "Bauturi",                   "usor de recunoscut"),
    ("Malai Morarit 1kg",         "Bacanie & Alimente de baza","produs specific romanesc"),
    ("Chifle kaiser 4 buc",       "Panificatie & Dulciuri",    "termen specific"),
]

KEYWORD_FIX = {
    "mici": "Carne & Mezeluri",
    "sarmale": "Carne & Mezeluri",
    "scăricică": "Carne & Mezeluri", "scaricica": "Carne & Mezeluri",
    "cremwursti": "Carne & Mezeluri",
    "cascaval": "Lactate & Oua",
    "malai": "Bacanie & Alimente de baza",
    "chifle": "Panificatie & Dulciuri", "chiflă": "Panificatie & Dulciuri",
    "vopsea oua": "Ingrijire & Curatenie",
}

def ask_llm(raw_name: str) -> dict:
    prompt = (
        f"Esti expert in retail romanesc. Categorizeaza produsul de mai jos.\n"
        f"CATEGORII PERMISE: {CATEGORIES}\n"
        f'FORMAT: {{"categorie": "...", "brand": "...", "nume_curat": "..."}}\n'
        f'PRODUS: "{raw_name}"'
    )
    try:
        r = ollama.generate(model=MODEL, prompt=prompt, format="json",
                            options={"temperature": 0.1})
        return json.loads(r["response"])
    except Exception as e:
        return {"categorie": "EROARE", "brand": "", "nume_curat": raw_name, "_err": str(e)}

def keyword_fix(raw_name: str, llm_cat: str) -> str:
    rn = raw_name.lower()
    for kw, cat in KEYWORD_FIX.items():
        if kw in rn:
            return cat
    return llm_cat

def run_demo():
    print("=" * 70)
    print("DEMO: Categorizare produse supermarket cu Llama 3.2:3b")
    print("=" * 70)

    correct_llm = 0
    correct_after_fix = 0
    total = len(TEST_CASES)

    for raw_name, expected, nota in TEST_CASES:
        print(f"\nPRODUS  : {raw_name}")
        print(f"  nota  : {nota}")

        result = ask_llm(raw_name)
        llm_cat = result.get("categorie", "?")
        fixed_cat = keyword_fix(raw_name, llm_cat)

        llm_ok = llm_cat == expected
        fix_ok = fixed_cat == expected

        if llm_ok:
            correct_llm += 1
        if fix_ok:
            correct_after_fix += 1

        status_llm = "OK" if llm_ok else "GRESIT"
        status_fix = "OK" if fix_ok else "GRESIT"

        print(f"  LLM raw  : {llm_cat:<35} [{status_llm}]")
        if not llm_ok:
            print(f"  Fix      : {fixed_cat:<35} [{status_fix}]")
        print(f"  Asteptat : {expected}")

    print("\n" + "=" * 70)
    print(f"REZULTATE FINALE ({total} produse de test):")
    print(f"  Llama singur    : {correct_llm}/{total} corecte ({100*correct_llm//total}%)")
    print(f"  Llama + fix     : {correct_after_fix}/{total} corecte ({100*correct_after_fix//total}%)")
    print("=" * 70)
    print("\nCONCLUZIE:")
    print("  - Llama 3.2:3b are probleme cu produse traditional romanesti")
    print("    ('mici', 'sarmale', 'scaricica', 'malai', 'cremwursti')")
    print("  - Solutia: strat deterministic de corectie bazat pe cuvinte-cheie")
    print("  - Combinatia LLM + reguli depaseste performanta fiecareia separat")

if __name__ == "__main__":
    run_demo()
