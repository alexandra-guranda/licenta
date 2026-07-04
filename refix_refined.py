import json
import logging
from pathlib import Path
import ftfy
from web_refiner import fix_item, VALID_CATEGORIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REFINED_DIR  = Path("outputs/refined_llama")
COMBINED_OUT = REFINED_DIR / "REFINED_WEB_DATA.json"

STORE_FILES = [
    "refined_data_auchan.json",
    "refined_data_kaufland.json",
    "refined_data_penny.json",
    "refined_data_profi.json",
    "refined_data_carrefour.json",
    "refined_data_mega_image.json",
    "refined_data_lidl.json",
]

TEXT_FIELDS = ("name", "raw_name", "brand", "category")

def fix_encoding(item: dict) -> dict:
    out = dict(item)
    for field in TEXT_FIELDS:
        val = out.get(field)
        if isinstance(val, str) and val:
            out[field] = ftfy.fix_text(val)
    return out

def refix_file(path: Path) -> list[dict]:
    enc = "utf-8" if "lidl" in path.name else "cp1252"
    with open(path, encoding=enc, errors="replace") as f:
        data: list[dict] = json.load(f)

    encoding_fixes = 0
    fixed_data = []
    for item in data:
        cleaned = fix_encoding(item)
        if any(cleaned.get(f) != item.get(f) for f in TEXT_FIELDS):
            encoding_fixes += 1
        fixed_data.append(fix_item(cleaned))

    cat_fixes = sum(1 for a, b in zip(data, fixed_data) if a.get("category") != b.get("category"))
    log.info("%s: %d produse | encoding fixes: %d | categorii corectate: %d",
             path.name, len(data), encoding_fixes, cat_fixes)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(fixed_data, f, indent=4, ensure_ascii=False)

    return fixed_data

def main():
    all_products = []
    for fname in STORE_FILES:
        path = REFINED_DIR / fname
        if not path.exists():
            log.warning("Fisier lipsa: %s", path)
            continue
        products = refix_file(path)
        all_products.extend(products)

    cats = set(VALID_CATEGORIES) - {"Necategorizat"}
    necateg = [p for p in all_products if p.get("category") not in cats]
    log.info("Total: %d produse | Necategorizat/invalid ramas: %d", len(all_products), len(necateg))
    if necateg:
        for p in necateg[:10]:
            log.info("  [%s] cat=%r | raw=%r", p.get("store"), p.get("category"), p.get("raw_name", "")[:60])

    with open(COMBINED_OUT, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=4, ensure_ascii=False)
    log.info("Salvat → %s (%d produse)", COMBINED_OUT, len(all_products))

if __name__ == "__main__":
    main()
