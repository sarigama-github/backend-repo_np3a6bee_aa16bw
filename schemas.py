"""
Database Schemas for MC HEROS

Each Pydantic model corresponds to a MongoDB collection (lowercased class name).
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

class Product(BaseModel):
    name: str = Field(..., description="Item name")
    description: Optional[str] = Field(None, description="Item description")
    price: float = Field(..., ge=0, description="Price in USD")
    category: str = Field(..., description="Category e.g., Weapons, Tools, Ranks")
    image: Optional[str] = Field(None, description="Public image path")

class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int = Field(1, ge=1)

class Order(BaseModel):
    buyer_email: EmailStr
    buyer_name: str
    ign: Optional[str] = None
    items: List[OrderItem]
    total: float
    status: str = Field("pending")

class PageContent(BaseModel):
    key: str = Field(..., description="page key e.g., tos, rules, privacy")
    title: str
    content: str
