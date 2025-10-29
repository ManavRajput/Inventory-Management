import os
import json
import logging
import hashlib
import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Optional Postgres
try:
    from psycopg_pool import AsyncConnectionPool
    from psycopg.rows import dict_row
except Exception:
    AsyncConnectionPool = None
    dict_row = None

# SQLite
import sqlite3

load_dotenv()
logger = logging.getLogger(__name__)


class AsyncDBManager:
    _instance = None

    def __new__(cls, connection_string: str | None = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.connection_string = connection_string or os.getenv("POSTGRES_URL")
            cls._instance.pool = None
            cls._instance.fallback = None
            cls._instance.sqlite_conn = None
        return cls._instance

    async def open(self):
        if self.connection_string and AsyncConnectionPool:
            try:
                logger.info("Connecting to PostgreSQL...")
                self.pool = AsyncConnectionPool(
                    conninfo=self.connection_string,
                    min_size=1,
                    max_size=10,
                )
                await self.pool.open()
                self.fallback = "postgres"
                logger.info("Connected to PostgreSQL")
                return
            except Exception as e:
                logger.error(f"PostgreSQL unavailable: {e}")

        logger.warning("Using SQLite fallback (offline.db)")
        self._use_sqlite()

    def _use_sqlite(self):
        self.fallback = "sqlite"
        self.sqlite_conn = sqlite3.connect("offline.db", check_same_thread=False, isolation_level=None)
        self.sqlite_conn.row_factory = sqlite3.Row
        # Enable FK constraints
        self.sqlite_conn.execute("PRAGMA foreign_keys = ON;")
        logger.info("Connected to SQLite")

    async def close(self):
        if self.fallback == "postgres" and self.pool:
            await self.pool.close()
            logger.info("PostgreSQL pool closed")
        elif self.fallback == "sqlite" and self.sqlite_conn:
            self.sqlite_conn.close()
            logger.info("SQLite connection closed")

    async def init_schema(self):
        base_dir = os.path.dirname(__file__)
        if self.fallback == "postgres":
            sql_file = os.path.join(base_dir, "schema_postgres.sql")
        elif self.fallback == "sqlite":
            sql_file = os.path.join(base_dir, "schema_sqlite.sql")
        else:
            raise RuntimeError("Database backend not initialized")

        if not os.path.exists(sql_file):
            logger.warning(f"{sql_file} not found, skipping schema init")
            return

        with open(sql_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        if self.fallback == "postgres":
            await self.execute_script(schema_sql)
            logger.info("PostgreSQL schema initialized")
        else:
            self.sqlite_conn.executescript(schema_sql)
            logger.info("SQLite schema initialized")

    async def execute_query(self, query: str, params: tuple | list | dict | None = None, commit: bool = False):
        if self.fallback == "postgres":
            async with self.pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(query, params)
                    rows = None
                    if cur.description:
                        rows = await cur.fetchall()
                    if commit:
                        await conn.commit()
                    return rows
        else:
            cur = self.sqlite_conn.cursor()
            # Convert %s -> ? for SQLite
            q = query.replace("%s", "?")
            cur.execute(q, params or [])
            rows = cur.fetchall() if cur.description else None
            if commit:
                self.sqlite_conn.commit()
            if rows is None:
                return None
            return [dict(zip([d[0] for d in cur.description], r)) for r in rows]

    async def execute_script(self, script_sql: str):
        if self.fallback == "postgres":
            # Split on ; cautiously â€“ assume DDL safe here
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    for stmt in [s.strip() for s in script_sql.split(";") if s.strip()]:
                        await cur.execute(stmt)
                await conn.commit()
        else:
            self.sqlite_conn.executescript(script_sql)

    @asynccontextmanager
    async def transaction(self):
        if self.fallback == "postgres":
            async with self.pool.connection() as conn:
                try:
                    await conn.execute("BEGIN;")
                    yield conn
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    raise
        else:
            try:
                # BEGIN IMMEDIATE to get a reserved lock before writes
                self.sqlite_conn.execute("BEGIN IMMEDIATE;")
                yield self.sqlite_conn
                self.sqlite_conn.commit()
            except Exception:
                self.sqlite_conn.rollback()
                raise

    def is_postgres(self) -> bool:
        return self.fallback == "postgres"


