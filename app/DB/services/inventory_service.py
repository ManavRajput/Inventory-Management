from typing import Optional

from app.DB.Sql.db_manager import AsyncDBManager
from app.DB.repositories.inventory_repo import InventoryRepository


class InventoryService:
    def __init__(self, db: AsyncDBManager):
        self.db = db
        self.repo = InventoryRepository(db)

    async def ingest_product(self, sku: str, name: str, variety: Optional[str], price: float, attributes: dict | None):
        return await self.repo.upsert_product(sku, name, variety, price, attributes or {}, True)
    
    async def upsert_products_batch(self, items: list[dict]) -> list[dict]:
        # All-or-nothing for Postgres in one statement; SQLite uses one txn with per-row upserts
        async with self.db.transaction() as conn:
            return await self.repo.upsert_products_batch(items, conn=conn)


    async def restock_in(self, sku: str, variety: Optional[str], quantity: int,
                         unit_price: Optional[float], source: str = "supplier",
                         ref_id: Optional[str] = None, notes: Optional[str] = None):
        product_id = await self.repo._resolve_product_id(sku, variety)
        if not product_id:
            raise ValueError("Product not found; create it before restocking")
        # Append IN movement
        await self.repo.insert_ledger(product_id, "IN", quantity, unit_price, source, ref_id, notes)

    async def sell_out(self, sku: str, variety: Optional[str], quantity: int,
                       sale_price: Optional[float], ref_id: Optional[str] = None, notes: Optional[str] = None):
        product_id = await self.repo._resolve_product_id(sku, variety)
        if not product_id:
            raise ValueError("Product not found")

        async with self.db.transaction() as conn:
            # Lock the stock row scope and compute current qty
            current_qty = await self.repo.select_stock_for_update(product_id, conn)
            if current_qty < quantity:
                raise ValueError(f"Insufficient stock. Available={current_qty}, requested={quantity}")
            # Append OUT movement
            await self.repo.insert_ledger(product_id, "OUT", quantity, sale_price, "sale", ref_id, notes, conn=conn)

    async def batch_restock_in(self, supplier: str | None, batch_ref_id: str | None, notes: str | None, items: list[dict]):
        # items: list of RestockIN-like dicts
        # Single transaction for atomic batch posting
        async with self.db.transaction() as conn:
            # Resolve product ids
            ids = await self.repo.resolve_many_product_ids(items)
            # Insert ledger rows
            for it in items:
                pid = ids[(it["sku"], it.get("variety"))]
                ref = it.get("ref_id") or batch_ref_id
                note_line = it.get("notes") or notes
                await self.repo.insert_ledger(
                    product_id=pid,
                    movement="IN",
                    quantity=int(it["quantity"]),
                    unit_price=it.get("unit_price"),
                    source=supplier or "supplier",
                    ref_id=ref,
                    notes=note_line,
                    conn=conn,
                )

    async def sell_order(self, order_id: str, channel: str | None, notes: str | None, items: list[dict]):
        # items: list of OrderItem-like dicts
        async with self.db.transaction() as conn:
            # 1) Resolve product ids
            ids = await self.repo.resolve_many_product_ids(items)
            product_ids = [ids[(it["sku"], it.get("variety"))] for it in items]
            # 2) Lock and read stocks for all products
            stocks = await self.repo.select_many_stocks_for_update(product_ids, conn)
            # 3) Validate availability per line
            shortages = []
            for it in items:
                pid = ids[(it["sku"], it.get("variety"))]
                req = int(it["quantity"])
                have = stocks.get(pid, 0)
                if have < req:
                    shortages.append({
                        "sku": it["sku"],
                        "variety": it.get("variety"),
                        "requested": req,
                        "available": have,
                    })
            if shortages:
                raise ValueError({"order_id": order_id, "shortages": shortages})
            # 4) Append OUT movements
            for it in items:
                pid = ids[(it["sku"], it.get("variety"))]
                await self.repo.insert_ledger(
                    product_id=pid,
                    movement="OUT",
                    quantity=int(it["quantity"]),
                    unit_price=it.get("sale_price"),
                    source=channel or "sale",
                    ref_id=order_id,
                    notes=notes,
                    conn=conn,
                )

    async def get_price(self, sku: str, variety: Optional[str]):
        return await self.repo.get_price(sku, variety)

    async def get_stock(self, sku: str, variety: Optional[str]):
        return await self.repo.get_stock(sku, variety)

    async def product_card(self, sku: str, variety: Optional[str]):
        return await self.repo.product_card(sku, variety)

    async def list_varieties(self, name: str):
        return await self.repo.list_varieties(name)

    async def search(self, query: str, variety: Optional[str]):
        return await self.repo.search(query, variety)
