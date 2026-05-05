import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Accepta directorul ca argument: python eval_accuracy.py outputs/refined_gemma
REFINED_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs/refined")

# Keywords per category for category validation
CATEGORY_KEYWORDS = {
    "Carne & Mezeluri": [
        "pui", "porc", "vita", "miel", "rata", "vitel", "curcan", "iepure",
        "salam", "sunca", "parizer", "carnat", "carnati", "babic", "kaizer",
        "muschi", "cotlet", "piept", "pulpa", "aripi", "ceafa", "scaricica",
        "mici", "prosciutto", "bacon", "pastrama", "lebarvurst", "lebărvurst",
        "hamsii", "merluciu", "dorada", "macrou", "somon", "ton", "crap",
        "hering", "calcan", "file de", "file ", "trunchi", "pește", "peste",
        "pastrav", "halibut", "tilapia", "somn ",
        "cubulețe", "cubule", "jambon",
    ],
    "Lactate & Oua": [
        "lapte", "iaurt", "smantana", "branza", "unt", "oua", "ou ", "ou,",
        "kefir", "telemea", "cascaval", "mozzarella", "ricotta", "mascarpone",
        "feta", "crema de branza", "cheddar", "parmezan", "emmental",
        "budinca", "frisca", "frișcă",
    ],
    "Legume & Fructe": [
        "legume", "fructe", "cartofi", "mere", "pere", "rosii", "roșii",
        "castraveti", "ceapa", "telina", "dovleac", "ciuperci", "stafide",
        "migdale", "nuci", "alune", "banane", "portocale", "lamaie", "lămâie",
        "capsuni", "căpșuni", "zmeura", "zmeuă", "afine", "prune", "piersici",
        "mango", "ananas", "avocado", "ardei", "broccoli", "conopida",
        "spanac", "salata ", "salată", "varza", "vinete", "usturoi",
        "patrunjel", "marar", "ghimbir", "hrean", "ridichi", "mazare ",
        "fasole verde", "kiwi", "grepfrut", "grapefruit",
    ],
    "Bacanie & Alimente de baza": [
        "paste", "orez", "faina", "făină", "zahar", "zahăr", "ulei", "otet",
        "oțet", "sos", "gem", "dulceata", "dulceată", "miere", "cafea",
        "ceai", "napolitana", "napolitane", "biscuiti", "biscuiți",
        "ciocolata", "ciocolată", "mazare", "fasole", "linte",
        "conserva", "conservă", "naut", "ton la conserva",
        "ketchup", "mustar", "muștar", "maioneza", "maioneză",
        "sare", "piper", "condiment", "muesli", "granola", "fulgi",
        "pesmet", "amidon", "bicarbonat", "drojdie",
        "noodles", "couscous",
    ],
    "Bauturi": [
        "apa ", "apă", "suc", "vin ", "bere", "limonada", "limonadă",
        "bautura", "băutură", "nectar", "smoothie", "energizant",
        "cola", "sprite", "pepsi", "fanta", "aqua", "natural",
        "whisky", "vodka", "rom ", "gin ", "tequila", "prosecco",
        "sampanie", "șampanie", "cidru", "kombucha",
        "carbogazoasa", "carbogazoasă", "necarbogazoasa",
    ],
    "Panificatie & Dulciuri": [
        "paine", "pâine", "cozonac", "prajitura", "prăjitură", "tort",
        "gogoasa", "gogoașă", "croissant", "briosa", "brioșă", "cornuri",
        "franzelă", "franzela", "chec", "tarta", "tartă", "ecler",
        "foietaj", "placinta", "plăcintă", "pasca", "pască",
        "multicereale", "secara", "secară", "graham",
        "halva", "rahat", "dropsuri",
    ],
    "Ingrijire & Curatenie": [
        "detergent", "balsam", "șampon", "sampon", "sapun", "săpun",
        "gel de dus", "deodorant", "pasta de dinti", "pasta de dinți",
        "servetele", "șervețele", "hartie", "hârtie", "scutece",
        "pampers", "saci menajeri", "saci ", "prosop", "burete",
        "dezinfectant", "clor", "inalbitor", "înălbitor",
    ],
    "Hrana animale": [
        "hrana pentru", "hrană pentru", "caini", "câini", "pisici",
        "friskies", "purina", "whiskas", "pedigree", "royal canin",
    ],
}

NOISE_NAME_PATTERNS = [
    r"^\+\/?-?$",           # just "+/-"
    r"^[^\w]{0,3}$",        # too short / non-word
    r"Cä'",                  # encoding artifact
    r"\bCä\b",
]

VALID_CATEGORIES = set(CATEGORY_KEYWORDS.keys())


def normalize(text: str) -> str:
    return text.lower().strip()


def name_is_correct(raw_name: str, name: str) -> tuple[bool, str]:
    """Check if the extracted name is a reasonable derivation of raw_name."""
    raw_low = normalize(raw_name)
    name_low = normalize(name)

    # Check for obvious noise/artifacts
    for pattern in NOISE_NAME_PATTERNS:
        if re.search(pattern, name, re.IGNORECASE):
            return False, f"artifact in name: '{name}'"

    # Name must not be empty
    if len(name_low) < 3:
        return False, f"name too short: '{name}'"

    # Check for repeated text (duplication artifacts like "Cămara Cä'Mara")
    words = name_low.split()
    if len(words) >= 4:
        first_half = " ".join(words[: len(words) // 2])
        second_half = " ".join(words[len(words) // 2 :])
        if first_half and first_half in second_half:
            return False, f"repeated text detected: '{name}'"

    # The significant words from name should appear in raw_name
    STOP_WORDS = {"de", "si", "și", "cu", "la", "pe", "a", "o", "al", "ale", "pentru", "din",
                  "fara", "fără", "sau", "ori", "ca", "dar", "ci", "nici", "deci", "dupa",
                  "după", "sub", "prin", "între", "între", "despre"}
    name_words = [w for w in re.findall(r"\w+", name_low) if w not in STOP_WORDS and len(w) > 2]

    if not name_words:
        return False, "no significant words in name"

    matched = sum(1 for w in name_words if w in raw_low)
    ratio = matched / len(name_words)

    if ratio < 0.6:
        return False, f"only {matched}/{len(name_words)} words match raw_name"

    return True, "ok"


def category_is_correct(raw_name: str, category: str) -> tuple[bool, str]:
    """Check if the category matches the product based on raw_name keywords."""
    if category not in VALID_CATEGORIES:
        return False, f"unknown category: '{category}'"

    raw_low = normalize(raw_name)

    # Find which category the keywords suggest
    best_category = None
    best_score = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in raw_low)
        if score > best_score:
            best_score = score
            best_category = cat

    if best_score == 0:
        # No keywords matched at all - can't determine, give benefit of doubt
        return True, "no keywords matched (unclassifiable)"

    if best_category == category:
        return True, "ok"

    return False, f"expected '{best_category}' (score={best_score}) but got '{category}'"


def evaluate_file(filepath: Path) -> dict:
    with open(filepath, encoding="utf-8") as f:
        products = json.load(f)

    store = filepath.stem.replace("refined_data_", "").capitalize()
    total = len(products)
    name_ok = 0
    cat_ok = 0
    errors_name = []
    errors_cat = []

    for p in products:
        raw = p.get("raw_name", "")
        name = p.get("name", "")
        cat = p.get("category", "")

        n_ok, n_reason = name_is_correct(raw, name)
        c_ok, c_reason = category_is_correct(raw, cat)

        if n_ok:
            name_ok += 1
        else:
            errors_name.append({
                "raw_name": raw,
                "name": name,
                "reason": n_reason,
            })

        if c_ok:
            cat_ok += 1
        else:
            errors_cat.append({
                "raw_name": raw,
                "category": cat,
                "reason": c_reason,
            })

    return {
        "store": store,
        "total": total,
        "name_correct": name_ok,
        "name_accuracy": round(name_ok / total * 100, 1) if total else 0,
        "cat_correct": cat_ok,
        "cat_accuracy": round(cat_ok / total * 100, 1) if total else 0,
        "name_errors": errors_name,
        "cat_errors": errors_cat,
    }


def main():
    files = sorted(REFINED_DIR.glob("refined_data_*.json"))
    if not files:
        print("Nu am gasit fisiere refined.")
        return

    all_results = []
    for fp in files:
        result = evaluate_file(fp)
        all_results.append(result)

    # Print summary table
    print("=" * 75)
    print(f"{'Magazin':<18} {'Total':>6} {'Nume OK':>8} {'Acur. Nume':>12} {'Cat OK':>8} {'Acur. Cat':>11}")
    print("=" * 75)

    total_all = name_all = cat_all = 0
    for r in all_results:
        print(
            f"{r['store']:<18} {r['total']:>6} {r['name_correct']:>8} "
            f"{r['name_accuracy']:>10.1f}% {r['cat_correct']:>8} {r['cat_accuracy']:>10.1f}%"
        )
        total_all += r["total"]
        name_all += r["name_correct"]
        cat_all += r["cat_correct"]

    print("=" * 75)
    print(
        f"{'TOTAL':<18} {total_all:>6} {name_all:>8} "
        f"{name_all/total_all*100:>10.1f}% {cat_all:>8} {cat_all/total_all*100:>10.1f}%"
    )
    print()

    # Print detailed errors per store
    for r in all_results:
        print(f"\n{'='*75}")
        print(f"  {r['store'].upper()} — Erori Nume ({len(r['name_errors'])} din {r['total']})")
        print(f"{'='*75}")
        for e in r["name_errors"][:20]:
            print(f"  raw:    {e['raw_name']}")
            print(f"  name:   {e['name']}")
            print(f"  motiv:  {e['reason']}")
            print()

        print(f"\n  {r['store'].upper()} — Erori Categorie ({len(r['cat_errors'])} din {r['total']})")
        print(f"  {'raw_name':<45} {'categorie gresita':<28} motiv")
        print(f"  {'-'*110}")
        for e in r["cat_errors"][:20]:
            print(f"  {e['raw_name'][:44]:<45} {e['category']:<28} {e['reason']}")


if __name__ == "__main__":
    main()
