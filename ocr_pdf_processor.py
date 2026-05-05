import fitz
import easyocr
import json
import re
import time
from pathlib import Path

INPUT_DIR  = Path("inputs")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

PRICE_RE = re.compile(r'\b\d{1,4}[.,]\d{2}\b')
CARD_RE  = re.compile(r'card|club|connect|plus', re.IGNORECASE)
DATE_RE  = re.compile(r'\b(0?[1-9]|[12]\d|3[01])[.,](0?[1-9]|1[0-2])\b')

NAME_BLACKLIST = {
    "disponibil", "oferta", "oferte", "promotii", "promoții", "promotie",
    "pagina", "pret", "preț", "lei/kg", "lei", "nr.", "valabilitate",
    "carrefour", "kaufland", "auchan", "penny", "profi", "lidl", "mega image",
    "prin act for good", "act for good", "ghiveci",
    "stocului", "limita", "limitat", "limitat stocului",
    "diverse sortimente", "diverse", "sortimente",
    "card", "lei/buc.", "lei/buc", "lei/2", "lei/1", "buc.",
    "pret pachet", "preț pachet", "per pachet", "pachet:",
    "prețuri mici, mâncare bună", "prețuri mici", "mâncare bună",
    "classic", "inferioare", "doar", "stoc", "all",
    "porții:", "porții", "portii", "portii:",
    "connect", "buc", "max.", "snow", "periș",
    "preț pachet:", "pachet:", "pachet", "laptellapte",
    "(penny", "spornig",
}

NOISE_NAME_RE = re.compile(
    r'^-?\d+\s*%'
    r'|^-\d+$'
    r'|\blei\b'
    r'|^\d+[a-z]{0,3}$'
    r'|^\d+x'
    r'|^[^a-zA-ZăâîșțĂÂÎȘȚ]+$'
    r'|^\(.*\)$'
    r'|^bro$',
    re.IGNORECASE
)


def clean_price(text: str) -> float:
    text = text.replace(' ', '').replace(',', '.')
    found = re.findall(r'\d+\.\d{2}', text)
    return float(found[0]) if found else 0.0


STORE_KEYWORDS = {
    "auchan":    "Auchan",
    "kaufland":  "Kaufland",
    "penny":     "Penny",
    "profi":     "Profi",
    "carrefour": "Carrefour",
    "mega image":"Mega Image",
    "mega_image":"Mega Image",
    "megaimage": "Mega Image",
    "lidl":      "Lidl",
}

def store_from_filename(path: Path) -> str:
    name = path.stem.lower()
    for keyword, store in STORE_KEYWORDS.items():
        if keyword in name:
            return store
    return path.stem.split('-')[0].split('_')[0].strip().capitalize()


def blocks_from_ocr(reader, img_data: bytes) -> list[dict]:
    results = reader.readtext(img_data)
    blocks = []
    for bbox, text, conf in results:
        if conf < 0.3 or not text.strip():
            continue
        x = (bbox[0][0] + bbox[2][0]) / 2
        y = (bbox[0][1] + bbox[2][1]) / 2
        blocks.append({"x": x, "y": y, "text": text.strip()})
    return blocks


def blocks_from_pdf_page(page) -> list[dict]:
    words = page.get_text("words")
    blocks = []
    for w in words:
        if not w[4].strip():
            continue
        x = (w[0] + w[2]) / 2
        y = (w[1] + w[3]) / 2
        blocks.append({"x": x, "y": y, "text": w[4].strip()})
    return blocks


def extract_products(blocks: list[dict], store: str) -> list[dict]:
    price_blocks = []
    for b in blocks:
        m = PRICE_RE.search(b["text"])
        if not m:
            continue
        candidate = m.group().replace(',', '.')
        if DATE_RE.fullmatch(candidate):
            continue
        val = clean_price(candidate)
        if val < 0.99 or val > 9999:
            continue
        price_blocks.append({**b, "price": val})

    products = []
    used = set()

    for i, pb in enumerate(price_blocks):
        if i in used:
            continue

        py, px, price_new = pb["y"], pb["x"], pb["price"]

        # Cauta un al doilea pret in apropiere (pret vechi)
        price_old = 0.0
        for j, pb2 in enumerate(price_blocks):
            if j == i or j in used:
                continue
            if abs(pb2["y"] - py) < 60 and abs(pb2["x"] - px) < 200:
                price_old = max(price_new, pb2["price"])
                price_new = min(price_new, pb2["price"])
                used.add(j)
                break

        def valid_name(b):
            t = b["text"]
            return (
                not PRICE_RE.search(t)
                and not DATE_RE.search(t)
                and len(t) > 2
                and t.lower().strip() not in NAME_BLACKLIST
                and not NOISE_NAME_RE.search(t)
            )

        vertical_range = 250

        # Cauta numele: text non-pret deasupra pretului, in aceeasi zona orizontala
        name_candidates = [
            b for b in blocks
            if b["y"] < py
            and (py - b["y"]) < vertical_range
            and abs(b["x"] - px) < 350
            and valid_name(b)
        ]

        # Fallback: text la acelasi nivel, in stanga
        if not name_candidates:
            name_candidates = [
                b for b in blocks
                if abs(b["y"] - py) < 25
                and b["x"] < px
                and valid_name(b)
            ]

        if not name_candidates:
            continue

        # Cel mai apropiat bloc de text fata de pret
        name_block = min(name_candidates, key=lambda b: ((b["x"] - px)**2 + (b["y"] - py)**2) ** 0.5)
        raw_name = name_block["text"]

        if raw_name.lower().strip() in NAME_BLACKLIST or len(raw_name.strip()) < 3 or NOISE_NAME_RE.search(raw_name):
            continue

        nearby_text = " ".join(
            b["text"] for b in blocks
            if abs(b["y"] - py) < 80 and abs(b["x"] - px) < 350
        )
        requires_card = bool(CARD_RE.search(nearby_text))

        discount = round(1 - price_new / price_old, 2) if price_old > price_new else 0.0

        products.append({
            "store": store,
            "raw_name": raw_name,
            "price_new": price_new,
            "price_old": price_old if price_old > price_new else round(price_new * 1.2, 2),
            "discount": discount,
            "requires_card": requires_card,
            "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        used.add(i)

    return products


def process_pdf(path: Path, reader, store: str) -> list[dict]:
    doc = fitz.open(str(path))
    products = []
    for page in doc:
        text = page.get_text().strip()
        has_prices_in_text = bool(PRICE_RE.search(text))
        use_ocr = len(text) < 20 or not has_prices_in_text
        if use_ocr:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            blocks = blocks_from_ocr(reader, pix.tobytes("png"))
        else:
            blocks = blocks_from_pdf_page(page)
        products.extend(extract_products(blocks, store))
    doc.close()
    return products


def process_image(path: Path, reader, store: str) -> list[dict]:
    blocks = blocks_from_ocr(reader, path.read_bytes())
    return extract_products(blocks, store)


def run():
    print("Initializare EasyOCR (ro + en)...")
    reader = easyocr.Reader(['ro', 'en'])

    pdf_files = list(INPUT_DIR.glob("*.pdf"))
    img_files = [f for f in INPUT_DIR.iterdir()
                 if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.bmp', '.webp')]
    all_files = pdf_files + img_files

    if not all_files:
        print(f"Niciun fisier gasit in '{INPUT_DIR}'.")
        return

    print(f"Gasit {len(all_files)} fisiere ({len(pdf_files)} PDF, {len(img_files)} imagini)\n")

    by_store: dict[str, list] = {}
    for path in all_files:
        store = store_from_filename(path)
        print(f"Procesare {path.name} [{store}]...", end=" ", flush=True)
        start = time.time()
        try:
            if path.suffix.lower() == '.pdf':
                products = process_pdf(path, reader, store)
            else:
                products = process_image(path, reader, store)
            by_store.setdefault(store.lower().replace(' ', '_'), []).extend(products)
            print(f"{len(products)} produse ({round(time.time() - start, 1)}s)")
        except Exception as e:

            print(f"Eroare: {e}")

    total = 0
    for store_slug, products in by_store.items():
        out_path = OUTPUT_DIR / f"ocr_{store_slug}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(products, f, indent=4, ensure_ascii=False)
        print(f"  {out_path.name}: {len(products)} produse")
        total += len(products)

    print(f"\nTotal: {total} produse in {len(by_store)} fisiere")


if __name__ == "__main__":
    run()
