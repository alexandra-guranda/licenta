import json
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def strip_diacritics(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

REFINED_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs/refined_llama")

CATEGORY_KEYWORDS = {
    "Ingrijire & Curatenie": [
        "detergent", "balsam", "sampon", "șampon", "sapun", "săpun",
        "gel de dus", "deodorant", "pasta de dinti", "pasta de dinți",
        "servetele", "șervețele", "scutece", "pampers",
        "prosop hartie", "hartie igienica", "hârtie igienică",
        "dezinfectant", "clor", "inalbitor", "înălbitor",
        "saci menajeri", "burete","absorbante"
    ],
    "Panificatie & Dulciuri": [
        "paine", "pâine", "cozonac", "prajitura", "prăjitură", "tort",
        "gogoasa", "gogoașă", "croissant", "briosa", "brioșă", "cornuri",
        "franzelă", "franzela", "chec", "tarta", "tartă", "ecler", "chifla",
        "foietaj", "placinta", "plăcintă", "pasca", "pască", "strudel",
        "multicereale", "secara", "secară", "graham",
        "halva", "rahat", "dropsuri", "napolitane", "napolitana",
        "biscuiti", "biscuiți", "ciocolata", "ciocolată",
        "inghetata", "înghețată", "wafer", "praline", "bomboane",
        "cereale mic dejun", "pernuta", "pernita",
    ],
    "Carne & Mezeluri": [
        "pui", "porc", "vita", "miel", "vitel", "curcan", "iepure",
        "carne de rata", "piept de rata", "pulpa de rata",
        "salam", "sunca", "parizer", "carnat", "carnati", "babic", "kaizer",
        "muschi", "cotlet", "piept", "pulpa", "aripi", "ceafa", "scaricica",
        "mici", "prosciutto", "bacon", "pastrama", "lebarvurst", "lebărvurst",
        "hamsii", "merluciu", "dorada", "somon",
        "calcan", "file de", "trunchi", "pește", "peste",
        "pastrav", "halibut", "tilapia", "jambon",
        "cubulețe", "cubule",
    ],
    "Lactate & Oua": [
        "lapte", "iaurt", "smantana", "branza", "branzica",
        "unt", "oua", "ou",
        "kefir", "telemea", "cascaval", "mozzarella", "ricotta", "mascarpone",
        "feta", "crema de branza", "cheddar", "parmezan", "emmental",
        "grana padano", "budinca", "frisca", "frișcă", "danonino",
    ],
    "Bauturi": [
        "apa", "suc", "vin", "bere", "limonada", "limonadă",
        "bautura", "băutură", "nectar", "smoothie", "energizant",
        "whisky", "vodka", "gin", "tequila", "prosecco", "brandy",
        "sampanie", "șampanie", "cidru", "kombucha", "rachiu", "palinca",
        "carbogazoasa", "carbogazoasă", "necarbogazoasa",
        "pepsi", "fanta", "sprite", "coca-cola",
    ],
    "Legume & Fructe": [
        "legume", "fructe", "cartofi", "mere", "pere", "rosii", "roșii",
        "castraveti", "ceapa", "telina", "dovleac", "ciuperci",
        "banane", "portocale", "lamaie", "lămâie",
        "capsuni", "căpșuni", "zmeura", "zmeuă", "afine", "prune", "piersici",
        "mango", "ananas", "avocado", "ardei", "broccoli", "conopida",
        "spanac", "varza", "vinete", "usturoi",
        "patrunjel", "marar", "ghimbir", "ridichi",
        "fasole verde", "mazare verde", "kiwi", "grepfrut", "grapefruit",
    ],
    "Bacanie & Alimente de baza": [
        "paste", "orez", "faina", "făină", "zahar", "zahăr", "ulei", "otet", "oțet",
        "gem", "dulceata", "dulceată", "miere",
        "linte", "naut",
        "conserva", "conservă",
        "ketchup", "mustar", "muștar", "maioneza", "maioneză",
        "piper", "condiment", "muesli", "granola", "fulgi",
        "pesmet", "amidon", "bicarbonat", "drojdie",
        "noodles", "couscous",
        "cafea",
        "chips", "chipsuri", "covrigei", "grisine", "stickletti",
        "migdale", "arahide", "nuci",
        "legume baza", "salata humus", "supa instant",
        "ton in", "ton bucati", "macrou in", "macrou sos", "hering in",
        "fasole boabe", "fasole alba", "fasole rosie", "mazare boabe",
        "ton la conserva",
        "macrou", "hering", "ton", "crap",
        "ceai",
        "in otet", "decojite", "rosii decojite", "vinete coapte", "coapte",
        "castraveti in otet", "ardei capia in otet",
        "fasole cu", "mazare",
        "pate", "pate de", "pasta vegetala",
        "sticks", "cu cascaval",
    ],
    "Casa & Diverse": [
        "hrana pentru", "hrană pentru", "hrana caini", "hrana pisici",
        "friskies", "purina", "whiskas", "pedigree", "royal canin",
        "jucarie", "jucărie", "figurine", "puzzle", "lego",
        "folie aluminiu", "saci menajeri", "lumanare", "lumânare",
        "electrocasnic", "baterie", "sosete", "șosete",
        "vopsea", "vopsea de",
    ],
}

NOISE_NAME_PATTERNS = [
    r"^\+\/?-?$",
    r"^[^\w]{0,3}$",
    r"Cä'",
    r"\bCä\b",
]
VALID_CATEGORIES = set(CATEGORY_KEYWORDS.keys()) | {"Necategorizat"}

def normalize(text: str) -> str:
    return text.lower().strip()


def _kw_match(kw: str, text: str) -> bool:
    return bool(re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE))

def name_is_correct(raw_name: str, name: str) -> tuple[bool, str]:
    raw_low  = strip_diacritics(normalize(raw_name))
    name_low = strip_diacritics(normalize(name))

    for pattern in NOISE_NAME_PATTERNS:
        if re.search(pattern, name, re.IGNORECASE):
            return False, f"artifact in name: '{name}'"

    if len(name_low) < 3:
        return False, f"name too short: '{name}'"

    words = name_low.split()
    if len(words) >= 4:
        first_half = " ".join(words[: len(words) // 2])
        second_half = " ".join(words[len(words) // 2 :])
        if first_half and first_half in second_half:
            return False, f"repeated text detected: '{name}'"

    STOP_WORDS = {
        "de", "si", "și", "cu", "la", "pe", "a", "o", "al", "ale", "pentru", "din",
        "fara", "fără", "sau", "ori", "ca", "dar", "ci", "nici", "deci", "dupa",
        "după", "sub", "prin", "între", "despre",
    }
    name_words = [w for w in re.findall(r"\w+", name_low) if w not in STOP_WORDS and len(w) > 2]

    if not name_words:
        return False, "no significant words in name"

    matched = sum(1 for w in name_words if w in raw_low)
    ratio = matched / len(name_words)

    if ratio < 0.6:
        return False, f"only {matched}/{len(name_words)} words match raw_name"

    return True, "ok"

def category_is_correct(raw_name: str, category: str) -> tuple[bool, str]:
    if category not in VALID_CATEGORIES:
        return False, f"unknown category: '{category}'"

    raw_low = normalize(raw_name)

    best_category = None
    best_score = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if _kw_match(kw, raw_low))
        if score > best_score:
            best_score = score
            best_category = cat

    if best_score == 0:
        return True, "no keywords matched (unclassifiable)"

    if best_category == category:
        return True, "ok"

    return False, f"expected '{best_category}' (score={best_score}) but got '{category}'"


def evaluate_file(filepath: Path) -> dict:
    with open(filepath, encoding="utf-8") as fh:
        products = json.load(fh)

    store = filepath.stem.replace("refined_data_", "").capitalize()
    total = len(products)
    name_ok = cat_ok = 0
    errors_name: list[dict] = []
    errors_cat: list[dict] = []

    for p in products:
        raw = p.get("raw_name", "")
        name = p.get("name", "")
        cat = p.get("category", "")

        n_ok, n_reason = name_is_correct(raw, name)
        c_ok, c_reason = category_is_correct(raw, cat)

        if n_ok:
            name_ok += 1
        else:
            errors_name.append({"raw_name": raw, "name": name, "reason": n_reason})

        if c_ok:
            cat_ok += 1
        else:
            errors_cat.append({"raw_name": raw, "category": cat, "reason": c_reason})

    return {
        "store": store,
        "total": total,
        "name_correct": name_ok,
        "name_accuracy": round(name_ok / total * 100, 2) if total else 0,
        "cat_correct": cat_ok,
        "cat_accuracy": round(cat_ok / total * 100, 2) if total else 0,
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

    print("=" * 80)
    print(f"{'Magazin':<18} {'Total':>6} {'Nume OK':>8} {'Acur. Nume':>13} {'Cat OK':>8} {'Acur. Cat':>12}")
    print("=" * 80)

    total_all = name_all = cat_all = 0
    for r in all_results:
        print(
            f"{r['store']:<18} {r['total']:>6} {r['name_correct']:>8} "
            f"{r['name_accuracy']:>11.2f}% {r['cat_correct']:>8} {r['cat_accuracy']:>10.2f}%"
        )
        total_all += r["total"]
        name_all += r["name_correct"]
        cat_all += r["cat_correct"]

    print("=" * 80)
    print(
        f"{'TOTAL':<18} {total_all:>6} {name_all:>8} "
        f"{name_all/total_all*100:>11.2f}% {cat_all:>8} {cat_all/total_all*100:>10.2f}%"
    )
    print()

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
