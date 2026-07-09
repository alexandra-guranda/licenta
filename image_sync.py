import json
import logging
import re
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REFINED_DIR = Path("outputs/refined_llama")
IMAGE_BASE  = Path("outputs/fixed_images_llama")
COMBINED    = REFINED_DIR / "REFINED_WEB_DATA.json"

STORE_FILES = [
    "refined_data_auchan.json",
    "refined_data_kaufland.json",
    "refined_data_penny.json",
    "refined_data_profi.json",
    "refined_data_carrefour.json",
    "refined_data_mega_image.json",
    "refined_data_lidl.json",
]

HEADERS    = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
MIN_BYTES  = 5_000
MAX_WORKERS = 12

STORE_LOGOS = {
    "auchan":      "assets/logos/auchan.png",
    "lidl":        "assets/logos/lidl.png",
    "kaufland":    "assets/logos/kaufland.png",
    "carrefour":   "assets/logos/carrefour.png",
    "mega_image":  "assets/logos/mega_image.png",
    "penny":       "assets/logos/penny.png",
    "profi":       "assets/logos/profi.png",
}

def slugify(text: str) -> str:
    if not text:
        return "produs_fara_nume"
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:80]


def is_valid_image(data: bytes) -> bool:
    if len(data) < MIN_BYTES:
        return False
    if data[:3] == b"\xff\xd8\xff":
        return True
    if data[:4] == b"\x89PNG":
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False

def download_and_validate(url: str, dest: Path) -> tuple[bool, str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        if not is_valid_image(r.content):
            return False, f"imagine invalida ({len(r.content)} bytes)"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        return True, ""
    except Exception as e:
        return False, str(e)


def build_correct_path(prod: dict) -> tuple[Path, str]:
    store    = (prod.get("store") or "unknown").lower().replace(" ", "_")
    raw_name = prod.get("raw_name") or prod.get("name") or ""
    fname    = slugify(raw_name) + ".jpg"
    rel      = f"fixed_images_llama/{store}/{fname}"
    return IMAGE_BASE / store / fname, rel

def needs_download(dest: Path, force: bool) -> bool:
    if force:
        return True
    if not dest.exists():
        return True
    if dest.stat().st_size < MIN_BYTES:
        return True
    try:
        data = dest.read_bytes()
        if not is_valid_image(data):
            return True
    except Exception:
        return True
    return False


def process_product(prod: dict, force: bool) -> str:
    dest, rel = build_correct_path(prod)

    if not needs_download(dest, force):
        prod["image_local"] = rel
        return "skip"

    url = prod.get("image_url", "")
    if not url:
        _apply_logo_fallback(prod)
        return "no_url"

    ok, reason = download_and_validate(url, dest)
    if ok:
        prod["image_local"] = rel
        return "download"
    else:
        log.debug("FAIL [%s]: %s | %s", prod.get("raw_name", "?")[:40], reason, url[:60])
        _apply_logo_fallback(prod)
        return "fail"


def _apply_logo_fallback(prod: dict) -> None:
    store = (prod.get("store") or "").lower().replace(" ", "_")
    logo = STORE_LOGOS.get(store)
    if logo:
        prod["image_local"] = logo


def sync_store(fname: str, force: bool) -> dict:
    path = REFINED_DIR / fname
    if not path.exists():
        log.warning("Lipsa: %s", path)
        return {}

    with open(path, encoding="utf-8") as f:
        data: list[dict] = json.load(f)

    counts = {"skip": 0, "download": 0, "fail": 0, "no_url": 0}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(process_product, prod, force): prod for prod in data}
        done = 0
        for fut in as_completed(futures):
            status = fut.result()
            counts[status] = counts.get(status, 0) + 1
            done += 1
            print(f"  {fname}: {done}/{len(data)}", end="\r")

    print()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return counts


def clean_orphans() -> int:
    referenced: set[Path] = set()
    for fname in STORE_FILES:
        p = REFINED_DIR / fname
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for prod in json.load(f):
                rel = prod.get("image_local", "")
                if rel:
                    referenced.add((Path("outputs") / rel).resolve())

    deleted = 0
    for img in IMAGE_BASE.rglob("*.jpg"):
        if img.resolve() not in referenced:
            img.unlink()
            deleted += 1

    log.info("--clean: %d fisiere orfane sterse.", deleted)
    return deleted

def main():
    force   = "--force" in sys.argv
    clean   = "--clean" in sys.argv
    store_filter = next((a for a in sys.argv[1:] if not a.startswith("-")), None)

    if clean:
        clean_orphans()

    if force:
        log.info("Mod FORCE: re-descarca toate imaginile indiferent daca exista.")
    if store_filter:
        log.info("Filtru magazin: %s", store_filter)

    files = [f for f in STORE_FILES if not store_filter or store_filter in f]

    total = {"skip": 0, "download": 0, "fail": 0, "no_url": 0}
    for fname in files:
        store = fname.replace("refined_data_", "").replace(".json", "")
        log.info("▶ %s", store.upper())
        counts = sync_store(fname, force)
        if not counts:
            continue
        log.info("  skip=%-4d | descarcat=%-4d | esec=%-4d | fara_url=%-4d",
                 counts.get("skip", 0), counts.get("download", 0),
                 counts.get("fail", 0), counts.get("no_url", 0))
        for k in total:
            total[k] += counts.get(k, 0)

    log.info("─" * 55)
    log.info("TOTAL  skip=%-4d | descarcat=%-4d | esec=%-4d | fara_url=%-4d",
             total["skip"], total["download"], total["fail"], total["no_url"])

    all_products = []
    for fname in STORE_FILES:
        p = REFINED_DIR / fname
        if p.exists():
            with open(p, encoding="utf-8") as f:
                all_products.extend(json.load(f))

    with open(COMBINED, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=4, ensure_ascii=False)
    log.info("Salvat → %s (%d produse)", COMBINED, len(all_products))


if __name__ == "__main__":
    main()
