"""
Actualizeaza image_local in fisierele refined_data_*.json
sa pointeze spre images_fixed.

Strategii de matching (in ordine):
  1. Filename din image_local existent (daca nu e logo)
  2. Slug din raw_name  (formula colectorului: re.sub(r'[^a-z0-9]+','_', name.lower()).strip('_'))
  3. Slug din name

Daca nicio strategie nu gaseste un fisier → image_local = None (se foloseste image_url)

Ruleaza:
    python update_image_paths.py
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REFINED_DIR = Path("outputs/refined")
IMAGES_DIR  = Path("outputs/data/images_fixed")

STORE_FILES = {
    "auchan":     "refined_data_auchan.json",
    "kaufland":   "refined_data_kaufland.json",
    "penny":      "refined_data_penny.json",
    "profi":      "refined_data_profi.json",
    "carrefour":  "refined_data_carrefour.json",
    "mega_image": "refined_data_mega_image.json",
    "lidl":       "refined_data_lidl.json",
}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")


def build_index(store_folder: str) -> dict[str, str]:
    """stem → filename (e.g. 'ceafa_de_porc' → 'ceafa_de_porc.jpg')"""
    folder = IMAGES_DIR / store_folder
    if not folder.exists():
        return {}
    return {p.stem: p.name for p in folder.iterdir() if p.is_file()}


def extract_filename(image_local: str | None) -> str | None:
    if not image_local or "logos" in image_local:
        return None
    try:
        fname = image_local.encode("latin-1").decode("utf-8").rsplit("/", 1)[-1]
    except Exception:
        fname = image_local.rsplit("/", 1)[-1]
    return fname if fname.endswith(".jpg") else None


def find_image(p: dict, index: dict[str, str]) -> str | None:
    """Returns filename if found, else None."""
    # Strategy 1: existing image_local filename
    fname = extract_filename(p.get("image_local"))
    if fname:
        stem = Path(fname).stem
        if stem in index:
            return index[stem]

    # Strategy 2: slug from raw_name
    for field in ("raw_name", "name"):
        slug = slugify(p.get(field, ""))
        if slug and slug in index:
            return index[slug]

        # Strategy 3: prefix match (scrapers truncate long names)
        if slug and len(slug) > 20:
            for stem, filename in index.items():
                if stem.startswith(slug[:40]) or slug.startswith(stem[:40]):
                    return filename

    return None


def main():
    total_updated = total_missing = 0

    for store_key, json_fname in STORE_FILES.items():
        path = REFINED_DIR / json_fname
        if not path.exists():
            print(f"[SKIP] {json_fname} — lipsa")
            continue

        index = build_index(store_key)
        with open(path, encoding="utf-8") as f:
            products = json.load(f)

        updated = missing = 0
        for p in products:
            match = find_image(p, index)
            if match:
                p["image_local"] = f"data/images_fixed/{store_key}/{match}"
                updated += 1
            else:
                p["image_local"] = None
                missing += 1

        with open(path, "w", encoding="utf-8") as f:
            json.dump(products, f, indent=2, ensure_ascii=False)

        print(f"{json_fname}: {updated}/{len(products)} cu imagine  ({missing} fara)")
        total_updated += updated
        total_missing += missing

    print(f"\nTotal: {total_updated} produse cu image_local → images_fixed")
    print(f"       {total_missing} produse fara imagine (vor folosi image_url)")
    print("\nRuleaza acum: python build_db.py")


if __name__ == "__main__":
    main()