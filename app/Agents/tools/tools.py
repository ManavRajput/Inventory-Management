# tools.py
from langchain_core.tools import tool
from typing import Optional
from app.DB.services.inventory_service import InventoryService
from app.DB.Sql.db_manager import AsyncDBManager
from app.DB.models.schema import (
    StockResponse, ProductCard, VarietiesResponse
)
from langchain_core.tools import tool
from typing import Optional, List, Dict, Any
import uuid


db = AsyncDBManager()
service = InventoryService(db)

# --- Tools ---

@tool
async def get_price(sku: str, variety: Optional[str] = None) -> dict:
    """Get the price of a product by SKU and optional variety."""
    price = await service.get_price(sku, variety)
    if price is None:
        return {"error": "Not found"}
    return {"sku": sku, "variety": variety, "price": price}

@tool
async def get_stock(sku: str, variety: Optional[str] = None) -> StockResponse:
    """Get stock info for a product by SKU and optional variety."""
    data = await service.get_stock(sku, variety)
    return StockResponse(**data)

@tool
async def get_card(sku: str, variety: Optional[str] = None) -> ProductCard:
    """Get a product card by SKU and optional variety."""
    card = await service.product_card(sku, variety)
    if not card:
        return {"error": "Not found"}
    return ProductCard(**card)

@tool
async def varieties(name: str) -> VarietiesResponse:
    """List varieties of a product given its name."""
    vs = await service.list_varieties(name)
    return VarietiesResponse(name=name, varieties=vs)

@tool
async def search(q: str, variety: Optional[str] = None) -> dict:
    """Search for products by query and optional variety."""
    items = await service.search(q, variety)
    return {"count": len(items), "items": items}


@tool
async def sell_single_item(
    sku: str, 
    variety: Optional[str] = None,
    quantity: int = 1,
    sale_price: Optional[float] = None,
    ref_id: Optional[str] = None,
    notes: Optional[str] = None
) -> dict:
    """Sell a single item - reduces inventory stock by specified quantity.
    
    Args:
        sku: Product SKU to sell
        variety: Product variety/variant (optional)
        quantity: Number of units to sell (default: 1)
        sale_price: Sale price per unit (optional, for analytics)
        ref_id: Reference ID like order number (optional)
        notes: Additional notes (optional)
    """
    try:
        await service.sell_out(
            sku=sku,
            variety=variety, 
            quantity=quantity,
            sale_price=sale_price,
            ref_id=ref_id or f"SALE-{uuid.uuid4().hex[:8].upper()}",
            notes=notes
        )
        
        return {
            "status": "success",
            "message": f"✅ Sold {quantity} x {sku} ({variety or 'default'})",
            "sku": sku,
            "variety": variety,
            "quantity": quantity,
            "sale_price": sale_price,
            "ref_id": ref_id
        }
        
    except ValueError as e:
        error_msg = str(e)
        if "insufficient stock" in error_msg.lower():
            return {
                "status": "error",
                "error": "insufficient_stock", 
                "message": f"❌ Not enough stock for {sku}. {error_msg}",
                "sku": sku,
                "requested": quantity
            }
        else:
            return {
                "status": "error",
                "error": "sale_failed",
                "message": f"❌ Sale failed: {error_msg}",
                "sku": sku
            }
    
    except Exception as e:
        return {
            "status": "error", 
            "error": "system_error",
            "message": f"❌ System error: {str(e)}",
            "sku": sku
        }


@tool 
async def sell_multiple_items(
    order_id: str,
    items: List[Dict[str, Any]],
    channel: Optional[str] = "chatbot",
    notes: Optional[str] = None
) -> dict:
    """Sell multiple items in one transaction - all items must be available or none are sold.
    
    Args:
        order_id: Unique order identifier
        items: List of items to sell, each containing: sku, variety?, quantity, sale_price?
        channel: Sales channel (default: "chatbot")
        notes: Order-level notes (optional)
        
    Example items format:
    [
        {"sku": "TSHIRT-BLK-M", "variety": "M / Black", "quantity": 2, "sale_price": 499.0},
        {"sku": "TSHIRT-WHT-L", "variety": "L / White", "quantity": 1, "sale_price": 479.0}
    ]
    """
    try:
        await service.sell_order(
            order_id=order_id,
            channel=channel,
            notes=notes,
            items=items
        )
        
        total_items = sum(item.get("quantity", 0) for item in items)
        total_value = sum(
            item.get("quantity", 0) * item.get("sale_price", 0) 
            for item in items 
            if item.get("sale_price")
        )
        
        return {
            "status": "success",
            "message": f"✅ Order {order_id} completed successfully",
            "order_id": order_id,
            "total_items": total_items,
            "total_value": total_value if total_value > 0 else None,
            "items": items,
            "channel": channel
        }
        
    except ValueError as e:
        error_msg = str(e)
        
        # Handle shortage errors (contains details about which items are short)
        if "shortages" in error_msg.lower() or isinstance(e.args[0], dict):
            try:
                error_data = e.args[0] if isinstance(e.args[0], dict) else {"error": error_msg}
                shortages = error_data.get("shortages", [])
                
                shortage_details = []
                for shortage in shortages:
                    shortage_details.append({
                        "sku": shortage.get("sku"),
                        "variety": shortage.get("variety"), 
                        "requested": shortage.get("requested"),
                        "available": shortage.get("available")
                    })
                
                return {
                    "status": "error",
                    "error": "insufficient_stock",
                    "message": "❌ Insufficient stock for some items",
                    "order_id": order_id,
                    "shortages": shortage_details
                }
            except:
                pass
        
        return {
            "status": "error",
            "error": "order_failed", 
            "message": f"❌ Order failed: {error_msg}",
            "order_id": order_id
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": "system_error",
            "message": f"❌ System error: {str(e)}",
            "order_id": order_id
        }


@tool
async def compute_order_total(items: List[Dict[str, Any]]) -> dict:
    """Calculate total price for multiple items without selling them.
    
    Args:
        items: List of items with sku, variety?, quantity
        
    Example items format:
    [
        {"sku": "TSHIRT-BLK-M", "variety": "M / Black", "quantity": 2},
        {"sku": "TSHIRT-WHT-L", "variety": "L / White", "quantity": 1}
    ]
    """
    try:
        line_items = []
        grand_total = 0.0
        unavailable_items = []
        
        for item in items:
            sku = item.get("sku")
            variety = item.get("variety")
            quantity = item.get("quantity", 1)
            
            if not sku:
                continue
                
            # Get product card (price + availability)
            card = await service.product_card(sku, variety)
            
            if not card:
                unavailable_items.append({
                    "sku": sku,
                    "variety": variety,
                    "error": "Product not found"
                })
                continue
            
            unit_price = card["price"]
            available_qty = card["quantity"]
            line_total = unit_price * quantity
            grand_total += line_total
            
            line_items.append({
                "sku": sku,
                "name": card["name"],
                "variety": variety,
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
                "available": available_qty,
                "in_stock": available_qty >= quantity
            })
        
        return {
            "status": "success",
            "line_items": line_items,
            "grand_total": round(grand_total, 2),
            "currency": "₹",
            "total_quantity": sum(item["quantity"] for item in line_items),
            "unavailable_items": unavailable_items if unavailable_items else None,
            "all_available": len(unavailable_items) == 0 and all(
                item["in_stock"] for item in line_items
            )
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": "calculation_failed",
            "message": f"❌ Failed to calculate total: {str(e)}"
        }


