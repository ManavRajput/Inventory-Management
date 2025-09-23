# from typing import Optional, Dict, Any, List
# from pydantic import BaseModel, Field


# class ProductUpsert(BaseModel):
#     sku: str
#     name: str
#     variety: Optional[str] = None
#     price: float
#     # 'attributes' is an optional dictionary for storing arbitrary product metadata,
#     # such as {"color": "red", "size": "XL"} or {"brand": "Acme", "weight": 1.2}
#     attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)


# class RestockIN(BaseModel):
#     sku: str
#     variety: Optional[str] = None
#     quantity: int
#     unit_price: Optional[float] = None
#     ref_id: Optional[str] = None
#     notes: Optional[str] = None


# class SaleOUT(BaseModel):
#     sku: str
#     variety: Optional[str] = None
#     quantity: int
#     sale_price: Optional[float] = None
#     ref_id: Optional[str] = None
#     notes: Optional[str] = None


# class StockResponse(BaseModel):
#     sku: str
#     quantity: int
#     available: bool


# class ProductCard(BaseModel):
#     sku: str
#     name: str
#     variety: Optional[str]
#     price: float
#     quantity: int
#     available: bool


# class SearchQuery(BaseModel):
#     q: str
#     variety: Optional[str] = None


# class SearchItem(ProductCard):
#     pass


# class VarietiesResponse(BaseModel):
#     name: str
#     varieties: List[str]
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field




class ProductUpsert(BaseModel):
    sku: str = Field(
        description="Merchant-chosen unique code per sellable variant (e.g., TSHIRT-BLK-M).",
        examples=["TSHIRT-BLK-M"],
    )
    name: str = Field(
        description="Human-readable product name as shown to customers.",
        examples=["Basic Cotton T-Shirt"],
    )
    variety: Optional[str] = Field(
        default=None,
        description="Optional variant label such as size/color/flavor. Keep consistent across the catalog.",
        examples=["M / Black"],
    )
    price: float = Field(
        description="Current selling price for this SKU/variety combination.",
        examples=[499.00],
    )
    # 'attributes' is an optional dictionary for storing arbitrary product metadata,
    # such as {"color": "red", "size": "XL"} or {"brand": "Acme", "weight": 1.2}
    attributes: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Arbitrary metadata such as brand, color, size, material, weight, etc.",
        examples=[{"brand": "Acme", "color": "Black", "size": "M", "material": "Cotton"}],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sku": "TSHIRT-BLK-M",
                    "name": "Basic Cotton T-Shirt",
                    "variety": "M / Black",
                    "price": 499.0,
                    "attributes": {"brand": "Acme", "color": "Black", "size": "M", "material": "Cotton"},
                }
            ]
        }
    }


class ProductUpsertBatch(BaseModel):
    items: List[ProductUpsert] = Field(
        description="List of products to upsert atomically by SKU.",
        examples=[[
            {"sku": "TSHIRT-BLK-M", "name": "Basic Cotton T-Shirt", "variety": "M / Black", "price": 499.0,
             "attributes": {"brand": "Acme", "color": "Black", "size": "M"}},
            {"sku": "TSHIRT-WHT-L", "name": "Basic Cotton T-Shirt", "variety": "L / White", "price": 479.0,
             "attributes": {"brand": "Acme", "color": "White", "size": "L"}}
        ]]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [
                        {"sku": "TSHIRT-BLK-M", "name": "Basic Cotton T-Shirt", "variety": "M / Black", "price": 499.0,
                         "attributes": {"brand": "Acme", "color": "Black", "size": "M"}},
                        {"sku": "TSHIRT-WHT-L", "name": "Basic Cotton T-Shirt", "variety": "L / White", "price": 479.0,
                         "attributes": {"brand": "Acme", "color": "White", "size": "L"}}
                    ]
                }
            ]
        }
    }

class RestockIN(BaseModel):
    sku: str = Field(
        description="SKU being restocked; must already exist via product upsert.",
        examples=["TSHIRT-BLK-M"],
    )
    variety: Optional[str] = Field(
        default=None,
        description="Optional variant label to target a specific product variant.",
        examples=["M / Black"],
    )
    quantity: int = Field(
        description="Positive integer units added to inventory.",
        examples=[50],
    )
    unit_price: Optional[float] = Field(
        default=None,
        description="Optional per-unit cost price for this restock batch (for COGS/analytics).",
        examples=[250.0],
    )
    ref_id: Optional[str] = Field(
        default=None,
        description="Optional external reference like supplier invoice, GRN, or PO number.",
        examples=["PO-2025-000123"],
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional free text for internal notes (e.g., damaged items returned).",
        examples=["Initial stock from supplier Phoenix Traders"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sku": "TSHIRT-BLK-M",
                    "variety": "M / Black",
                    "quantity": 50,
                    "unit_price": 250.0,
                    "ref_id": "PO-2025-000123",
                    "notes": "Initial stock from supplier Phoenix Traders",
                }
            ]
        }
    }


class SaleOUT(BaseModel):
    sku: str = Field(
        description="SKU being sold to end customer.",
        examples=["TSHIRT-BLK-M"],
    )
    variety: Optional[str] = Field(
        default=None,
        description="Optional variant to match the exact product variant being sold.",
        examples=["M / Black"],
    )
    quantity: int = Field(
        description="Positive integer units removed from inventory (sold).",
        examples=[2],
    )
    sale_price: Optional[float] = Field(
        default=None,
        description="Optional per-unit sale price recorded for analytics/receipts.",
        examples=[499.0],
    )
    ref_id: Optional[str] = Field(
        default=None,
        description="Optional order/checkout/payment reference from website or WhatsApp flow.",
        examples=["ORD-2025-009876"],
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional free text for internal audit (e.g., discount code used).",
        examples=["WhatsApp order, COD applied"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sku": "TSHIRT-BLK-M",
                    "variety": "M / Black",
                    "quantity": 2,
                    "sale_price": 499.0,
                    "ref_id": "ORD-2025-009876",
                    "notes": "WhatsApp order, COD applied",
                }
            ]
        }
    }

class BatchRestockIN(BaseModel):
    supplier: Optional[str] = Field(default=None, description="Supplier/vendor name", examples=["Phoenix Traders"])
    ref_id: Optional[str] = Field(default=None, description="Invoice/GRN/PO reference for this batch", examples=["PO-2025-000124"])
    notes: Optional[str] = Field(default=None, description="Batch-level notes", examples=["Opening stock for season sale"])
    items: List[RestockIN] = Field(description="List of restock items to add in one transaction", examples=[[
        {"sku": "TSHIRT-BLK-M", "variety": "M / Black", "quantity": 30, "unit_price": 250.0},
        {"sku": "TSHIRT-WHT-L", "variety": "L / White", "quantity": 20, "unit_price": 240.0}
    ]])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "supplier": "Phoenix Traders",
                    "ref_id": "PO-2025-000124",
                    "notes": "Opening stock for season sale",
                    "items": [
                        {"sku": "TSHIRT-BLK-M", "variety": "M / Black", "quantity": 30, "unit_price": 250.0},
                        {"sku": "TSHIRT-WHT-L", "variety": "L / White", "quantity": 20, "unit_price": 240.0}
                    ]
                }
            ]
        }
    }


class OrderItem(BaseModel):
    sku: str = Field(description="SKU sold", examples=["TSHIRT-BLK-M"])
    variety: Optional[str] = Field(default=None, description="Variant label", examples=["M / Black"])
    quantity: int = Field(description="Units sold", examples=[2])
    sale_price: Optional[float] = Field(default=None, description="Per-unit sale price", examples=[499.0])


class SaleOrderOUT(BaseModel):
    order_id: str = Field(description="External order id from web/WhatsApp", examples=["ORD-2025-009990"])
    channel: Optional[str] = Field(default="web", description="Sales channel (web/whatsapp/pos)", examples=["whatsapp"])
    notes: Optional[str] = Field(default=None, description="Order-level notes", examples=["COD, deliver today"])
    items: List[OrderItem] = Field(description="Items to sell atomically as one order", examples=[[
        {"sku": "TSHIRT-BLK-M", "variety": "M / Black", "quantity": 2, "sale_price": 499.0},
        {"sku": "TSHIRT-WHT-L", "variety": "L / White", "quantity": 1, "sale_price": 479.0}
    ]])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "order_id": "ORD-2025-009990",
                    "channel": "whatsapp",
                    "notes": "COD, deliver today",
                    "items": [
                        {"sku": "TSHIRT-BLK-M", "variety": "M / Black", "quantity": 2, "sale_price": 499.0},
                        {"sku": "TSHIRT-WHT-L", "variety": "L / White", "quantity": 1, "sale_price": 479.0}
                    ]
                }
            ]
        }
    }


class StockResponse(BaseModel):
    sku: str = Field(
        description="SKU that the stock summary refers to.",
        examples=["TSHIRT-BLK-M"],
    )
    quantity: int = Field(
        description="Current computed quantity (IN - OUT ± adjustments).",
        examples=[48],
    )
    available: bool = Field(
        description="True if quantity > 0; used to quickly answer availability queries.",
        examples=[True],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"sku": "TSHIRT-BLK-M", "quantity": 48, "available": True}
            ]
        }
    }


class ProductCard(BaseModel):
    sku: str = Field(
        description="SKU of the product card displayed to users.",
        examples=["TSHIRT-BLK-M"],
    )
    name: str = Field(
        description="Product name for display.",
        examples=["Basic Cotton T-Shirt"],
    )
    variety: Optional[str] = Field(
        default=None,
        description="Variant label if applicable (e.g., size/color).",
        examples=["M / Black"],
    )
    price: float = Field(
        description="Current selling price from the catalog (not historical).",
        examples=[499.0],
    )
    quantity: int = Field(
        description="Live stock number computed from the ledger.",
        examples=[48],
    )
    available: bool = Field(
        description="True if in stock (>0).",
        examples=[True],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sku": "TSHIRT-BLK-M",
                    "name": "Basic Cotton T-Shirt",
                    "variety": "M / Black",
                    "price": 499.0,
                    "quantity": 48,
                    "available": True,
                }
            ]
        }
    }


class SearchQuery(BaseModel):
    q: str = Field(
        description="Search term matched against name and SKU (case-insensitive).",
        examples=["tshirt black"],
    )
    variety: Optional[str] = Field(
        default=None,
        description="Optional filter to restrict results to a specific variant.",
        examples=["M / Black"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"q": "tshirt black", "variety": "M / Black"},
                {"q": "cotton", "variety": None},
            ]
        }
    }


class SearchItem(ProductCard):
    # Inherits fields and examples from ProductCard
    pass


class VarietiesResponse(BaseModel):
    name: str = Field(
        description="The product name used to search for distinct varieties.",
        examples=["Basic Cotton T-Shirt"],
    )
    varieties: List[str] = Field(
        description="List of unique variant labels available for the given product name.",
        examples=[["S / Black", "M / Black", "L / Black", "M / White"]],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Basic Cotton T-Shirt",
                    "varieties": ["S / Black", "M / Black", "L / Black", "M / White"],
                }
            ]
        }
    }
