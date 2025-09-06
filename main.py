import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

# --- SQLAlchemy Database Setup ---
from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, func
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

DATABASE_URL = "sqlite:///./warehouse.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# --------------------
# 1. Pydantic Models (for API requests/responses)
# --------------------

class AddProductRequest(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    quantity: int = Field(0, ge=0)
    location_id: Optional[str] = None

class InventoryItem(BaseModel):
    sku: str
    name: str
    quantity: int
    location_id: Optional[str]

    class Config:
        from_attributes = True

class CreateOrderRequest(BaseModel):
    items: Dict[str, int]

class Order(BaseModel):
    id: str
    items: Dict[str, int]
    picked_items: Dict[str, int]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class UpdateProductRequest(BaseModel):
    quantity: int = Field(..., ge=0)
    location_id: Optional[str] = None

class PickItemRequest(BaseModel):
    sku: str
    quantity: int = Field(..., ge=1)


# --------------------
# 2. SQLAlchemy Models (for Database Tables)
# --------------------

class DBInventoryItem(Base):
    __tablename__ = "inventory"
    sku = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    quantity = Column(Integer, default=0)
    location_id = Column(String, nullable=True)

class DBOrder(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, index=True)
    items = Column(JSON)
    picked_items = Column(JSON)
    status = Column(String, default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_initial_data(db: Session):
    initial_inventory = [
        DBInventoryItem(sku="SKU001", name="Wireless Mouse", quantity=150, location_id="IL1-A-01"),
        DBInventoryItem(sku="SKU002", name="Mechanical Keyboard", quantity=80, location_id="IL1-A-02"),
        DBInventoryItem(sku="SKU003", name="USB-C Cable", quantity=300, location_id="IL2-D-01"),
        DBInventoryItem(sku="SKU004", name="Monitor Stand", quantity=50, location_id="IL10-D-03"),
        DBInventoryItem(sku="SKU005", name="Laptop Sleeve", quantity=250, location_id="IL4-E-04"),
    ]
    db.add_all(initial_inventory)
    db.commit()
        
# --------------------
# 3. FastAPI Application
# --------------------

app = FastAPI(
    title="Warehouse Management API",
    description="Backend with persistent SQLite database."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    if db.query(DBInventoryItem).count() == 0:
        seed_initial_data(db)
    db.close()

# --------------------
# 4. API Endpoints
# --------------------

@app.get("/api/health")
def get_health_status():
    return {"status": "ok"}

@app.get("/api/dashboard-stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_skus = db.query(DBInventoryItem).count()
    items_in_stock = db.query(func.sum(DBInventoryItem.quantity)).scalar() or 0
    total_orders = db.query(DBOrder).count()
    pending_orders = db.query(DBOrder).filter(DBOrder.status != "Completed").count()
    return {
        "total_skus": total_skus, "items_in_stock": items_in_stock,
        "total_orders": total_orders, "pending_orders": pending_orders,
    }

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(db: Session = Depends(get_db)):
    return db.query(DBInventoryItem).all()

@app.get("/api/orders", response_model=List[Order])
def get_orders(db: Session = Depends(get_db)):
    return db.query(DBOrder).order_by(DBOrder.created_at.desc()).all()

@app.post("/api/products", status_code=status.HTTP_201_CREATED, response_model=InventoryItem)
def add_product(product: AddProductRequest, db: Session = Depends(get_db)):
    db_item = db.query(DBInventoryItem).filter(DBInventoryItem.sku == product.sku).first()
    if db_item:
        raise HTTPException(status_code=409, detail="Product SKU already exists.")
    
    new_item = DBInventoryItem(
        sku=product.sku, 
        name=product.name, 
        quantity=product.quantity, 
        location_id=product.location_id
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.put("/api/products/{sku}", response_model=InventoryItem)
def update_product(sku: str, item_data: UpdateProductRequest, db: Session = Depends(get_db)):
    db_item = db.query(DBInventoryItem).filter(DBInventoryItem.sku == sku).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Product not found")
    
    db_item.quantity = item_data.quantity
    db_item.location_id = item_data.location_id
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/api/products/{sku}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(sku: str, db: Session = Depends(get_db)):
    db_item = db.query(DBInventoryItem).filter(DBInventoryItem.sku == sku).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_item)
    db.commit()

@app.post("/api/orders", status_code=status.HTTP_201_CREATED, response_model=Order)
def create_order(order_request: CreateOrderRequest, db: Session = Depends(get_db)):
    for sku in order_request.items:
        if not db.query(DBInventoryItem).filter(DBInventoryItem.sku == sku).first():
            raise HTTPException(status_code=404, detail=f"Product SKU '{sku}' not found.")

    new_order = DBOrder(id=str(uuid.uuid4()), items=order_request.items, picked_items={})
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

@app.delete("/api/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: str, db: Session = Depends(get_db)):
    db_order = db.query(DBOrder).filter(DBOrder.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found.")
    db.delete(db_order)
    db.commit()

@app.put("/api/orders/{order_id}/pick")
def pick_item(order_id: str, pick_data: PickItemRequest, db: Session = Depends(get_db)):
    db_order = db.query(DBOrder).filter(DBOrder.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    db_item = db.query(DBInventoryItem).filter(DBInventoryItem.sku == pick_data.sku).first()
    if not db_item or db_item.quantity < pick_data.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock.")

    db_item.quantity -= pick_data.quantity
    
    new_picked_items = db_order.picked_items.copy()
    new_picked_items[pick_data.sku] = new_picked_items.get(pick_data.sku, 0) + pick_data.quantity
    db_order.picked_items = new_picked_items

    completed = all(new_picked_items.get(sku, 0) >= qty for sku, qty in db_order.items.items())
    if completed:
        db_order.status = "Completed"
    elif any(new_picked_items.get(sku, 0) > 0 for sku in db_order.items):
        db_order.status = "Partial"
    
    db.commit()
    return {"message": "Item picked successfully", "order_status": db_order.status}

# --------------------
# 5. Server Runner
# --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

