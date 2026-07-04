import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
DB_PATH      = Path("outputs/refined_llama/REFINED_WEB_DATA.json")
BATCH_SIZE   = 500

LOGOS_DIR    = Path("assets/logos")
LOGO_BUCKET  = "logos"

STORES = [
    {"id": 1, "name": "Auchan",     "file": "auchan.png"},
    {"id": 2, "name": "Kaufland",   "file": "kaufland.png"},
    {"id": 3, "name": "Penny",      "file": "penny.png"},
    {"id": 4, "name": "Profi",      "file": "profi.png"},
    {"id": 5, "name": "Carrefour",  "file": "carrefour.png"},
    {"id": 6, "name": "Mega Image", "file": "mega_image.png"},
    {"id": 7, "name": "Lidl",       "file": "lidl.png"},
]

STORE_ID_MAP = {s["name"].lower(): s["id"] for s in STORES}
STORE_ID_MAP.update({
    "mega image": 6,
    "mega_image": 6,
})

def get_store_id(store_name: str) -> int | None:
    return STORE_ID_MAP.get((store_name or "").lower().strip())

def clean_product(product: dict, idx: int) -> dict:
    return {
        "id":           idx,
        "store_id":     get_store_id(product.get("store", "")),
        "store":        product.get("store") or "",
        "raw_name":     product.get("raw_name") or "",
        "name":         product.get("name") or "",
        "brand":        product.get("brand") or "Generic",
        "category":     product.get("category") or "Necategorizat",
        "price_new":    float(product["price_new"]) if product.get("price_new") is not None else None,
        "price_old":    float(product["price_old"]) if product.get("price_old") is not None else None,
        "discount":     float(product["discount"])  if product.get("discount")  is not None else 0.0,
        "image_url":    product.get("image_url"),
        "image_local":  product.get("image_local"),
        "requires_card": bool(product.get("requires_card", False)),
    }

def main():
    if not DB_PATH.exists():
        print(f"Fisier lipsa: {DB_PATH}. Ruleaza mai intai: python build_db.py")
        sys.exit(1)

    with open(DB_PATH, encoding="utf-8") as f:
        products = json.load(f)

    print(f"Produse de incarcat: {len(products)}")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("\n[1/2] Incarc magazinele si logo-urile...")
    client.table("products").delete().gte("id", 0).execute()
    client.table("stores").delete().gte("id", 0).execute()

    stores_rows = []
    for s in STORES:
        logo_url = None
        logo_path = LOGOS_DIR / s["file"]
        if logo_path.exists():
            dest = s["file"]
            with open(logo_path, "rb") as f:
                data = f.read()
            try:
                client.storage.from_(LOGO_BUCKET).remove([dest])
            except Exception:
                pass
            client.storage.from_(LOGO_BUCKET).upload(dest, data, {"content-type": "image/png"})
            logo_url = f"{SUPABASE_URL}/storage/v1/object/public/{LOGO_BUCKET}/{dest}"
            print(f"  Logo uploadat: {dest}")
        else:
            print(f"  [SKIP] Logo lipsa: {logo_path}")
        stores_rows.append({"id": s["id"], "name": s["name"], "logo": logo_url})

    client.table("stores").insert(stores_rows).execute()
    print(f"  {len(stores_rows)} magazine incarcate.")

    print("\n[2/2] Incarc produsele...")

    rows = [clean_product(p, i) for i, p in enumerate(products)]
    total = len(rows)

    fara_store = [r for r in rows if r["store_id"] is None]
    if fara_store:
        magazine_necunoscute = {r["store"] for r in fara_store}
        print(f"  Atentie: {len(fara_store)} produse cu magazin necunoscut: {magazine_necunoscute}")

    uploaded = 0
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        client.table("products").insert(batch).execute()
        uploaded += len(batch)
        print(f"  {uploaded}/{total} produse...", end="\r")

    print(f"\n  {total} produse incarcate.")
    print(f"\nGata! Supabase actualizat cu {len(STORES)} magazine si {total} produse.")

if __name__ == "__main__":
    main()
