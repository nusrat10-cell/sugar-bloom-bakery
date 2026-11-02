from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

app = FastAPI(title="Sugar Bloom Bakery - Product Management API")

# Pydantic Models for Product
class Product(BaseModel):
    id: int
    name: str = Field(..., min_string_length=1)
    description: str
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    category: str

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    stock: int
    category: str

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category: Optional[str] = None
# In-memory database initial mock data for Sugar Bloom Bakery
products_db = [
    {
        "id": 1,
        "name": "Chocolate Truffle Cake",
        "description": "Rich layered chocolate cake with creamy ganache.",
        "price": 25.00,
        "stock": 10,
        "category": "Cakes"
    },
    {
        "id": 2,
        "name": "Glazed Strawberry Pastry",
        "description": "Flaky puff pastry topped with fresh strawberries and glaze.",
        "price": 4.50,
        "stock": 25,
        "category": "Pastries"
    },
    {
        "id": 3,
        "name": "Artisanal Sourdough Bread",
        "description": "Freshly baked crunchy crust sourdough loaf.",
        "price": 6.00,
        "stock": 15,
        "category": "Breads"
    }
]

# Health check & Hello routes
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/api/hello")
def hello(name: str = "World") -> dict[str, str]:
    return {"message": f"Hello, {name}!"}


# --- PRODUCT CRUD ENDPOINTS ---

# 1. Read List (Get all products)
@app.get("/api/products", response_model=List[Product])
def get_products():
    return products_db

# 2. Read Single (Get product by ID)
@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: int):
    for product in products_db:
        if product["id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")

# 3. Create (Add a new bakery product)
@app.post("/api/products", response_model=Product, status_code=201)
def create_product(product_in: ProductCreate):
    new_id = max([p["id"] for p in products_db], default=0) + 1
    new_product = {
        "id": new_id,
        "name": product_in.name,
        "description": product_in.description,
        "price": product_in.price,
        "stock": product_in.stock,
        "category": product_in.category
    }
    products_db.append(new_product)
    return new_product

# 4. Update (Edit an existing product)
@app.put("/api/products/{product_id}", response_model=Product)
def update_product(product_id: int, product_in: ProductUpdate):
    for product in products_db:
        if product["id"] == product_id:
            if product_in.name is not None:
                product["name"] = product_in.name
            if product_in.description is not None:
                product["description"] = product_in.description
            if product_in.price is not None:
                product["price"] = product_in.price
            if product_in.stock is not None:
                product["stock"] = product_in.stock
            if product_in.category is not None:
                product["category"] = product_in.category
            return product
    raise HTTPException(status_code=404, detail="Product not found")

# 5. Delete (Remove a product)
@app.delete("/api/products/{product_id}")
def delete_product(product_id: int):
    for i, product in enumerate(products_db):
        if product["id"] == product_id:
            deleted = products_db.pop(i)
            return {"message": "Product deleted successfully", "product": deleted}
    raise HTTPException(status_code=404, detail="Product not found")


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIR.is_dir():
    app.frontend("/", directory=FRONTEND_DIR)