from pydantic import BaseModel, Field


class Category(BaseModel):
    category_id: int
    name: str
    description: str | None = None


class Customer(BaseModel):
    customer_id: int
    name: str
    phone: str | None = None
    email: str | None = None
    city: str | None = None


class Product(BaseModel):
    product_id: int
    name: str
    category_id: int
    price_brl: float = Field(ge=0)
    description: str | None = None
    stock_quantity: int = Field(default=0, ge=0)
    status: str = "active"
    specs: str | None = None
    created_at: str | None = None


class Order(BaseModel):
    order_id: int
    customer_id: int
    order_date: str | None = None
    status: str
    total_brl: float | None = None
    payment_method: str | None = None
    tracking_code: str | None = None
    estimated_delivery: str | None = None
    notes: str | None = None


class OrderItem(BaseModel):
    order_id: int
    product_id: int
    quantity: int = Field(ge=1)


class Promotion(BaseModel):
    promotion_id: int
    product_id: int
    discount_percent: float = Field(ge=0, le=100)
    description: str | None = None
    is_active: bool = False
