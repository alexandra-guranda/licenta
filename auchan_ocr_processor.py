import fitz
import easyocr
import ollama
import json
import time
import re
from pathlib import Path

INPUT_FILE = Path("inputs/Auchan.pdf")
OUTPUT_FILE = Path("outputs/ocr_auchan.json")

SKIP_LINES = {
    "lei", "lei/kg", "lei/buc", "valabilitate", "oferta", "oferte",
    "promotii", "auchan", "card", "pret cu card", "pret fara card",
    "preț cu card", "preț fără card", "de la", "dela", "bun",
    "diverse sortimente", "limita stocului", "stoc limitat",
}

NOISE_RE = re.compile(
    r'^-?\d+\s*%$'
    r'|^\d{1,3}[gG]$'
    r'|^\d+x\d+$'
    r'|^[^a-zA-ZăâîșțĂÂÎȘȚa-z]{1,3}$',
    re.IGNORECASE
)


def page_to_text(reader, page) -> str:
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    results = reader.readtext(pix.tobytes("png"))
    lines = []
    for _, text, conf in results:
        t = text.strip()
        if conf < 0.35 or not t:
            continue
        if t.lower() in SKIP_LINES:
            continue
        if NOISE_RE.match(t):
            continue
        lines.append(t)
    return " | ".join(lines)


def llm_extract(page_text: str, store: str = "Auchan") -> list[dict]:
    prompt = (
        "Esti expert in retail romanesc. Analizeaza textul de pe o pagina de catalog supermarket.\n"
        "IMPORTANT: Preturile sunt afisate FARA virgula. Ultimele 2 cifre sunt banii. "
        "Exemple: 549=5.49 lei, 1099=10.99 lei, 2949=29.49 lei, 99=0.99 lei.\n"
        "Extrage TOATE produsele cu preturile lor.\n"
        "Ignora: titluri de sectiune, date de valabilitate, 'LEI', 'LEI/KG', procente de discount.\n"
        f"FORMAT JSON: {{\"produse\": [{{\"nume\": \"...\", \"pret_nou\": 0.00, \"pret_vechi\": 0.00}}]}}\n"
        f"Daca nu exista pret vechi, pune 0.\n\n"
        f"TEXT PAGINA: {page_text}"
    )
    try:
        r = ollama.generate(
            model="llama3.2:3b",
            prompt=prompt,
            format="json",
            options={"temperature": 0.1}
        )
        return json.loads(r["response"]).get("produse", [])
    except Exception as e:
        print(f"    LLM error: {e}")
        return []


def run():
    if not INPUT_FILE.exists():
        print(f"Fisier negasit: {INPUT_FILE}")
        return

    print("Initializare EasyOCR...")
    reader = easyocr.Reader(['ro', 'en'], gpu=False)

    doc = fitz.open(str(INPUT_FILE))
    print(f"Auchan.pdf: {len(doc)} pagini\n")

    all_products = []
    captured_at = time.strftime("%Y-%m-%d %H:%M:%S")

    for i, page in enumerate(doc):
        page_text = page_to_text(reader, page)

        # Sari paginile goale sau doar cu header
        if len(page_text) < 30:
            print(f"  Pagina {i+1}: prea putin text, skip")
            continue

        print(f"  Pagina {i+1}: {len(page_text)} chars -> LLM...", end=" ", flush=True)
        start = time.time()

        products = llm_extract(page_text)

        for p in products:
            name = str(p.get("nume") or "").strip()
            pret_nou = p.get("pret_nou") or 0
            pret_vechi = p.get("pret_vechi") or 0

            if not name or len(name) < 3:
                continue
            try:
                pret_nou = round(float(str(pret_nou).replace(',', '.')), 2)
                pret_vechi = round(float(str(pret_vechi).replace(',', '.')), 2)
            except (ValueError, TypeError):
                continue
            if pret_nou < 0.5 or pret_nou > 500:
                continue
            discount = round(1 - pret_nou / pret_vechi, 2) if pret_vechi > pret_nou else 0.0

            all_products.append({
                "store": "Auchan",
                "raw_name": name,
                "price_new": pret_nou,
                "price_old": pret_vechi if pret_vechi > pret_nou else round(pret_nou * 1.2, 2),
                "discount": discount,
                "requires_card": False,
                "captured_at": captured_at,
            })

        print(f"{len(products)} produse ({round(time.time()-start, 1)}s)")

    doc.close()

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_products, f, indent=4, ensure_ascii=False)

    print(f"\nTotal: {len(all_products)} produse -> {OUTPUT_FILE}")


if __name__ == "__main__":
    run()
