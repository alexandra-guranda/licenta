from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import os
import re
import random
import ollama
from thefuzz import fuzz
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = "outputs/refined_llama/REFINED_WEB_DATA.json"
AI_MODEL      = "llama3.2:3b"
TABLE         = "products"

app = FastAPI(title="SmartPrice API", version="1.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("assets"):
    app.mount("/static/assets", StaticFiles(directory="assets"), name="static_assets")
if os.path.exists("outputs"):
    app.mount("/static", StaticFiles(directory="outputs"), name="static")

_db: list[dict] = []
_stores: list[dict] = []
_categories: list[str] = []
_source: str = "none"

def _supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Credentiale Supabase lipsa in .env")
    from supabase import create_client
    return create_client(url, key)

def _paginate(client, table: str) -> list[dict]:
    all_rows, page, page_size = [], 0, 1000
    while True:
        resp = client.table(table).select("*").range(page * page_size, (page + 1) * page_size - 1).execute()
        rows = resp.data or []
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        page += 1
    return all_rows

IMAGES_FIXED_DIR = Path("outputs/fixed_images_llama")
STORE_SLUG_MAP = {
    "auchan": "auchan", "kaufland": "kaufland", "penny": "penny",
    "profi": "profi", "carrefour": "carrefour",
    "mega image": "mega_image", "mega_image": "mega_image", "lidl": "lidl",
}

_images_index: dict[str, set[str]] = {}

def _build_images_index() -> None:
    if not IMAGES_FIXED_DIR.exists():
        return
    for folder in IMAGES_FIXED_DIR.iterdir():
        if folder.is_dir():
            _images_index[folder.name] = {p.stem for p in folder.glob("*.jpg")}

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")

def _patch_image_local(products: list[dict]) -> None:
    if not _images_index:
        _build_images_index()
    for p in products:
        store_folder = STORE_SLUG_MAP.get((p.get("store") or "").lower().strip())
        if not store_folder:
            p["image_local"] = None
            continue
        existing = p.get("image_local")
        if existing:
            fname = existing.rsplit("/", 1)[-1]
            stem = fname.rsplit(".", 1)[0]
            filenames = _images_index.get(store_folder, set())
            if fname in filenames or stem in filenames:
                continue
        p["image_local"] = None

def _load_from_supabase() -> tuple[list[dict], list[dict]]:
    client = _supabase_client()
    products = _paginate(client, "products")
    stores   = _paginate(client, "stores")
    return products, stores

def _load_from_json() -> list[dict]:
    if not os.path.exists(DATABASE_PATH):
        raise RuntimeError(f"Fisier local lipsa: {DATABASE_PATH}")
    with open(DATABASE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    for i, item in enumerate(data):
        item["id"] = i
    return data

def _init_db(data: list[dict], stores: list[dict] = None) -> None:
    global _db, _stores, _categories
    _db = data
    _stores = stores or []
    _categories = sorted({p["category"] for p in _db if p.get("category")})

@app.on_event("startup")
def startup():
    global _source
    _build_images_index()
    try:
        products, stores = _load_from_supabase()
        _patch_image_local(products)
        _init_db(products, stores)
        _source = "supabase"
        print(f"[DB] Incarcat din Supabase: {len(_db)} produse, {len(_stores)} magazine")
    except Exception as e:
        print(f"[DB] Supabase indisponibil ({e}), folosesc JSON local...")
        try:
            data = _load_from_json()
            _patch_image_local(data)
            _init_db(data)
            _source = "local"
            print(f"[DB] Incarcat din JSON local: {len(_db)} produse")
        except Exception as e2:
            print(f"[DB] EROARE CRITICA: {e2}")

def search_products(q: str = None, category: str = None, store: str = None) -> list[dict]:
    results = _db
    if category:
        results = [p for p in results if p.get("category") == category]
    if store:
        results = [p for p in results if p.get("store", "").lower() == store.lower()]
    if q:
        q_lower = q.lower()
        scored = []
        for p in results:
            name = p.get("name", "").lower()
            if q_lower in name:
                scored.append((100, p))
            else:
                score = fuzz.partial_ratio(q_lower, name)
                if score >= 65:
                    scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [p for _, p in scored]
    return results

class ChatRequest(BaseModel):
    message: str

class SubscribeRequest(BaseModel):
    email: str

@app.get("/")
def root():
    return {"status": "online", "total_products": len(_db), "source": _source}

@app.post("/reload")
def reload_db():
    global _source
    try:
        products, stores = _load_from_supabase()
        _patch_image_local(products)
        _init_db(products, stores)
        _source = "supabase"
    except Exception:
        data = _load_from_json()
        _patch_image_local(data)
        _init_db(data)
        _source = "local"
    return {"status": "reloaded", "total_products": len(_db), "source": _source}

@app.get("/stores")
def get_stores():
    if _stores:
        return {"stores": _stores}
    names = sorted({p["store"] for p in _db if p.get("store")})
    return {"stores": [{"name": n} for n in names]}

@app.get("/products")
def get_products(q: str = None, category: str = None, store: str = None,
                 skip: int = 0, limit: int = 200):
    results = search_products(q, category, store)
    if not q:
        results = random.sample(results, len(results))
    return {"count": len(results), "products": results[skip: skip + limit]}

@app.get("/products/{product_id}")
def get_product(product_id: int):
    matches = [p for p in _db if p.get("id") == product_id]
    if not matches:
        raise HTTPException(status_code=404, detail="Produs negăsit")
    return matches[0]

@app.get("/top-deals")
def get_top_deals(limit: int = 15):
    deals = [p for p in _db if (p.get("discount") or 0) >= 0.35]
    deals = sorted(deals, key=lambda x: x.get("discount") or 0, reverse=True)
    return deals[:limit]

@app.get("/categories")
def get_categories():
    counts: dict[str, int] = {}
    for p in _db:
        cat = p.get("category")
        if cat:
            counts[cat] = counts.get(cat, 0) + 1
    result = [{"name": c, "count": counts.get(c, 0)} for c in _categories]
    return {"categories": result}

@app.get("/compare")
def compare_product(name: str):

    name_lower = name.lower()
    scored = []
    for p in _db:
        score = fuzz.token_set_ratio(name_lower, p.get("name", "").lower())
        if score >= 70:
            scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    by_store: dict = {}
    for score, p in scored[:60]:
        store = p.get("store")
        if store not in by_store:
            by_store[store] = p
    results = sorted(by_store.values(), key=lambda x: x.get("price_new") or 9999)
    return {"results": results, "count": len(results)}

SUBSCRIBERS_PATH = "outputs/subscribers.json"

@app.post("/subscribe")
def subscribe(req: SubscribeRequest):
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Email invalid")
    subscribers = []
    if os.path.exists(SUBSCRIBERS_PATH):
        with open(SUBSCRIBERS_PATH, "r", encoding="utf-8") as f:
            subscribers = json.load(f)
    if email not in subscribers:
        subscribers.append(email)
        with open(SUBSCRIBERS_PATH, "w", encoding="utf-8") as f:
            json.dump(subscribers, f, ensure_ascii=False, indent=2)
    return {"status": "ok", "email": email}

@app.post("/ai/chat")
async def ai_chat(request: ChatRequest):
    query_words = [w for w in request.message.lower().split() if len(w) > 2]

    relevant = []
    for p in _db:
        name = p.get("name", "").lower()
        if any(w in name for w in query_words):
            relevant.append(p)
    relevant = sorted(relevant, key=lambda x: x.get("discount") or 0, reverse=True)[:8]

    if relevant:
        context = "Oferte găsite în baza de date:\n" + "".join(
            f"- {p['name']} la {p['store']}: {p['price_new']} lei"
            f" (reducere {int((p.get('discount') or 0) * 100)}%)\n"
            for p in relevant
        )
    else:
        context = "Nu am găsit produse specifice pentru această căutare."

    system_prompt = (
        "Ești 'SmartPrice Bot', un asistent care ajută utilizatorii să găsească "
        "cele mai bune oferte din supermarketurile din România.\n"
        "Folosește CONTEXTUL de mai jos dacă e disponibil, citează produsele găsite, drăguț și formal. "
        "fii atent să răspunzi exact la subiect și răspunde în română"
        "Daca se cere carne, utilizatorul se referă la produse din carne și mezeluri, nu la hrană de animale.Doar daca este mentionat un animal, cauti la casa si diverse, hrană pentru animale.\n\n"
        f"CONTEXT:\n{context}"
    )

    try:
        response = ollama.generate(model=AI_MODEL, system=system_prompt, prompt=request.message)
        return {"reply": response["response"]}
    except Exception:
        return {"reply": "Momentan nu pot accesa AI-ul. Încearcă căutarea manuală!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
