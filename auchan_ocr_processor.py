from pathlib import Path
from ocr_base import init_reader, process_pdf_with_llm

STORE      = "Auchan"
INPUT_FILE = Path("inputs/Auchan.pdf")
OUTPUT     = Path("outputs/ocr_llama_auchan.json")

STORE_HINT = (
    "IMPORTANT: Preturile sunt afisate FARA virgula — ultimele 2 cifre sunt banii. "
    "Exemple: 549=5.49 lei, 1099=10.99 lei, 2949=29.49 lei, 99=0.99 lei. "
    "Catalogul contine promotii saptamanale cu pret cu card si fara card."
)

EXTRA_SKIP = {"fără os", "tocată", "bun", "flei", "igp", "salutl"}
EXTRA_NOISE_RE = r"|^[A-ZĂÂÎȘȚ]{1,4}$"

def run():
    if not INPUT_FILE.exists():
        print(f"Fisier negasit: {INPUT_FILE}")
        return

    reader = init_reader()
    products = process_pdf_with_llm(INPUT_FILE, STORE, reader, OUTPUT,
                                    store_hint=STORE_HINT,
                                    extra_skip=EXTRA_SKIP, extra_noise_re=EXTRA_NOISE_RE)
    print(f"\nTotal: {len(products)} produse -> {OUTPUT}")

if __name__ == "__main__":
    run()
