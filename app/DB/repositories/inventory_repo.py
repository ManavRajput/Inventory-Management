from optparse import Option
import uuid
from typing import Optional, List, Dict, Any

from app.DB.Sql.db_manager import AsyncDBManager
# from DB.Sql.db_manager import AsyncDBManager

class InventoryRepository:
    def __init__(self, db: AsyncDBManager):
        self.db = db
  # This function inserts a new product or updates an existing product in the "products" table.
    # It takes product details (sku, name, variety, price, attributes, is_active) and:
    # - If using PostgreSQL, it performs an upsert (insert or update on conflict of sku) and returns the product's id.
    # - If using SQLite, it checks if the product exists by sku:
    #     - If it exists, it updates the product and returns its id.
    #     - If not, it inserts a new product with a generated UUID and returns the new id.
    # The function always returns the id of the upserted product as a string.
    async def upsert_product(self, sku: str, name: str, variety: Optional[str], price: float, quantity: float,
                             attributes: Optional[dict] = None, is_active: bool = True) -> str:
        attributes = attributes or {}
        if self.db.is_postgres():
            query = """
            INSERT INTO products (id, sku, name, variety, price, attributes, is_active)
            VALUES (uuid_generate_v4(), %s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (sku) DO UPDATE
            SET name = EXCLUDED.name,
                variety = EXCLUDED.variety,
                price = EXCLUDED.price,
                quantity = EXCLUDED.quantity,
                attributes = EXCLUDED.attributes,
                is_active = EXCLUDED.is_active
            RETURNING id
            """
            rows = await self.db.execute_query(query, (sku, name, variety, price, quantity, attributes, is_active), commit=True)
            return rows[0]["id"]
        else:
            # SQLite: need to manage IDs ourselves
            row = await self.db.execute_query("SELECT id FROM products WHERE sku = ?", (sku,))
            if row:
                await self.db.execute_query(
                    "UPDATE products SET name=?, variety=?, price=?, qunatity=?, attributes=?, is_active=? WHERE sku=?",
                    (name, variety, price, quantity, json_dumps(attributes), 1 if is_active else 0, sku),
                    commit=True,
                )
                return row[0]["id"]
            new_id = str(uuid.uuid4())
            await self.db.execute_query(
                "INSERT INTO products (id, sku, name, variety, price, quantity, attributes, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_id, sku, name, variety, price, quantity, json_dumps(attributes), 1 if is_active else 0),
                commit=True,
            )
            return new_id

    async def upsert_products_batch(self, items: list[dict], conn=None) -> list[dict]:
        # items: [{sku, name, variety, price, attributes, is_active?}]
        # Normalize attributes
        for it in items:
            it.setdefault("attributes", {})
            it.setdefault("variety", None)
            it.setdefault("is_active", True)

        if self.db.is_postgres():
            cols = ("sku", "name", "variety", "price","quantity","tributes", "is_active")
            placeholders = ", ".join(["(%s, %s, %s, %s, %s::jsonb, %s)"] * len(items))
            flat = []
            for it in items:
                flat.extend([
                    it["sku"], it["name"], it.get("variety"), it["price"],it["quantity"] ,it["attributes"], it.get("is_active", True)
                ])
            sql = f"""
            INSERT INTO products ({", ".join(cols)})
            VALUES {placeholders}
            ON CONFLICT (sku) DO UPDATE
            SET name = EXCLUDED.name,
                variety = EXCLUDED.variety,
                price = EXCLUDED.price,
                quantity = EXCLUDED.quantity,
                attributes = EXCLUDED.attributes,
                is_active = EXCLUDED.is_active
            RETURNING id, sku
            """
            if conn is None:
                rows = await self.db.execute_query(sql, flat, commit=True)
            else:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(sql, flat)
                    rows = await cur.fetchall()
            return rows or []
        else:
            # SQLite: per-row UPSERT inside a single transaction
            q = """
            INSERT INTO products (id, sku, name, variety, price, quantity, attributes, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sku) DO UPDATE SET
                name=excluded.name,
                variety=excluded.variety,
                price=excluded.price,
                quantity = excluded.quantity,
                attributes=excluded.attributes,
                is_active=excluded.is_active
            """
            created = []
            if conn is None:
                async with self.db.transaction() as scon:
                    cur = scon.cursor()
                    for it in items:
                        pid = str(uuid.uuid4())
                        cur.execute(
                            q,
                            (pid, it["sku"], it["name"], it.get("variety"), it["price"], it["quantity"], json_dumps(it["attributes"]),
                             1 if it.get("is_active", True) else 0),
                        )
                        created.append({"id": pid, "sku": it["sku"]})
                return created
            else:
                cur = conn.cursor()
                for it in items:
                    pid = str(uuid.uuid4())
                    cur.execute(
                        q,
                        (pid, it["sku"], it["name"], it.get("variety"), it["price"],it["quantity"], json_dumps(it["attributes"]),
                         1 if it.get("is_active", True) else 0),
                    )
                    created.append({"id": pid, "sku": it["sku"]})
                return created


    async def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        q = "SELECT * FROM products WHERE sku = %s" if self.db.is_postgres() else "SELECT * FROM products WHERE sku = ?"
        rows = await self.db.execute_query(q, (sku,))
        return rows[0] if rows else None

    async def get_price(self, sku: str, variety: Optional[str] = None) -> Optional[float]:
        if self.db.is_postgres():
            q = "SELECT price FROM products WHERE sku = %s AND (%s IS NULL OR variety = %s)"
            rows = await self.db.execute_query(q, (sku, variety, variety))
        else:
            q = "SELECT price FROM products WHERE sku = ? AND (? IS NULL OR variety = ?)"
            rows = await self.db.execute_query(q, (sku, variety, variety))
        return rows[0]["price"] if rows else None

    async def get_stock(self, sku: str, variety: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
        if self.db.is_postgres():
            q = """
            SELECT p.sku, p.name, p.variety, COALESCE(sv.quantity,0) AS quantity
            FROM products p
            LEFT JOIN stock_view sv ON sv.product_id = p.id
            WHERE p.sku = %s AND (%s IS NULL OR p.variety = %s)
            """
            rows = await self.db.execute_query(q, (sku, variety, variety))
        else:
            q = """
            SELECT p.sku, p.name, p.variety, COALESCE(sv.quantity,0) AS quantity
            FROM products p
            LEFT JOIN stock_view sv ON sv.product_id = p.id
            WHERE p.sku = ? AND (? IS NULL OR p.variety = ?)
            """
            rows = await self.db.execute_query(q, (sku, variety, variety))
        if not rows:
            return {"sku": sku, "quantity": 0, "available": False}
        qty = rows[0]["quantity"] or 0
        return {"sku": sku, "quantity": qty, "available": qty > 0}

    async def list_varieties(self, name: str) -> List[str]:
        if self.db.is_postgres():
            q = "SELECT DISTINCT variety FROM products WHERE name ILIKE %s AND variety IS NOT NULL"
            rows = await self.db.execute_query(q, (f"%{name}%",))
        else:
            q = "SELECT DISTINCT variety FROM products WHERE name LIKE ? AND variety IS NOT NULL"
            rows = await self.db.execute_query(q, (f"%{name}%",))
        return [r["variety"] for r in rows if r["variety"]]

    async def product_card(self, sku: str, variety: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if self.db.is_postgres():
            q = """
            SELECT p.sku, p.name, p.variety, p.price,
                   COALESCE(sv.quantity,0) AS quantity,
                   (COALESCE(sv.quantity,0) > 0) AS available
            FROM products p
            LEFT JOIN stock_view sv ON sv.product_id = p.id
            WHERE p.sku = %s AND (%s IS NULL OR p.variety = %s)
            """
            rows = await self.db.execute_query(q, (sku, variety, variety))
        else:
            q = """
            SELECT p.sku, p.name, p.variety, p.price,
                   COALESCE(sv.quantity,0) AS quantity,
                   CASE WHEN COALESCE(sv.quantity,0) > 0 THEN 1 ELSE 0 END AS available
            FROM products p
            LEFT JOIN stock_view sv ON sv.product_id = p.id
            WHERE p.sku = ? AND (? IS NULL OR p.variety = ?)
            """
            rows = await self.db.execute_query(q, (sku, variety, variety))
        if not rows:
            return None
        row = rows[0]
        return {
            "sku": row["sku"],
            "name": row["name"],
            "variety": row["variety"],
            "price": float(row["price"]),
            "quantity": float(row["quantity"]),
            "available": bool(row["available"]),
        }

    async def search(self, query: str, variety: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for products whose SKU or name matches the given query string,
        optionally filtering by variety.

        Args:
            query (str): The search string to match against product SKU or name.
                For example, if you have inserted a product with
                sku="123", name="colgate", variety="toothpaste",
                then:
                    - search("123") will match this product (by SKU)
                    - search("colgate") will match this product (by name)
                    - search("toothpaste") will NOT match unless 'toothpaste' is in the SKU or name
                    - search("col", variety="toothpaste") will match this product (partial name and variety filter)

            variety (Optional[str]): If provided, only products with this variety are included.
                For example, search("colgate", variety="toothpaste") will match the above product.

        Returns:
            List[Dict[str, Any]]: A list of product records, each including sku, name, variety, price, quantity, and availability.

        Example usage:
            await repo.search("123")
            await repo.search("colgate")
            await repo.search("col", variety="toothpaste")
        """
        # 'query' is the search string used to match product SKU or name (partial match).
        if self.db.is_postgres():
            q = """
            SELECT p.sku, p.name, p.variety, p.price, AS quantity,
                   (COALESCE(sv.quantity,0) > 0) AS available
            FROM products p
            LEFT JOIN stock_view sv ON sv.product_id = p.id
            WHERE (p.sku ILIKE %s OR p.name ILIKE %s)
              AND (%s IS NULL OR p.variety = %s)
            ORDER BY p.name
            """
            rows = await self.db.execute_query(q, (f"%{query}%", f"%{query}%", variety, variety))
        else:
            q = """
            SELECT p.sku, p.name, p.variety, p.price,
                   COALESCE(sv.quantity,0) AS quantity,
                   CASE WHEN COALESCE(sv.quantity,0) > 0 THEN 1 ELSE 0 END AS available
            FROM products p
            LEFT JOIN stock_view sv ON sv.product_id = p.id
            WHERE (p.sku LIKE ? OR p.name LIKE ?)
              AND (? IS NULL OR p.variety = ?)
            ORDER BY p.name
            """
            rows = await self.db.execute_query(q, (f"%{query}%", f"%{query}%", variety, variety))
        out = []
        for r in rows or []:
            out.append({
                "sku": r["sku"],
                "name": r["name"],
                "variety": r["variety"],
                "price": float(r["price"]),
                "quantity": int(r["quantity"]),
                "available": bool(r["available"]),
            })
        return out

   
    async def _resolve_product_id(self, sku: str, variety: Optional[str]) -> Optional[str]:

        #  This function looks up and returns the unique product ID from the database for a given SKU and (optionally) variety.
        #  If a variety is provided, it matches both SKU and variety; if not, it matches only by SKU.
        # Returns the product ID as a string if found, or None if no matching product exists.
        
        if self.db.is_postgres():
            q = "SELECT id FROM products WHERE sku = %s AND (%s IS NULL OR variety = %s)"
            rows = await self.db.execute_query(q, (sku, variety, variety))
        else:
            q = "SELECT id FROM products WHERE sku = ? AND (? IS NULL OR variety = ?)"
            rows = await self.db.execute_query(q, (sku, variety, variety))
        return rows[0]["id"] if rows else None

    async def insert_ledger(self, product_id: str, movement: str, quantity: int,
                            unit_price: Optional[float], source: Optional[str],
                            ref_id: Optional[str], notes: Optional[str], conn=None):
        """
        
        This function inserts a new record into the stock_ledger table to log a stock movement (such as IN, OUT, or ADJUST) for a given product.
        It records the product ID, movement type, quantity, unit price, source, reference ID, and notes.
        The function supports both PostgreSQL and SQLite, and can optionally use an existing database connection (for transactional operations).
        If no connection is provided, it executes the insert as a standalone operation.

        Insert a new record into the stock_ledger table to log a stock movement.

        Args:
            product_id (str): The unique ID of the product.
            movement (str): The type of stock movement ('IN', 'OUT', 'ADJUST').
            quantity (int): The quantity of the movement.
            unit_price (Optional[float]): The price per unit for this movement.
            source (Optional[str]): The source of the movement (e.g., 'supplier', 'sale').
            ref_id (Optional[str]): An optional reference ID for this transaction. 
                This can be used to link the ledger entry to an external document, 
                invoice, purchase order, or sale transaction. For example, for a 
                restock, ref_id might be a supplier invoice number; for a sale, 
                it could be a sales order or receipt number.
            notes (Optional[str]): Any additional notes or comments.
            conn: Optional database connection for transactional operations.

        Returns:
            None
        """
        if self.db.is_postgres():
            q = """
            INSERT INTO stock_ledger (product_id, movement, quantity, unit_price, source, ref_id, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            params = (product_id, movement, quantity, unit_price, source, ref_id, notes)
            if conn is None:
                await self.db.execute_query(q, params, commit=True)
            else:
                async with conn.cursor() as cur:
                    await cur.execute(q, params)
        else:
            q = """
            INSERT INTO stock_ledger (product_id, movement, quantity, unit_price, source, ref_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (product_id, movement, quantity, unit_price, source, ref_id, notes)
            if conn is None:
                await self.db.execute_query(q, params, commit=True)
            else:
                conn.execute(q.replace("%s", "?"), params)

    async def select_stock_for_update(self, product_id: str, conn):
        if self.db.is_postgres():
            q = """
            SELECT COALESCE(SUM(CASE
                       WHEN movement='IN' THEN quantity
                       WHEN movement='OUT' THEN -quantity
                       WHEN movement='ADJUST' THEN quantity
                   END), 0) AS qty
            FROM stock_ledger
            WHERE product_id = %s
            FOR UPDATE
            """
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(q, (product_id,))
                row = await cur.fetchone()
                return int(row["qty"])
        else:
            # SQLite: no row-level locks; BEGIN IMMEDIATE already holds a write lock
            q = """
            SELECT COALESCE(SUM(CASE
                WHEN movement='IN' THEN quantity
                WHEN movement='OUT' THEN -quantity
                WHEN movement='ADJUST' THEN quantity
            END), 0) AS qty
            FROM stock_ledger
            WHERE product_id = ?
            """
            cur = conn.cursor()
            cur.execute(q, (product_id,))
            row = cur.fetchone()
            return int(row[0] if row and row[0] is not None else 0)
    
    async def resolve_many_product_ids(self, items: list[dict]) -> dict:
        # items contain {"sku": str, "variety": Optional[str]}
        ids: dict[tuple[str, Optional[str]], str] = {}
        for it in items:
            pid = await self._resolve_product_id(it["sku"], it.get("variety"))
            if not pid:
                raise ValueError(f"Product not found: {it['sku']} ({it.get('variety')})")
            ids[(it["sku"], it.get("variety"))] = pid
        return ids

    async def select_many_stocks_for_update(self, product_ids: list[str], conn) -> dict[str, int]:
        stocks: dict[str, int] = {}
        if self.db.is_postgres():
            # Lock each product scope deterministically to avoid deadlocks
            for pid in sorted(product_ids):
                q = """
                SELECT COALESCE(SUM(CASE
                           WHEN movement='IN' THEN quantity
                           WHEN movement='OUT' THEN -quantity
                           WHEN movement='ADJUST' THEN quantity
                       END), 0) AS qty
                FROM stock_ledger
                WHERE product_id = %s
                FOR UPDATE
                """
                async with conn.cursor() as cur:
                    await cur.execute(q, (pid,))
                    row = await cur.fetchone()
                stocks[pid] = int(row[0] if row and row[0] is not None else 0)
        else:
            # SQLite: BEGIN IMMEDIATE already holds the database write lock
            for pid in sorted(product_ids):
                q = """
                SELECT COALESCE(SUM(CASE
                    WHEN movement='IN' THEN quantity
                    WHEN movement='OUT' THEN -quantity
                    WHEN movement='ADJUST' THEN quantity
                END), 0) AS qty
                FROM stock_ledger
                WHERE product_id = ?
                """
                cur = conn.cursor()
                cur.execute(q, (pid,))
                row = cur.fetchone()
                stocks[pid] = int(row[0] if row and row[0] is not None else 0)
        return stocks



def json_dumps(obj) -> str:
    import json
    return json.dumps(obj, separators=(",", ":"))

