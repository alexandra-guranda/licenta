"""
Asigura ca fiecare imagine de pe disk are numele corect din image_local (refined JSON).
Foloseste JSON-ul doar ca referinta (NU il modifica).

Logic:
  - Daca fisierul exista deja la calea corecta → skip
  - Daca nu exista → descarca din nou de la image_url cu numele corect
"""
import json
import os
import re
import logging
import requests
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REFINED_DIR = Path("outputs/refined")
OUTPUTS_DIR = Path("outputs")

STORE_FILES = {
    "auchan":      "refined_data_auchan.json",
    "kaufland":    "refined_data_kaufland.json",
    "penny":       "refined_data_penny.json",
    "profi":       "refined_data_profi.json",
    "carrefour":   "refined_data_carrefour.json",
    "mega_image":  "refined_data_mega_image.json",
    "lidl":        "refined_data_lidl.json",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return True
    except Exception as e:
        log.debug("Download esuat %s: %s", url[:60], e)
    return False


def fix_store(store: str, force: bool = False) -> None:
    fname = STORE_FILES.get(store)
    if not fname:
        log.error("Magazin necunoscut: %s", store)
        return

    path = REFINED_DIR / fname
    if not path.exists():
        log.error("Fisier lipsa: %s", path)
        return

    with open(path, encoding="utf-8") as f:
        data: list[dict] = json.load(f)

    ok = redownloaded = failed = 0

    for prod in data:
        image_local = prod.get("image_local", "")
        image_url   = prod.get("image_url", "")

        if not image_local:
            continue

        correct_path = OUTPUTS_DIR / image_local

        if correct_path.exists() and not force:
            ok += 1
            continue

        if not image_url:
            log.warning("Fara URL: %s", prod.get("raw_name", "?")[:50])
            failed += 1
            continue

        if download_image(image_url, correct_path):
            redownloaded += 1
        else:
            log.warning("  ESEC: %s | %s", prod.get("raw_name", "?")[:40], image_url[:60])
            failed += 1

    log.info("%s: ok=%d | re-descarcate=%d | erori=%d", store, ok, redownloaded, failed)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", default=None,
                        help="Proceseaza un singur magazin (ex: lidl, auchan). "
                             "Fara argument = toate magazinele.")
    parser.add_argument("--force", action="store_true",
                        help="Re-descarca toate imaginile chiar daca fisierul exista deja.")
    args = parser.parse_args()

    stores = [args.store] if args.store else list(STORE_FILES.keys())

    for store in stores:
        fix_store(store, force=args.force)

    log.info("Gata!")


if __name__ == "__main__":
    main()
