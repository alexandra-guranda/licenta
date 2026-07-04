import json
import logging
import re
import sys
from pathlib import Path

import ftfy
from web_refiner import (
    AI_BATCH_SIZE,
    FALLBACK_CATEGORY,
    ai_refine_batch,
    fix_item,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

INPUT_DIR  = Path("outputs")
OUTPUT_DIR = Path("outputs/refined_llama_ocr")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_FRAGMENT_PREFIXES = re.compile(
    r"^(cu |și |si |fara |fără |în |in |pe |"
    r"pentru |sau |ori |dar |ci |care |"
    r"per pachet|lei/|lei )",
    re.IGNORECASE,
)

_NON_PRODUCT_PHRASES = {
    "diverse", "diverse sortimente", "stoc", "limita stocului",
    "la masa in romania", "la masă în românia", "act for good",
    "prin act for good", "valabilitate", "oferta", "oferte",
    "promotii", "promotie", "disponibil",
}

_BROKEN_MARKERS = (
    "Ä‚",
    "Ã‚",
    "Ã¢",
    "Ã®",
    "È™",
    "È",
    "Å£",
    "â€",
)

def fix_encoding(text: str) -> str:
    try:
        fixed = ftfy.fix_text(text)
        return fixed
    except Exception:
        return text

def is_ocr_noise(raw_name: str) -> bool:
    s = raw_name.strip()

    if len(s) < 3:
        return True

    if re.match(r"^[\d\s\.,;:\-\+\/\\%]+$", s):
        return True

    if re.match(r"^\d+\s*(ml|l|g|kg|buc|x\s*\d)", s, re.IGNORECASE):
        return True

    if any(marker in s for marker in _BROKEN_MARKERS):
        return True

    s_low = s.lower()

    if s_low in _NON_PRODUCT_PHRASES:
        return True

    if _FRAGMENT_PREFIXES.match(s_low):
        return True

    _PRODUSE_SCURTE_RO = {
        "pui", "vin", "unt", "oua", "apa", "suc", "gem", "ton", "cas", "sos",
        "rom", "gin", "bor", "sec", "ros", "alb", "mie", "otet", "zer", "ou",
        "mac", "nuc", "smoc", "cod", "lac", "mel", "ceai", "rac", "mur",
    }
    if re.match(r"^[A-Z0-9]{1,4}\.?$", s) and s.lower() not in _PRODUSE_SCURTE_RO:
        return True

    return False

def calc_discount(price_new, price_old, stored_discount) -> float:
    try:
        pn = float(price_new or 0)
        po = float(price_old or 0)
        sd = float(stored_discount or 0)
    except (TypeError, ValueError):
        return 0.0

    if sd != 0.0:
        return sd

    if po > pn > 0:
        return round((po - pn) / po, 4)

    return 0.0

def process_file(path: Path) -> None:
    with open(path, encoding="utf-8") as f:
        raw_data: list[dict] = json.load(f)

    repaired: list[dict] = []
    for p in raw_data:
        fixed_name = fix_encoding(p.get("raw_name", ""))
        p["raw_name"] = fixed_name
        repaired.append(p)

    clean_data = [p for p in repaired if not is_ocr_noise(p.get("raw_name", ""))]
    skipped = len(raw_data) - len(clean_data)

    log.info("Procesare %s (%d produse, %d sarite ca zgomot/fragment/encoding rupt)...",
             path.name, len(clean_data), skipped)

    interim: list[dict] = []
    for i in range(0, len(clean_data), AI_BATCH_SIZE):
        batch = clean_data[i : i + AI_BATCH_SIZE]
        ai_results = ai_refine_batch(batch)
        for j, raw_item in enumerate(batch):
            ai = ai_results[j] if j < len(ai_results) else {}
            pn  = raw_item.get("price_new")
            po  = raw_item.get("price_old")
            sd  = raw_item.get("discount")
            interim.append({
                "store":         raw_item.get("store", ""),
                "raw_name":      raw_item.get("raw_name", ""),
                "name":          ai.get("nume_curat") or raw_item.get("raw_name", ""),
                "brand":         ai.get("brand") or "Generic",
                "category":      ai.get("categorie") or FALLBACK_CATEGORY,
                "price_new":     pn,
                "price_old":     po,
                "discount":      calc_discount(pn, po, sd),
                "requires_card": raw_item.get("requires_card", False),
                "captured_at":   raw_item.get("captured_at"),
                "source":        "ocr",
            })
        print(f"  AI: {min(i + AI_BATCH_SIZE, len(clean_data))}/{len(clean_data)}", end="\r")

    print()
    fixed_data = [fix_item(item) for item in interim]

    cat_fixes   = sum(1 for a, b in zip(interim, fixed_data) if a.get("category") != b.get("category"))
    brand_fixes = sum(1 for a, b in zip(interim, fixed_data) if a.get("brand")    != b.get("brand"))
    name_fixes  = sum(1 for a, b in zip(interim, fixed_data) if a.get("name")     != b.get("name"))
    disc_filled = sum(1 for a, b in zip(interim, fixed_data)
                      if b.get("discount", 0) != 0 and a.get("discount", 0) == 0)

    store_slug = path.stem.replace("ocr_llama_", "").replace("ocr_", "")
    out_path   = OUTPUT_DIR / f"refined_ocr_{store_slug}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fixed_data, f, indent=4, ensure_ascii=False)

    log.info("%s → sarite:%d | cat:%d brand:%d name:%d disc_calculat:%d | %d produse → %s",
             path.name, skipped, cat_fixes, brand_fixes, name_fixes,
             disc_filled, len(fixed_data), out_path)

def main() -> None:
    store_filter = sys.argv[1].lower() if len(sys.argv) > 1 else None

    files = sorted(INPUT_DIR.glob("ocr_llama_*.json"))
    if store_filter:
        files = [f for f in files if store_filter in f.stem]

    if not files:
        log.warning("Niciun fisier ocr_*.json gasit in %s (filtru: %s)", INPUT_DIR, store_filter)
        return

    log.info("Fisiere de procesat: %s", [f.name for f in files])
    for path in files:
        process_file(path)

    log.info("Gata! Rezultate in %s", OUTPUT_DIR)

    all_products = []
    for f in sorted(OUTPUT_DIR.glob("refined_ocr_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        all_products.extend(data)
    final_path = OUTPUT_DIR / "REFINED_OCR_DATA.json"
    final_path.write_text(json.dumps(all_products, indent=4, ensure_ascii=False), encoding="utf-8")
    log.info("REFINED_OCR_DATA.json: %d produse totale", len(all_products))

if __name__ == "__main__":
    main()
