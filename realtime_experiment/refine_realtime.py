"""
Aplica intregul pipeline de curatare pe datele din realtime_experiment/outputs/raw_web/:
  Pasul 1 — Curatare encoding (mojibake fix)
  Pasul 2 — Normalizare AI (Llama 3.2) + reguli deterministe (reparator.py)
  Pasul 3 — ftfy pass + re-aplicare reguli + combinare in REFINED_WEB_DATA.json

Salveaza rezultatul in realtime_experiment/outputs/refined/
fara sa atinga nimic din radacina proiectului.

Utilizare:
    cd realtime_experiment
    python refine_realtime.py
"""

import sys
import json
import logging
import ftfy
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# --- Paths locale ---
BASE_DIR    = Path(__file__).parent
RAW_DIR     = BASE_DIR / "outputs" / "raw_web"
REFINED_DIR = BASE_DIR / "outputs" / "refined"
REFINED_DIR.mkdir(parents=True, exist_ok=True)

# Adaugam directorul parinte in sys.path ca sa importam scripturile existente
PARENT_DIR = BASE_DIR.parent
sys.path.insert(0, str(PARENT_DIR))

from final_web_cleanup import fix_romanian_encoding  # noqa: E402
import reparator                                      # noqa: E402

TEXT_FIELDS = ("name", "raw_name", "brand", "category")


# ─── PASUL 1: Curatare encoding (mojibake fix) ────────────────────────────────

def apply_encoding_fix(raw_dir: Path) -> list[Path]:
    files = sorted(raw_dir.glob("data_*.json"))
    if not files:
        log.warning("Niciun fisier data_*.json gasit in %s", raw_dir)
        return []

    for fpath in files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        fixed = 0
        for item in data:
            original = item.get("raw_name", "")
            cleaned  = fix_romanian_encoding(original)
            if cleaned != original:
                item["raw_name"] = cleaned
                fixed += 1
        fpath.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
        log.info("  Encoding fix: %s — %d denumiri corectate", fpath.name, fixed)

    return files


# ─── PASUL 2: Normalizare AI + reguli deterministe ────────────────────────────

def apply_normalization(files: list[Path]) -> None:
    reparator.OUTPUT_DIR = REFINED_DIR
    for fpath in files:
        log.info("Normalizare: %s", fpath.name)
        reparator.process_file(fpath)


# ─── PASUL 3: ftfy pass + re-aplicare reguli + combinare ─────────────────────

def apply_refix_and_combine() -> None:
    refined_files = sorted(REFINED_DIR.glob("refined_data_*.json"))
    if not refined_files:
        log.warning("Niciun fisier refined gasit in %s", REFINED_DIR)
        return

    all_products = []

    for fpath in refined_files:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        fixed_data = []
        encoding_fixes = 0

        for item in data:
            # ftfy pe toate campurile text
            cleaned = dict(item)
            for field in TEXT_FIELDS:
                val = cleaned.get(field)
                if isinstance(val, str) and val:
                    fixed_val = ftfy.fix_text(val)
                    if fixed_val != val:
                        cleaned[field] = fixed_val
                        encoding_fixes += 1

            # Re-aplica regulile deterministe
            fixed_data.append(reparator.fix_item(cleaned))

        cat_fixes = sum(1 for a, b in zip(data, fixed_data)
                        if a.get("category") != b.get("category"))
        log.info("  refix: %s | ftfy: %d | categorii: %d",
                 fpath.name, encoding_fixes, cat_fixes)

        fpath.write_text(json.dumps(fixed_data, indent=4, ensure_ascii=False), encoding="utf-8")
        all_products.extend(fixed_data)

    # Combina totul intr-un singur fisier
    combined_path = REFINED_DIR / "REFINED_WEB_DATA.json"
    combined_path.write_text(json.dumps(all_products, indent=4, ensure_ascii=False), encoding="utf-8")
    log.info("Combinat: %d produse → %s", len(all_products), combined_path)

    # Raport categorii necategorizate
    from reparator import VALID_CATEGORIES
    necateg = [p for p in all_products if p.get("category") not in VALID_CATEGORIES]
    if necateg:
        log.warning("%d produse necategorizate:", len(necateg))
        for p in necateg[:10]:
            log.warning("  [%s] cat=%r | raw=%r", p.get("store"), p.get("category"), p.get("raw_name", "")[:60])


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    log.info("=== PASUL 1: Curatare encoding ===")
    files = apply_encoding_fix(RAW_DIR)
    if not files:
        return

    log.info("\n=== PASUL 2: Normalizare AI + reguli deterministe ===")
    apply_normalization(files)

    log.info("\n=== PASUL 3: ftfy + re-aplicare reguli + combinare ===")
    apply_refix_and_combine()

    log.info("\n✅ Gata! Datele finale sunt in: %s/REFINED_WEB_DATA.json", REFINED_DIR)
    log.info("   Compara cu outputs/refined_llama/REFINED_WEB_DATA.json din radacina.")


if __name__ == "__main__":
    main()
