"""
Pipeline de rafinare cu Gemma3 — paralel cu reparator.py (Llama).
Toate regulile de post-procesare (fix_item, KEYWORD_CATEGORIES etc.)
sunt importate din reparator.py pentru a nu duplica logica.
Output: outputs/refined_gemma/
"""
import json
import logging
import re
import ollama
from pathlib import Path

from reparator import (
    AI_CATEGORIES,
    FALLBACK_CATEGORY,
    VALID_CATEGORIES,
    fix_item,
    _FEW_SHOT,
    _CATEGORY_GUIDE,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

INPUT_DIR  = Path("outputs/raw_web")
OUTPUT_DIR = Path("outputs/refined_gemma")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AI_MODEL      = "gemma3:12b"
AI_BATCH_SIZE = 1


def ai_refine_gemma(item: dict) -> dict:
    raw = item.get("raw_name", "").strip()
    raw_clean = re.sub(r"\s*\+\/\-?\s*", " ", raw).strip()

    prompt = (
        f"Esti un expert in retail romanesc. Analizeaza numele de produs si returneaza DOAR JSON.\n\n"
        f"{_CATEGORY_GUIDE}\n"
        f"{_FEW_SHOT}\n"
        f"REGULI STRICTE:\n"
        f"- nume_curat: numele produsului cu brand, cu gramaj (g/kg/ml/L), fara +/-\n"
        f"- brand: primul nume propriu din input. De obicei e in partea din mijloc sau spre final, si e scris cu litera mare. Daca nu exista brand clar, pune \"Generic\".\n"
        f"- categorie: EXACT una din cele 8 categorii de mai sus, fara modificari. De obicei, primul cuvant din nume indica si categoria.\n"
        f"- Raspunde DOAR cu JSON, fara text suplimentar\n\n"
        f"INPUT: \"{raw_clean}\"\n"
        f"OUTPUT:"
    )
    try:
        response = ollama.generate(
            model=AI_MODEL,
            prompt=prompt,
            format="json",
            options={"temperature": 0.0, "num_predict": 200},
        )
        parsed = json.loads(response["response"])
        normalized = {k.lower(): v for k, v in parsed.items()}
        return {
            "nume_curat": normalized.get("nume_curat") or normalized.get("name") or "",
            "brand":      normalized.get("brand") or "Generic",
            "categorie":  normalized.get("categorie") or normalized.get("category") or FALLBACK_CATEGORY,
        }
    except Exception as e:
        log.warning("Eroare Gemma [%s]: %s", raw[:40], e)
        return {}


def process_file(path: Path) -> None:
    with open(path, "r", encoding="utf-8") as f:
        raw_data: list[dict] = json.load(f)

    log.info("Procesare %s cu Gemma (%d produse)...", path.name, len(raw_data))

    interim: list[dict] = []
    for i, raw_item in enumerate(raw_data):
        ai = ai_refine_gemma(raw_item)
        interim.append({
            "store":         raw_item.get("store", ""),
            "raw_name":      raw_item.get("raw_name", ""),
            "name":          ai.get("nume_curat") or raw_item.get("raw_name", ""),
            "brand":         ai.get("brand") or "Generic",
            "category":      ai.get("categorie") or FALLBACK_CATEGORY,
            "price_new":     raw_item.get("price_new"),
            "price_old":     raw_item.get("price_old"),
            "discount":      raw_item.get("discount"),
            "image_url":     raw_item.get("image_url"),
            "image_local":   raw_item.get("local_image_path") or raw_item.get("image_local"),
            "requires_card": raw_item.get("requires_card", False),
        })
        print(f"  Gemma: {i + 1}/{len(raw_data)}", end="\r")

    print()
    fixed_data = [fix_item(item) for item in interim]

    cat_fixes   = sum(1 for a, b in zip(interim, fixed_data) if a.get("category") != b.get("category"))
    brand_fixes = sum(1 for a, b in zip(interim, fixed_data) if a.get("brand")    != b.get("brand"))
    name_fixes  = sum(1 for a, b in zip(interim, fixed_data) if a.get("name")     != b.get("name"))

    store_slug = path.name.replace("data_", "")
    out_path = OUTPUT_DIR / f"refined_data_{store_slug}"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(fixed_data, f, indent=4, ensure_ascii=False)

    log.info("%s → cat:%d brand:%d name:%d | salvat → %s",
             path.name, cat_fixes, brand_fixes, name_fixes, out_path)


if __name__ == "__main__":
    files = list(INPUT_DIR.glob("data_*.json"))
    if not files:
        log.warning("Niciun fisier data_*.json gasit in %s", INPUT_DIR)
    for f in sorted(files):
        process_file(f)
