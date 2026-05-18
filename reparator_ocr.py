"""
Rafinare date OCR cu aceeasi pipeline AI ca reparator.py (web data).
Permite compararea rezultatelor OCR vs Web pentru aceleasi magazine.

Citeste:  outputs/ocr_*.json          (produse extrase din cataloage PDF/imagini)
Scrie:    outputs/refined/refined_ocr_*.json

Utilizare:
    python reparator_ocr.py              # toate fisierele ocr_*.json
    python reparator_ocr.py auchan       # doar ocr_auchan.json
"""
import json
import logging
import re
import sys
from pathlib import Path

import ftfy
from reparator import (
    AI_BATCH_SIZE,
    FALLBACK_CATEGORY,
    ai_refine_batch,
    fix_item,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

INPUT_DIR  = Path("outputs")
OUTPUT_DIR = Path("outputs/refined")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Fragmente care indica ca numele e continuare dintr-o linie anterioara
_FRAGMENT_PREFIXES = re.compile(
    r"^(cu |și |si |fara |fără |în |in |pe |"
    r"pentru |sau |ori |dar |ci |care |"
    r"per pachet|lei/|lei )",
    re.IGNORECASE,
)

# Cuvinte/fraze care nu sunt produse (reclame, texte catalog)
_NON_PRODUCT_PHRASES = {
    "diverse", "diverse sortimente", "stoc", "limita stocului",
    "la masa in romania", "la masă în românia", "act for good",
    "prin act for good", "valabilitate", "oferta", "oferte",
    "promotii", "promotie", "disponibil",
}

# Secvente tipice de encoding rupt (UTF-8 citit ca Latin-1/Windows-1252)
# Ä‚ = Ă, Ã‚ = Â, È™ = ș, Å£ = ț etc.
_BROKEN_MARKERS = (
    "Ä‚",    # Ä‚ → Ă
    "Ã‚",    # Ã‚ → Â
    "Ã¢",    # Ã¢ → â
    "Ã®",    # Ã® → î
    "È™",    # È™ → ș
    "È",    # Èš → Ș
    "Å£",    # Å£ → ț
    "â€",  # â€ sequence
)


def fix_encoding(text: str) -> str:
    """Incearca sa repare encoding-ul rupt cu ftfy."""
    try:
        fixed = ftfy.fix_text(text)
        return fixed
    except Exception:
        return text


def is_ocr_noise(raw_name: str) -> bool:
    """
    Returneaza True daca raw_name este zgomot OCR sau nu reprezinta un produs real.
    Criterii:
      - prea scurt (< 3 caractere dupa trim)
      - doar cifre / simboluri
      - encoding rupt care nu a putut fi reparat
      - fragment de fraza (incepe cu conector)
      - fraza non-produs cunoscuta (reclame, etichete catalog)
      - descriptor de ambalaj pur (ex: "380 ml", "6 x 2L")
      - abreviere pura de 1-3 litere mari (ex: "IGP", "B24", "ECO")
    """
    s = raw_name.strip()

    if len(s) < 3:
        return True

    if re.match(r"^[\d\s\.,;:\-\+\/\\%]+$", s):
        return True

    # Descriptor de ambalaj pur: incepe cu numar + unitate
    if re.match(r"^\d+\s*(ml|l|g|kg|buc|x\s*\d)", s, re.IGNORECASE):
        return True

    # Encoding rupt nereparabil (ftfy nu a putut repara)
    if any(marker in s for marker in _BROKEN_MARKERS):
        return True

    s_low = s.lower()

    if s_low in _NON_PRODUCT_PHRASES:
        return True

    if _FRAGMENT_PREFIXES.match(s_low):
        return True

    # Abreviere pura: 1-4 litere mari (IGP, B24, ECO) — dar nu cuvinte romanesti reale
    _PRODUSE_SCURTE_RO = {
        "pui", "vin", "unt", "oua", "apa", "suc", "gem", "ton", "cas", "sos",
        "rom", "gin", "bor", "sec", "ros", "alb", "mie", "otet", "zer", "ou",
        "mac", "nuc", "smoc", "cod", "lac", "mel", "ceai", "rac", "mur",
    }
    if re.match(r"^[A-Z0-9]{1,4}\.?$", s) and s.lower() not in _PRODUSE_SCURTE_RO:
        return True

    return False


def calc_discount(price_new, price_old, stored_discount) -> float:
    """
    Calculeaza discountul ca fractie (0.0 - 1.0).
    Daca OCR-ul a extras deja o valoare != 0, o pastreaza.
    Altfel o calculeaza din preturi.
    """
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

    # Pas 1: repara encoding, apoi filtreaza zgomotul
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

    store_slug = path.stem.replace("ocr_", "")
    out_path   = OUTPUT_DIR / f"refined_ocr_{store_slug}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fixed_data, f, indent=4, ensure_ascii=False)

    log.info("%s → sarite:%d | cat:%d brand:%d name:%d disc_calculat:%d | %d produse → %s",
             path.name, skipped, cat_fixes, brand_fixes, name_fixes,
             disc_filled, len(fixed_data), out_path)


def main() -> None:
    store_filter = sys.argv[1].lower() if len(sys.argv) > 1 else None

    files = sorted(INPUT_DIR.glob("ocr_*.json"))
    if store_filter:
        files = [f for f in files if store_filter in f.stem]

    if not files:
        log.warning("Niciun fisier ocr_*.json gasit in %s (filtru: %s)", INPUT_DIR, store_filter)
        return

    log.info("Fisiere de procesat: %s", [f.name for f in files])
    for path in files:
        process_file(path)

    log.info("Gata! Rezultate in %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
