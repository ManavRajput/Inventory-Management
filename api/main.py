import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.DB.Sql.db_manager import AsyncDBManager
from app.DB.services.inventory_service import InventoryService
from app.DB.models.schema import (
    ProductUpsert, RestockIN, SaleOUT,
    StockResponse, ProductCard, SearchQuery, VarietiesResponse,
    BatchRestockIN, SaleOrderOUT, ProductUpsertBatch
)
from fastapi import UploadFile
import io
import pandas as pd

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Inventory API", version="1.0.0")

db = AsyncDBManager()
service = InventoryService(db)




def csv_to_api_json(file: UploadFile):
    import csv, io
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    items = []

    for row in reader:
        # Map CSV columns to expected dict structure
        item = {
            "sku": row.get("sku"),
            "name": row.get("name"),
            "variety": row.get("variety"),
            "price": float(row.get("price", 0)),
            "attributes": {
                "brand": row.get("brand"),
                "color": row.get("color"),
                "size": row.get("size"),
            },
            "is_active": True,
        }
        items.append(item)

    return items


# Example usage 


@app.on_event("startup")
async def on_startup():
    await db.open()
    await db.init_schema()


@app.on_event("shutdown")
async def on_shutdown():
    await db.close()


@app.post("/products/upsert")
async def upsert_product(payload: ProductUpsert):
    pid = await service.ingest_product(payload.sku, payload.name, payload.variety, payload.price, payload.attributes)
    return {"id": pid, "sku": payload.sku}


from fastapi import APIRouter, File, UploadFile, HTTPException, Body
from typing import Optional
import pandas as pd
import io

@app.post("/products/upsert/batch")
async def upsert_products_batch(
    file: UploadFile
):
    """
    Accepts either a JSON payload or a CSV/Excel file upload.
    User must provide exactly one.
    """


    if file:
        items = csv_to_api_json(file)
    else:
        raise HTTPException(status_code=400, detail="No file found. Please upload a CSV or Excel file.")

    rows = await service.upsert_products_batch(items)
    return {"count": len(rows), "items": rows}


@app.post("/stock/buy/batch")
async def batch_restock(payload: BatchRestockIN):
    try:
        items = [i.model_dump() for i in payload.items]
        await service.batch_restock_in(payload.supplier, payload.ref_id, payload.notes, items)
    except ValueError as e:
        # e may contain dict with shortages
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "count": len(payload.items)}

@app.post("/stock/sell/order")
async def sell_order(payload: SaleOrderOUT):
    try:
        items = [i.model_dump() for i in payload.items]
        await service.sell_order(payload.order_id, payload.channel, payload.notes, items)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "order_id": payload.order_id, "count": len(payload.items)}


@app.post("/stock/buy")
async def restock(payload: RestockIN):
    try:
        await service.restock_in(payload.sku, payload.variety, payload.quantity, payload.unit_price, ref_id=payload.ref_id, notes=payload.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}


@app.post("/stock/sell")
async def sell(payload: SaleOUT):
    try:
        await service.sell_out(payload.sku, payload.variety, payload.quantity, payload.sale_price, ref_id=payload.ref_id, notes=payload.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok"}


@app.get("/products/{sku}/price")
async def get_price(sku: str, variety: str | None = None):
    price = await service.get_price(sku, variety)
    if price is None:
        raise HTTPException(status_code=404, detail="Not found")
    return {"sku": sku, "variety": variety, "price": price}


@app.get("/products/{sku}/stock", response_model=StockResponse)
async def get_stock(sku: str, variety: str | None = None):
    data = await service.get_stock(sku, variety)
    return StockResponse(**data)


@app.get("/products/{sku}/card", response_model=ProductCard)
async def get_card(sku: str, variety: str | None = None):
    card = await service.product_card(sku, variety)
    if not card:
        raise HTTPException(status_code=404, detail="Not found")
    return ProductCard(**card)


@app.get("/products/varieties", response_model=VarietiesResponse)
async def varieties(name: str):
    vs = await service.list_varieties(name)
    return VarietiesResponse(name=name, varieties=vs)


@app.post("/products/search")
async def search(payload: SearchQuery):
    items = await service.search(payload.q, payload.variety)
    return {"count": len(items), "items": items}
