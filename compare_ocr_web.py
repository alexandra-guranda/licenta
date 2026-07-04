import json
import re
import sys
from pathlib import Path

from thefuzz import fuzz

WEB_DIR = Path("outputs/refined_llama")
OCR_DIR = Path("outputs/refined_llama_ocr")

STORE_PAIRS = [
    ("refined_data_auchan.json",     "refined_ocr_auchan.json",     "Auchan"),
    ("refined_data_kaufland.json",   "refined_ocr_kaufland.json",   "Kaufland"),
    ("refined_data_penny.json",      "refined_ocr_penny.json",      "Penny"),
    ("refined_data_profi.json",      "refined_ocr_profi.json",      "Profi"),
    ("refined_data_carrefour.json",  "refined_ocr_carrefour.json",  "Carrefour"),
    ("refined_data_mega_image.json", "refined_ocr_mega_image.json", "Mega Image"),
    ("refined_data_lidl.json",       "refined_ocr_lidl.json",       "Lidl"),
]

VALID_CATS = {
    "Panificatie & Dulciuri", "Carne & Mezeluri", "Lactate & Oua",
    "Legume & Fructe", "Bauturi", "Bacanie & Alimente de baza",
    "Ingrijire & Curatenie", "Casa & Diverse",
}

CATEGORY_KEYWORDS = {
    "Ingrijire & Curatenie":       ["detergent", "sampon", "sapun", "gel de dus", "deodorant",
                                    "pasta de dinti", "servetele", "scutece", "hartie igienica",
                                    "dezinfectant", "absorbante", "balsam"],
    "Panificatie & Dulciuri":      ["paine", "cozonac", "prajitura", "tort", "croissant",
                                    "ciocolata", "biscuiti", "inghetata", "napolitane", "wafer",
                                    "halva", "gogoasa", "chifla", "cereale"],
    "Carne & Mezeluri":            ["pui", "porc", "vita", "miel", "salam", "sunca", "parizer",
                                    "carnati", "piept", "pulpa", "muschi", "ceafa", "bacon",
                                    "mici", "curcan", "somon", "pastrav"],
    "Lactate & Oua":               ["lapte", "iaurt", "branza", "smantana", "unt", "oua",
                                    "cascaval", "telemea", "kefir", "mozzarella", "frisca"],
    "Bauturi":                     ["apa", "suc", "vin", "bere", "bautura", "nectar",
                                    "whisky", "vodka", "gin", "energizant", "pepsi", "fanta",
                                    "sprite", "cidru", "prosecco"],
    "Legume & Fructe":             ["legume", "fructe", "cartofi", "mere", "rosii", "ceapa",
                                    "banane", "portocale", "ardei", "ciuperci", "capsuni",
                                    "mango", "avocado", "broccoli", "spanac", "usturoi"],
    "Bacanie & Alimente de baza":  ["paste", "orez", "faina", "zahar", "ulei", "otet",
                                    "gem", "miere", "conserva", "ketchup", "mustar",
                                    "cafea", "ceai", "chips", "ton", "maioneza"],
    "Casa & Diverse":              ["hrana", "jucarie", "folie", "saci", "lumanare",
                                    "baterie", "sosete", "vopsea", "puzzle"],
}

STOP_WORDS = {"de", "si", "cu", "la", "pe", "a", "o", "al", "ale", "pentru",
              "din", "fara", "sau", "ori", "dar", "ci", "care"}

def significant_words(text: str) -> list[str]:
    return [w for w in re.findall(r"\w+", text.lower())
            if w not in STOP_WORDS and len(w) > 2]

def name_ok(raw: str, name: str) -> bool:
    if not name or len(name.strip()) < 3:
        return False
    nw = significant_words(name)
    if not nw:
        return False
    raw_low = raw.lower()
    matched = sum(1 for w in nw if w in raw_low)
    return (matched / len(nw)) >= 0.5

def cat_ok(raw: str, cat: str) -> bool:
    if cat not in VALID_CATS:
        return False
    raw_low = raw.lower()
    best, best_score = None, 0
    for c, kws in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in raw_low)
        if score > best_score:
            best_score, best = score, c
    if best_score == 0:
        return True
    return best == cat

def discount_pct(p: dict) -> float:
    d = float(p.get("discount") or 0)
    if d == 0:
        return 0.0
    return round(d * 100, 1) if d <= 1.0 else round(d, 1)

def stats(products: list[dict]) -> dict:
    total = len(products)
    if total == 0:
        return {}
    name_correct = sum(1 for p in products if name_ok(p.get("raw_name",""), p.get("name","")))
    cat_correct  = sum(1 for p in products if cat_ok(p.get("raw_name",""), p.get("category","")))
    with_discount = sum(1 for p in products if float(p.get("discount") or 0) != 0)
    cat_dist: dict[str, int] = {}
    for p in products:
        c = p.get("category", "Necategorizat")
        cat_dist[c] = cat_dist.get(c, 0) + 1
    return {
        "total":         total,
        "name_acc":      round(name_correct / total * 100, 1),
        "cat_acc":       round(cat_correct  / total * 100, 1),
        "disc_pct":      round(with_discount / total * 100, 1),
        "cat_dist":      dict(sorted(cat_dist.items(), key=lambda x: -x[1])),
    }

MATCH_THRESHOLD = 72   # scor minim fuzzy pentru a considera doua produse "identice"

def _score(a: str, b: str) -> int:
    return max(fuzz.token_set_ratio(a, b), fuzz.partial_ratio(a, b))

def compute_overlap(src: list[dict], tgt: list[dict]) -> tuple[list[dict], list[dict]]:
    tgt_names = [(p, p.get("raw_name", "").lower()) for p in tgt]
    matched, unmatched = [], []

    for sp in src:
        sn = sp.get("raw_name", "").lower()
        if not sn:
            unmatched.append(sp)
            continue
        best_score, best_tp = 0, None
        for tp, tn in tgt_names:
            s = _score(sn, tn)
            if s > best_score:
                best_score, best_tp = s, tp
        if best_score >= MATCH_THRESHOLD and best_tp:
            matched.append({**sp, "_match_score": best_score, "_match_raw": best_tp.get("raw_name", ""),
                             "_match_cat": best_tp.get("category", ""), "_match_price": best_tp.get("price_new")})
        else:
            unmatched.append(sp)

    return matched, unmatched

def top_examples(matched: list[dict], n: int = 6) -> list[dict]:
    seen, unique = set(), []
    for m in sorted(matched, key=lambda x: -x["_match_score"]):
        key = m["_match_raw"]
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique[:n]

def print_header(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

def compare_store(store: str, web: list[dict], ocr: list[dict]) -> None:
    sw = stats(web)
    so = stats(ocr)

    print_header(f"{store.upper()}")

    print(f"  Calcul overlap (poate dura cateva secunde)...", end="\r")
    w_matched, w_only  = compute_overlap(web, ocr)
    o_matched, o_only  = compute_overlap(ocr, web)

    w_in_ocr_pct = round(len(w_matched) / len(web) * 100, 1) if web else 0
    o_in_web_pct = round(len(o_matched) / len(ocr) * 100, 1) if ocr else 0

    print(f"  {'Metrica':<35} {'WEB':>10} {'OCR':>10}")
    print(f"  {'-'*57}")
    print(f"  {'Produse totale':<35} {sw['total']:>10} {so['total']:>10}")
    print(f"  {'Acuratete nume':<35} {sw['name_acc']:>9}% {so['name_acc']:>9}%")
    print(f"  {'Acuratete categorie':<35} {sw['cat_acc']:>9}% {so['cat_acc']:>9}%")
    print(f"  {'Cu discount':<35} {sw['disc_pct']:>9}% {so['disc_pct']:>9}%")
    print(f"  {'-'*57}")
    print(f"  {'Gasite si in cealalta sursa':<35} {len(w_matched):>7} ({w_in_ocr_pct}%) {len(o_matched):>4} ({o_in_web_pct}%)")
    print(f"  {'Doar in aceasta sursa':<35} {len(w_only):>10} {len(o_only):>10}")

    print(f"\n  {'Categorie':<32} {'WEB':>6} {'OCR':>6}")
    print(f"  {'-'*46}")
    all_cats = sorted(set(list(sw["cat_dist"].keys()) + list(so["cat_dist"].keys())))
    for cat in all_cats:
        wc = sw["cat_dist"].get(cat, 0)
        oc = so["cat_dist"].get(cat, 0)
        flag = "  " if wc == 0 or oc == 0 else ("✓ " if abs(wc - oc) / max(wc, oc) < 0.5 else "△ ")
        print(f"  {flag}{cat:<30} {wc:>6} {oc:>6}")

    examples = top_examples(w_matched, n=6)
    if examples:
        print(f"\n  Exemple produse comune (scor >= {MATCH_THRESHOLD}):")
        print(f"  {'Sc':>3}  {'WEB raw_name':<36} {'OCR raw_name':<36} {'Cat?':>4}  {'PretW':>6} {'PretO':>6}")
        print(f"  {'-'*100}")
        for m in examples:
            cat_flag = "==" if m.get("category") == m["_match_cat"] else "!="
            print(f"  {m['_match_score']:>3}  {m['raw_name'][:35]:<36} {m['_match_raw'][:35]:<36} "
                  f"{cat_flag:>4}  {str(m.get('price_new') or ''):>6} {str(m['_match_price'] or ''):>6}")

    if w_only:
        print(f"\n  Exemple produse DOAR in WEB (fara corespondent OCR):")
        for p in w_only[:5]:
            print(f"    [{p.get('category','?')[:20]:<20}] {p.get('raw_name','')[:55]}")

def main() -> None:
    store_filter = sys.argv[1].lower() if len(sys.argv) > 1 else None

    pairs = [
        (wf, of, name) for wf, of, name in STORE_PAIRS
        if not store_filter or store_filter in name.lower()
    ]

    if not pairs:
        print(f"Niciun magazin gasit pentru filtrul: {store_filter}")
        return

    total_web = total_ocr = 0
    name_web = name_ocr = cat_web = cat_ocr = disc_web = disc_ocr = 0

    for web_file, ocr_file, store in pairs:
        wp = WEB_DIR / web_file
        op = OCR_DIR / ocr_file
        if not wp.exists() or not op.exists():
            print(f"[SKIP] {store}: fisier lipsa ({wp.name} sau {op.name})")
            continue

        with open(wp, encoding="utf-8") as f:
            web = json.load(f)
        with open(op, encoding="utf-8") as f:
            ocr = json.load(f)

        compare_store(store, web, ocr)

        sw, so = stats(web), stats(ocr)
        total_web += sw["total"]; total_ocr += so["total"]
        name_web  += sum(1 for p in web if name_ok(p.get("raw_name",""), p.get("name","")))
        name_ocr  += sum(1 for p in ocr if name_ok(p.get("raw_name",""), p.get("name","")))
        cat_web   += sum(1 for p in web if cat_ok(p.get("raw_name",""), p.get("category","")))
        cat_ocr   += sum(1 for p in ocr if cat_ok(p.get("raw_name",""), p.get("category","")))
        disc_web  += sum(1 for p in web if float(p.get("discount") or 0) != 0)
        disc_ocr  += sum(1 for p in ocr if float(p.get("discount") or 0) != 0)

    if len(pairs) > 1:
        print_header("SUMAR GLOBAL — WEB vs OCR")
        print(f"  {'Metrica':<28} {'WEB':>10} {'OCR':>10}")
        print(f"  {'-'*50}")
        print(f"  {'Produse totale':<28} {total_web:>10} {total_ocr:>10}")
        print(f"  {'Acuratete nume':<28} {round(name_web/total_web*100,1):>9}% {round(name_ocr/total_ocr*100,1):>9}%")
        print(f"  {'Acuratete categorie':<28} {round(cat_web/total_web*100,1):>9}% {round(cat_ocr/total_ocr*100,1):>9}%")
        print(f"  {'Cu discount':<28} {round(disc_web/total_web*100,1):>9}% {round(disc_ocr/total_ocr*100,1):>9}%")
        print()

if __name__ == "__main__":
    main()
