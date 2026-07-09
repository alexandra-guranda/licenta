import sys
import re
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Rsc": "1",
    "Referer": "https://zgarcit.ro/",
}

COLLECTORS = {
    "auchan":     ("auchan_collector",     "auchan_precision_extractor"),
    "lidl":       ("lidl_collector",       "lidl_precision_extractor"),
    "kaufland":   ("kaufland_collector",   "kaufland_precision_extractor"),
    "carrefour":  ("carrefour_collector",  "carrefour_precision_extractor"),
    "mega_image": ("mega_image_collector", "mega_image_precision_extractor"),
    "penny":      ("penny_collector",      "penny_precision_extractor"),
    "profi":      ("profi_collector",      "profi_precision_extractor"),
}

def get_rsc_token() -> str | None:
    log.info("Detectare token RSC din zgarcit.ro: ")
    try:
        r = requests.get("https://zgarcit.ro/", headers={
            "User-Agent": HEADERS["User-Agent"],
        }, timeout=15)
        match = re.search(r'_rsc=([a-z0-9]+)', r.text)
        if match:
            token = match.group(1)
            log.info("Token RSC detectat automat: %s", token)
            return token

        r2 = requests.get(
            "https://zgarcit.ro/?providers=Penny&page=1&_rsc=test",
            headers=HEADERS, timeout=15, allow_redirects=False,
        )
        match2 = re.search(r'_rsc=([a-z0-9]+)', r2.headers.get("location", ""))
        if match2:
            token = match2.group(1)
            log.info("Token RSC din redirect: %s", token)
            return token

    except Exception as e:
        log.warning("Nu am putut detecta tokenul automat: %s", e)
    return None

def verify_token(token: str) -> bool:
    url = f"https://zgarcit.ro/?providers=Penny&page=1&_rsc={token}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and '"title"' in r.text:
            log.info("Token valid: %s", token)
            return True
    except Exception:
        pass
    log.warning("Token invalid sau expirat: %s", token)
    return False


def run_collector(store: str, token: str) -> bool:
    entry = COLLECTORS.get(store)
    if not entry:
        log.warning("Magazin necunoscut: %s", store)
        return False
    module_name, func_name = entry
    try:
        import importlib
        mod = importlib.import_module(module_name)
        func = getattr(mod, func_name)
        func(token)
        return True
    except ModuleNotFoundError:
        log.error("Fisier %s.py nu exista.", module_name)
        return False
    except Exception as e:
        log.error("Eroare la %s: %s", store, e)
        return False


def main():
    requested = [s.lower() for s in sys.argv[1:]] or list(COLLECTORS.keys())
    token = get_rsc_token()
    if not token or not verify_token(token):
        log.error(
            "Nu s-a putut detecta tokenul RSC automat.\n"
        )
        for arg in sys.argv[1:]:
            if arg.startswith("--token="):
                token = arg.split("=", 1)[1]
                break
            if arg == "--token" and sys.argv.index(arg) + 1 < len(sys.argv):
                token = sys.argv[sys.argv.index(arg) + 1]
                break
        if not token:
            return

    log.info("Token activ: %s", token)

    stores = [s for s in requested if s in COLLECTORS]
    for store in stores:
        log.info("▶ Colectare %s...", store.upper())
        run_collector(store, token)

    log.info("▶ Descarcare imagini (force)...")
    from image_sync import sync_store, STORE_FILES, COMBINED, REFINED_DIR
    import json

    for fname in STORE_FILES:
        if not any(s in fname for s in stores):
            continue
        counts = sync_store(fname, force=True)
        if counts:
            log.info("  %s: descarcat=%d esec=%d", fname, counts.get("download", 0), counts.get("fail", 0))

    all_products = []
    for fname in STORE_FILES:
        p = REFINED_DIR / fname
        if p.exists():
            with open(p, encoding="utf-8") as f:
                all_products.extend(json.load(f))
    with open(COMBINED, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=4, ensure_ascii=False)
    log.info("Gata! %d produse in %s", len(all_products), COMBINED)

if __name__ == "__main__":
    main()
