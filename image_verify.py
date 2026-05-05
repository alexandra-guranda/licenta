"""
Verificare si corectare imagini cu vision AI (gemma3:12b).

Logica per imagine:
  1. Vision model descrie ce vede.
  2. Fuzzy match descrierea cu toate produsele din JSON.
  3. Daca best match != produsul curent al imaginii:
       - Redenumeste fisierul la slug-ul produsului corect
       - Actualizeaza image_local in JSON pentru produsul corect
       - Seteaza logo magazin pentru produsul care ramanea fara imagine
  4. Daca scorul e sub prag → logo magazin.

Utilizare:
  python image_verify.py                    # toate magazinele
  python image_verify.py --store penny      # un singur magazin
  python image_verify.py --limit 50         # primele 50 imagini
  python image_verify.py --only-wrong       # sari peste imaginile deja verificate OK
  python image_verify.py --dry-run          # simuleaza fara sa modifice nimic
"""
import argparse
import base64
import json
import logging
import re
import shutil
import sys
from pathlib import Path

import ollama
from thefuzz import fuzz

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REFINED_DIR    = Path("outputs/refined")
IMAGE_BASE     = Path("outputs/data/images")           # sursa originala (read-only)
IMAGE_VERIFIED = Path("outputs/data/images_verified")  # destinatie verificata
CHECKPOINT     = Path("outputs/image_verify_checkpoint.json")

STORE_FILES = [
    "refined_data_auchan.json",
    "refined_data_kaufland.json",
    "refined_data_penny.json",
    "refined_data_profi.json",
    "refined_data_carrefour.json",
    "refined_data_mega_image.json",
    "refined_data_lidl.json",
]

STORE_LOGOS = {
    "auchan":     "assets/logos/auchan.png",
    "lidl":       "assets/logos/lidl.png",
    "kaufland":   "assets/logos/kaufland.png",
    "carrefour":  "assets/logos/carrefour.png",
    "mega_image": "assets/logos/mega_image.png",
    "penny":      "assets/logos/penny.png",
    "profi":      "assets/logos/profi.png",
}

VISION_MODEL   = "gemma3:12b"
MATCH_OK       = 65   # scor minim ca imaginea sa fie considerata corecta
MATCH_REMAP    = 70   # scor minim ca sa remapam imaginea la alt produs


def slugify(text: str) -> str:
    if not text:
        return "produs_fara_nume"
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:80]


def store_slug(store: str) -> str:
    return store.lower().replace(" ", "_")


def logo_for(store: str) -> str:
    return STORE_LOGOS.get(store_slug(store), "assets/logos/generic.png")


def describe_image(image_path: Path) -> str:
    """Trimite imaginea la vision model. Returneaza 'Brand | tip produs'."""
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    prompt = (
        "You are a retail expert. Look at this supermarket product image.\n"
        "Reply with ONLY two parts separated by | :\n"
        "  1. The brand name (e.g. Carlsberg, Agricola, Milka)\n"
        "  2. The product type in Romanian (e.g. bere blonda, piept de pui, ciocolata lapte)\n"
        "Example replies:\n"
        "  Carlsberg | bere blonda doza\n"
        "  Agricola | piept de pui dezosat\n"
        "  Milka | ciocolata cu lapte\n"
        "No other text. If brand is unclear write Generic."
    )
    try:
        response = ollama.generate(
            model=VISION_MODEL,
            prompt=prompt,
            images=[img_b64],
            options={"temperature": 0.0, "num_predict": 30},
        )
        raw = response["response"].strip().strip("\"'")
        # Normalizeaza separatorul (modelul poate folosi : sau -)
        raw = re.sub(r"\s*[:\-]\s*", " | ", raw, count=1)
        return raw
    except Exception as e:
        log.debug("Vision error pe %s: %s", image_path.name, e)
        return ""


def _extract_brand(description: str) -> str:
    """Extrage brandul din descriere (partea dinainte de |)."""
    if "|" in description:
        return description.split("|")[0].strip().lower()
    return description.split()[0].lower() if description else ""


def best_match(description: str, products: list[dict]) -> tuple[dict | None, int]:
    """
    Matching in doua etape:
      1. Filtreaza produsele care contin brandul detectat (daca e clar).
      2. Fuzzy match pe candidatii filtrati; fallback pe toate produsele.
    """
    if not description:
        return None, 0

    desc_low  = description.lower().replace("|", " ")
    brand_key = _extract_brand(description)

    # Etapa 1: candidati cu acelasi brand
    candidates = products
    if brand_key and brand_key != "generic" and len(brand_key) > 2:
        filtered = [
            p for p in products
            if brand_key in (p.get("brand") or "").lower()
            or brand_key in (p.get("raw_name") or "").lower()
        ]
        if filtered:
            candidates = filtered

    best_prod  = None
    best_score = 0

    for prod in candidates:
        candidate = f"{prod.get('brand', '')} {prod.get('raw_name', '')} {prod.get('name', '')}".lower()
        score = max(
            fuzz.token_set_ratio(desc_low, candidate),
            fuzz.partial_ratio(desc_low, candidate),
        )
        if score > best_score:
            best_score = score
            best_prod  = prod

    # Daca nu s-a gasit nimic bun in candidatii filtrati, incearca pe toate
    if best_score < MATCH_REMAP and candidates is not products:
        for prod in products:
            candidate = f"{prod.get('brand', '')} {prod.get('raw_name', '')} {prod.get('name', '')}".lower()
            score = max(
                fuzz.token_set_ratio(desc_low, candidate),
                fuzz.partial_ratio(desc_low, candidate),
            )
            if score > best_score:
                best_score = score
                best_prod  = prod

    return best_prod, best_score


def load_all_products(store_filter: str | None) -> tuple[list[dict], dict[str, list[dict]]]:
    """Incarca toate produsele. Returneaza (lista_plata, dict_per_fisier)."""
    all_products: list[dict] = []
    per_file: dict[str, list[dict]] = {}

    for fname in STORE_FILES:
        if store_filter and store_filter not in fname:
            continue
        path = REFINED_DIR / fname
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        per_file[fname] = data
        all_products.extend(data)

    return all_products, per_file


def save_all(per_file: dict[str, list[dict]], dry_run: bool) -> None:
    if dry_run:
        log.info("[DRY-RUN] Nu salvez nimic.")
        return
    for fname, data in per_file.items():
        path = REFINED_DIR / fname
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    log.info("JSON-uri salvate.")


def load_checkpoint() -> dict:
    if CHECKPOINT.exists():
        with open(CHECKPOINT, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_checkpoint(data: dict) -> None:
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def build_image_to_prod(all_products: list[dict]) -> dict[Path, dict]:
    """Construieste maparea: cale_absoluta_imagine -> produs."""
    mapping: dict[Path, dict] = {}
    for prod in all_products:
        rel = prod.get("image_local", "")
        if not rel or "logo" in rel or "assets" in rel:
            continue
        abs_path = (Path("outputs") / rel).resolve()
        mapping[abs_path] = prod
    return mapping


def process_image(
    img_path: Path,
    claimed_prod: dict | None,
    all_products: list[dict],
    checkpoint: dict,
    dry_run: bool,
) -> str:
    """
    Verifica o imagine. Returneaza statusul:
      'correct'  - imaginea se potriveste cu produsul din JSON
      'remapped' - imaginea a fost atribuita altui produs
      'logo'     - nu s-a putut identifica, s-a pus logo
      'skip'     - sarit (checkpoint sau nu e in JSON)
    """
    key = str(img_path)

    # Sarim daca am verificat deja si era corect
    if key in checkpoint and checkpoint[key] == "correct":
        return "skip"

    description = describe_image(img_path)
    if not description:
        return "logo"

    matched_prod, score = best_match(description, all_products)

    claimed_key  = id(claimed_prod)  if claimed_prod  else None
    matched_key  = id(matched_prod)  if matched_prod  else None

    log.debug(
        "%s | desc='%s' | match='%s' (score=%d)",
        img_path.name[:40], description[:40],
        matched_prod.get("raw_name", "?")[:40] if matched_prod else "?", score
    )

    # Imaginea se potriveste cu produsul curent → copiem in folderul verificat
    if score >= MATCH_OK and matched_key == claimed_key:
        if not dry_run and claimed_prod:
            store     = store_slug(claimed_prod.get("store", ""))
            new_abs   = IMAGE_VERIFIED / store / img_path.name
            new_rel   = f"data/images_verified/{store}/{img_path.name}"
            try:
                new_abs.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(img_path, new_abs)
                claimed_prod["image_local"] = new_rel
            except Exception as e:
                log.debug("Copy correct esuat %s: %s", img_path.name, e)
        checkpoint[key] = "correct"
        return "correct"

    # Imaginea se potriveste mai bine cu un alt produs
    if score >= MATCH_REMAP and matched_prod and matched_key != claimed_key:
        store   = store_slug(matched_prod.get("store", ""))
        new_fname = slugify(matched_prod.get("raw_name", "produs")) + ".jpg"
        new_abs   = IMAGE_VERIFIED / store / new_fname
        new_rel   = f"data/images_verified/{store}/{new_fname}"

        if not dry_run:
            # Copiem fisierul in folderul verificat (nu stergem originalul)
            try:
                new_abs.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(img_path, new_abs)
            except Exception as e:
                log.warning("Copy esuat %s → %s: %s", img_path.name, new_fname, e)
                return "logo"

            # Actualizam produsul corect cu noua cale
            matched_prod["image_local"] = new_rel

            # Produsul vechi (care pretindea aceasta imagine) primeste logo
            if claimed_prod:
                claimed_prod["image_local"] = logo_for(claimed_prod.get("store", ""))

        log.info(
            "REMAP: '%s' → '%s' (score=%d) | '%s'",
            img_path.name[:35],
            new_fname[:35],
            score,
            matched_prod.get("raw_name", "")[:35],
        )
        checkpoint[key] = "remapped"
        return "remapped"

    # Nu s-a putut identifica → logo
    if claimed_prod and not dry_run:
        claimed_prod["image_local"] = logo_for(claimed_prod.get("store", ""))

    log.info("LOGO: '%s' | desc='%s' (best score=%d)", img_path.name[:40], description[:40], score)
    checkpoint[key] = "logo"
    return "logo"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--store",      default=None,  help="Filtru magazin (ex: penny, lidl)")
    parser.add_argument("--limit",      type=int, default=0, help="Proceseaza maxim N imagini")
    parser.add_argument("--only-wrong", action="store_true",  help="Sari peste imaginile deja verificate OK")
    parser.add_argument("--dry-run",    action="store_true",  help="Simuleaza fara modificari")
    args = parser.parse_args()

    if args.dry_run:
        log.info("[DRY-RUN] Niciun fisier nu va fi modificat.")

    # Incarca date
    all_products, per_file = load_all_products(args.store)
    if not all_products:
        log.error("Niciun produs gasit.")
        return

    log.info("Produse incarcate: %d din %d fisiere", len(all_products), len(per_file))

    image_to_prod = build_image_to_prod(all_products)
    checkpoint    = load_checkpoint()

    # Selectam imaginile de procesat
    if args.store:
        images = [
            img for img in IMAGE_BASE.rglob("*.jpg")
            if args.store in str(img)
        ]
    else:
        images = list(IMAGE_BASE.rglob("*.jpg"))

    if args.only_wrong:
        images = [i for i in images if checkpoint.get(str(i)) != "correct"]

    if args.limit:
        images = images[: args.limit]

    log.info("Imagini de verificat: %d", len(images))

    # Procesare
    counts = {"correct": 0, "remapped": 0, "logo": 0, "skip": 0}
    for idx, img_path in enumerate(images, 1):
        claimed = image_to_prod.get(img_path.resolve())
        status  = process_image(img_path, claimed, all_products, checkpoint, args.dry_run)
        counts[status] += 1

        # Salvam checkpoint si JSON-uri periodic
        if idx % 20 == 0:
            save_checkpoint(checkpoint)
            save_all(per_file, args.dry_run)
            log.info(
                "[%d/%d] correct=%d remap=%d logo=%d skip=%d",
                idx, len(images),
                counts["correct"], counts["remapped"], counts["logo"], counts["skip"],
            )

    # Salvam tot la final
    save_checkpoint(checkpoint)
    save_all(per_file, args.dry_run)

    # Regeneram REFINED_WEB_DATA.json
    if not args.dry_run:
        all_updated = []
        for fname in STORE_FILES:
            p = REFINED_DIR / fname
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    all_updated.extend(json.load(f))
        combined = REFINED_DIR / "REFINED_WEB_DATA.json"
        with open(combined, "w", encoding="utf-8") as f:
            json.dump(all_updated, f, indent=4, ensure_ascii=False)
        log.info("Salvat → %s (%d produse)", combined, len(all_updated))

    log.info("=" * 55)
    log.info("REZULTAT FINAL:")
    log.info("  Corecte (neschimbate):  %d", counts["correct"])
    log.info("  Remapate (corectate):   %d", counts["remapped"])
    log.info("  Logo fallback:          %d", counts["logo"])
    log.info("  Sarite (din checkpoint):%d", counts["skip"])
    log.info("  TOTAL procesate:        %d", sum(counts.values()))


if __name__ == "__main__":
    main()
