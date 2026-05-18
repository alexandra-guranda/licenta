"""
Analiza overlap exact/aproape-exact intre produsele OCR si Web.
Afiseaza distributia scorurilor si exemple la fiecare prag.

Utilizare:
    python overlap_exact.py
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from thefuzz import fuzz

REFINED_DIR = Path("outputs/refined")

STORE_PAIRS = [
    ("refined_data_auchan.json",     "refined_ocr_auchan.json",     "Auchan"),
    ("refined_data_kaufland.json",   "refined_ocr_kaufland.json",   "Kaufland"),
    ("refined_data_penny.json",      "refined_ocr_penny.json",      "Penny"),
    ("refined_data_profi.json",      "refined_ocr_profi.json",      "Profi"),
    ("refined_data_carrefour.json",  "refined_ocr_carrefour.json",  "Carrefour"),
    ("refined_data_mega_image.json", "refined_ocr_mega_image.json", "Mega Image"),
]

THRESHOLDS = [100, 95, 90, 85, 80, 72]


def score(a: str, b: str) -> int:
    return max(fuzz.token_set_ratio(a, b), fuzz.partial_ratio(a, b))


def match_ocr_to_web(ocr: list[dict], web: list[dict]) -> list[dict]:
    """Pentru fiecare produs OCR, gaseste cel mai bun match in web."""
    web_items = [(p, p.get("raw_name", "").lower()) for p in web]
    results = []
    for op in ocr:
        on = op.get("raw_name", "").lower()
        if not on:
            continue
        best_s, best_wp = 0, None
        for wp, wn in web_items:
            s = score(on, wn)
            if s > best_s:
                best_s, best_wp = s, wp
        results.append({
            "ocr_raw":   op.get("raw_name", ""),
            "ocr_cat":   op.get("category", ""),
            "ocr_price": op.get("price_new"),
            "web_raw":   best_wp.get("raw_name", "") if best_wp else "",
            "web_cat":   best_wp.get("category", "") if best_wp else "",
            "web_price": best_wp.get("price_new") if best_wp else None,
            "score":     best_s,
        })
    return results


def main():
    all_results = []

    for web_file, ocr_file, store in STORE_PAIRS:
        wp = REFINED_DIR / web_file
        op = REFINED_DIR / ocr_file
        if not wp.exists() or not op.exists():
            continue

        with open(wp, encoding="utf-8") as f:
            web = json.load(f)
        with open(op, encoding="utf-8") as f:
            ocr = json.load(f)

        print(f"  Procesare {store}...", end="\r")
        results = match_ocr_to_web(ocr, web)
        for r in results:
            r["store"] = store
        all_results.extend(results)

    total_ocr = len(all_results)
    print(f"\n{'='*65}")
    print(f"  OVERLAP OCR → WEB  ({total_ocr} produse OCR totale)")
    print(f"{'='*65}")

    # Distributia la fiecare prag
    print(f"\n  {'Prag scor':<12} {'Gasite':>8} {'%':>8}  Interpretare")
    print(f"  {'-'*60}")
    prev = 0
    for t in THRESHOLDS:
        count = sum(1 for r in all_results if r["score"] >= t)
        pct = round(count / total_ocr * 100, 1)
        if t == 100:
            interp = "identice (acelasi text)"
        elif t == 95:
            interp = "aproape identice (diferente minore)"
        elif t == 90:
            interp = "foarte similare (brand + tip produs)"
        elif t == 85:
            interp = "similare (produse echivalente)"
        elif t == 80:
            interp = "partial similare"
        else:
            interp = "fuzzy match de baza"
        print(f"  >= {t:<9} {count:>8} {pct:>7}%  {interp}")

    # Per magazin la pragul 90 (cel mai relevant)
    print(f"\n{'='*65}")
    print(f"  OVERLAP PER MAGAZIN (prag >= 90 = 'aproape identice')")
    print(f"{'='*65}")
    print(f"  {'Magazin':<14} {'OCR total':>10} {'Gasite >=90':>12} {'%':>8} {'Gasite =100':>12} {'%':>8}")
    print(f"  {'-'*65}")

    for _, _, store in STORE_PAIRS:
        store_res = [r for r in all_results if r["store"] == store]
        if not store_res:
            continue
        n = len(store_res)
        n90  = sum(1 for r in store_res if r["score"] >= 90)
        n100 = sum(1 for r in store_res if r["score"] == 100)
        p90  = round(n90 / n * 100, 1) if n else 0
        p100 = round(n100 / n * 100, 1) if n else 0
        print(f"  {store:<14} {n:>10} {n90:>12} {p90:>7}% {n100:>12} {p100:>7}%")

    # Exemple identice (score = 100)
    exact = [r for r in all_results if r["score"] == 100]
    print(f"\n  Exemple IDENTICE (score=100) — {len(exact)} produse:")
    print(f"  {'-'*90}")
    print(f"  {'Magazin':<12} {'OCR raw_name':<35} {'WEB raw_name':<35} {'PretO':>6} {'PretW':>6}")
    print(f"  {'-'*90}")
    seen, shown = set(), 0
    for r in exact:
        if r["ocr_raw"] in seen or shown >= 15:
            continue
        seen.add(r["ocr_raw"])
        price_match = "==" if r["ocr_price"] == r["web_price"] else "!="
        print(f"  {r['store']:<12} {r['ocr_raw'][:34]:<35} {r['web_raw'][:34]:<35} "
              f"{str(r['ocr_price'] or ''):>6} {price_match} {str(r['web_price'] or ''):>6}")
        shown += 1

    # Exemple fara match (score < 72)
    nomatch = [r for r in all_results if r["score"] < 72]
    print(f"\n  Produse OCR FARA corespondent in web ({len(nomatch)}) — exemple:")
    print(f"  {'-'*65}")
    for r in nomatch[:10]:
        print(f"  [{r['store']:<12}] {r['ocr_raw'][:55]}")


if __name__ == "__main__":
    main()
