from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import os
import random
import ollama

DATABASE_PATH = "outputs/refined/REFINED_WEB_DATA.json"
AI_MODEL = "llama3.2:3b"

app = FastAPI(title="SmartPrice API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("outputs"):
    app.mount("/static", StaticFiles(directory="outputs"), name="static")

_db: list[dict] = []
_categories: list[str] = []


@app.on_event("startup")
def startup():
    global _db, _categories
    if os.path.exists(DATABASE_PATH):
        with open(DATABASE_PATH, "r", encoding="utf-8") as f:
            _db = json.load(f)
        for i, item in enumerate(_db):
            item["id"] = i
        _categories = sorted({p["category"] for p in _db if p.get("category")})


def search_products(q: str = None, category: str = None, store: str = None) -> list[dict]:
    results = _db
    if q:
        q_lower = q.lower()
        results = [p for p in results if q_lower in p.get("name", "").lower()]
    if category:
        results = [p for p in results if p.get("category") == category]
    if store:
        results = [p for p in results if p.get("store", "").lower() == store.lower()]
    return results


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {"status": "online", "total_products": len(_db)}


@app.get("/products")
def get_products(q: str = None, category: str = None, store: str = None,
                 skip: int = 0, limit: int = 50):
    results = search_products(q, category, store)
    if not q:
        results = random.sample(results, len(results))
    return {"count": len(results), "products": results[skip: skip + limit]}


@app.get("/products/{product_id}")
def get_product(product_id: int):
    if product_id < 0 or product_id >= len(_db):
        raise HTTPException(status_code=404, detail="Produs negăsit")
    return _db[product_id]


@app.get("/top-deals")
def get_top_deals(limit: int = 15):
    deals = [p for p in _db if (p.get("discount") or 0) >= 0.35]
    deals = sorted(deals, key=lambda x: x.get("discount") or 0, reverse=True)
    return deals[:limit]


@app.get("/categories")
def get_categories():
    return {"categories": _categories}


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
        "Folosește CONTEXTUL de mai jos dacă e disponibil, citează produsele găsite, "
        "fii scurt și răspunde în română.\n\n"
        f"CONTEXT:\n{context}"
    )

    try:
        response = ollama.generate(model=AI_MODEL, system=system_prompt, prompt=request.message)
        return {"reply": response["response"]}
    except Exception as e:
        return {"reply": "Momentan nu pot accesa AI-ul. Încearcă căutarea manuală! 🛠️"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
