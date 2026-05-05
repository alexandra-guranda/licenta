"""
Redenumeste imaginile descarcate cu numele gresit si actualizeaza image_local in JSON.

Logica:
  - Numele corect al fisierului = slugify(raw_name) + ".jpg"
  - Daca fisierul curent exista la calea din image_local → il redenumim
  - Daca nu exista → descarcam din nou de la image_url cu numele corect
  - Actualizam image_local in fiecare JSON
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
IMAGE_BASE  = Path("outputs/data/images")

STORE_FILES = [
    "refined_data_auchan.json",
    "refined_data_kaufland.json",
    "refined_data_penny.json",
    "refined_data_profi.json",
    "refined_data_carrefour.json",
    "refined_data_mega_image.json",
    "refined_data_lidl.json",
]

HEADERS = {"User-Agent": "Mozilla/5.0"}


def slugify(text: str) -> str:
    if not text:
        return "produs_fara_nume"
    text = re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')
    return text[:80]


def store_slug(store_name: str) -> str:
    return store_name.lower().replace(" ", "_")


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content)
            return True
    except Exception as e:
        log.debug("Download failed %s: %s", url, e)
    return False


def fix_store(fname: str) -> dict:
    path = REFINED_DIR / fname
    if not path.exists():
        log.warning("Lipsa: %s", path)
        return {}

    with open(path, encoding="utf-8") as f:
        data: list[dict] = json.load(f)

    renamed = 0
    redownloaded = 0
    failed = 0

    for prod in data:
        raw_name  = prod.get("raw_name") or prod.get("name") or ""
        store     = prod.get("store", "")
        image_url = prod.get("image_url", "")

        correct_fname = slugify(raw_name) + ".jpg"
        correct_rel   = f"data/images/{store_slug(store)}/{correct_fname}"
        correct_abs   = Path("outputs") / correct_rel

        current_rel = prod.get("image_local", "")
        current_abs = Path("outputs") / current_rel if current_rel else None

        # Already correct
        if current_rel == correct_rel and correct_abs.exists():
            continue

        # Try to rename existing file to correct name
        if current_abs and current_abs.exists() and current_abs != correct_abs:
            correct_abs.parent.mkdir(parents=True, exist_ok=True)
            try:
                current_abs.rename(correct_abs)
                prod["image_local"] = correct_rel
                renamed += 1
                continue
            except Exception as e:
                log.debug("Rename failed %s → %s: %s", current_abs.name, correct_abs.name, e)

        # File already at correct location
        if correct_abs.exists():
            prod["image_local"] = correct_rel
            continue

        # File missing — download from image_url
        if image_url:
            if download_image(image_url, correct_abs):
                prod["image_local"] = correct_rel
                redownloaded += 1
            else:
                log.warning("Nu s-a putut descarca: %s | %s", raw_name[:50], image_url[:60])
                failed += 1
        else:
            log.warning("Fara URL: %s", raw_name[:50])
            failed += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return {"total": len(data), "renamed": renamed, "redownloaded": redownloaded, "failed": failed}


def main():
    total_r = total_dl = total_fail = 0

    for fname in STORE_FILES:
        store = fname.replace("refined_data_", "").replace(".json", "")
        stats = fix_store(fname)
        if not stats:
            continue
        log.info("%-14s | total: %4d | redenumite: %3d | re-descarcate: %3d | erori: %d",
                 store, stats["total"], stats["renamed"], stats["redownloaded"], stats["failed"])
        total_r   += stats["renamed"]
        total_dl  += stats["redownloaded"]
        total_fail += stats["failed"]

    log.info("─" * 60)
    log.info("TOTAL: redenumite=%d | re-descarcate=%d | erori=%d", total_r, total_dl, total_fail)

    # Regeneram REFINED_WEB_DATA.json
    all_products = []
    for fname in STORE_FILES:
        p = REFINED_DIR / fname
        if p.exists():
            with open(p, encoding="utf-8") as f:
                all_products.extend(json.load(f))

    combined = REFINED_DIR / "REFINED_WEB_DATA.json"
    with open(combined, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=4, ensure_ascii=False)
    log.info("Salvat → %s (%d produse)", combined, len(all_products))


if __name__ == "__main__":
    main()
