"""
Reconstruieste REFINED_WEB_DATA.json din fisierele individuale per magazin.
Ruleaza dupa orice modificare a fisierelor refined_data_*.json.

Utilizare:
    python build_db.py
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REFINED_DIR = Path("outputs/refined")
OUTPUT     = REFINED_DIR / "REFINED_WEB_DATA.json"

STORE_FILES = [
    "refined_data_auchan.json",
    "refined_data_kaufland.json",
    "refined_data_penny.json",
    "refined_data_profi.json",
    "refined_data_carrefour.json",
    "refined_data_mega_image.json",
    "refined_data_lidl.json",
]

all_products = []
for fname in STORE_FILES:
    path = REFINED_DIR / fname
    if not path.exists():
        print(f"  [SKIP] {fname} — fisier lipsa")
        continue
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"  {fname}: {len(data)} produse")
    all_products.extend(data)

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(all_products, f, indent=2, ensure_ascii=False)

print(f"\nSalvat → {OUTPUT} ({len(all_products)} produse totale)")
print("Restart server pentru a incarca noile date: python main.py")
