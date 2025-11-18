import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any, Dict
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="MC HEROS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- Helpers ---------
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    d = {**doc}
    _id = d.pop("_id", None)
    if _id is not None:
        d["id"] = str(_id)
    # Convert nested ObjectIds if present
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
        if isinstance(v, list):
            d[k] = [str(x) if isinstance(x, ObjectId) else x for x in v]
        if isinstance(v, dict):
            d[k] = serialize_doc(v)
    return d

# --------- Schemas for API (separate from schemas.py viewer) ---------
class ProductOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float
    category: str
    image: Optional[str] = None

class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = Field(ge=1)

class OrderCreate(BaseModel):
    buyer_email: EmailStr
    buyer_name: str
    ign: Optional[str] = None
    items: List[OrderItem]
    note: Optional[str] = None

class OrderOut(BaseModel):
    id: str
    buyer_email: EmailStr
    buyer_name: str
    ign: Optional[str] = None
    items: List[OrderItem]
    total: float
    status: str

# --------- Seed Data ---------
DEFAULT_PRODUCTS = [
    {
        "name": "Diamond Sword",
        "description": "Sharp V ready! Deal massive damage.",
        "price": 12.99,
        "category": "Weapons",
        "image": "/items/diamond_sword.png",
    },
    {
        "name": "Enchanted Pickaxe",
        "description": "Efficiency V, Unbreaking III.",
        "price": 10.49,
        "category": "Tools",
        "image": "/items/enchanted_pickaxe.png",
    },
    {
        "name": "Netherite Armor Set",
        "description": "Full protection for endgame raiding.",
        "price": 39.99,
        "category": "Armor",
        "image": "/items/netherite_armor.png",
    },
    {
        "name": "VIP Rank (30 Days)",
        "description": "Perks: /fly, kits, queue skip.",
        "price": 14.99,
        "category": "Ranks",
        "image": "/items/vip_rank.png",
    },
]

def ensure_seed_products():
    if db is None:
        return
    count = db["product"].count_documents({})
    if count == 0:
        db["product"].insert_many(
            [
                {**p, "created_at": None, "updated_at": None} for p in DEFAULT_PRODUCTS
            ]
        )

# --------- Routes ---------
@app.get("/")
def read_root():
    return {"message": "MC HEROS Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Welcome to MC HEROS API"}

@app.get("/api/products", response_model=List[ProductOut])
def list_products():
    try:
        ensure_seed_products()
        docs = get_documents("product")
        return [ProductOut(**serialize_doc(d)) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/orders", response_model=OrderOut)
def create_order(order: OrderCreate):
    if not order.items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    total = sum(i.price * i.quantity for i in order.items)
    data = {
        "buyer_email": order.buyer_email,
        "buyer_name": order.buyer_name,
        "ign": order.ign,
        "items": [i.model_dump() for i in order.items],
        "total": round(total, 2),
        "status": "pending",
    }
    try:
        order_id = create_document("order", data)
        saved = db["order"].find_one({"_id": ObjectId(order_id)})
        s = serialize_doc(saved)
        return OrderOut(**s)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: str):
    try:
        doc = db["order"].find_one({"_id": ObjectId(order_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Order not found")
        s = serialize_doc(doc)
        return OrderOut(**s)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = (
                os.getenv("DATABASE_NAME") if os.getenv("DATABASE_NAME") else "❌ Not Set"
            )
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
