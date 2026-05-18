"""
Echivalent cu final_web_cleanup.py din radacina proiectului,
redirectat catre realtime_experiment/outputs/.

Face:
  - Encoding fix (mojibake) pe raw_name din toate fisierele raw_web
  - Recalcul discount daca lipseste sau e 0
  - Salveaza fiecare fisier separat (nu le combina)

Utilizare:
    cd realtime_experiment
    python cleanup_realtime.py
"""

import sys
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
RAW_DIR  = BASE_DIR / "outputs" / "raw_web"

PARENT_DIR = BASE_DIR.parent
sys.path.insert(0, str(PARENT_DIR))

from final_web_cleanup import fix_romanian_encoding  # noqa: E402


def main():
    files = sorted(RAW_DIR.glob("data_*.json"))
    if not files:
        log.warning("Niciun fisier data_*.json gasit in %s", RAW_DIR)
        return

    log.info("Pornire curatare...")

    for fpath in files:
        store_key = fpath.stem.replace("data_", "").capitalize()
        data = json.loads(fpath.read_text(encoding="utf-8"))
        fixed = 0

        for item in data:
            # Encoding fix pe raw_name
            original = item.get("raw_name", "")
            cleaned  = fix_romanian_encoding(original)
            if cleaned != original:
                item["raw_name"] = cleaned
                fixed += 1

            # Recalcul discount daca lipseste sau e 0
            p_new = item.get("price_new")
            p_old = item.get("price_old")
            if p_new and p_old and p_old > p_new:
                item["discount"] = round(1 - p_new / p_old, 2)

        # Salveaza fisierul individual cu fix aplicat
        fpath.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
        log.info("  %s: %d produse | %d encoding fixes", store_key, len(data), fixed)

    log.info("\n Gata! Fisierele curatate sunt in: %s", RAW_DIR)


if __name__ == "__main__":
    main()
