"""Data access layer.

PgRepo talks to PostgreSQL (used in containers).
MemoryRepo keeps data in a dict (used by unit tests, no database needed).
Both expose the same methods, so the Flask code never knows the difference.
"""
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal


class NotFound(Exception):
    pass


class OutOfStock(Exception):
    pass


def _norm(row):
    """Make a DB row JSON friendly (Decimal -> float, datetime -> ISO string)."""
    out = {}
    for key, value in dict(row).items():
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        out[key] = value
    return out


class PgRepo:
    def __init__(self, **connect_kwargs):
        self.kw = connect_kwargs

    @classmethod
    def from_env(cls):
        return cls(
            host=os.environ.get("DB_HOST", "db"),
            port=int(os.environ.get("DB_PORT", "5432")),
            dbname=os.environ.get("DB_NAME", "shop"),
            user=os.environ.get("DB_USER", "shop"),
            password=os.environ.get("DB_PASSWORD", ""),
            connect_timeout=3,
        )

    @contextmanager
    def _cursor(self):
        # imported here so unit tests do not need psycopg2 installed
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(**self.kw)
        try:
            with conn:  # commit on success, rollback on exception
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    yield cur
        finally:
            conn.close()

    def ping(self):
        with self._cursor() as cur:
            cur.execute("SELECT 1")
        return True

    def list_products(self):
        with self._cursor() as cur:
            cur.execute("SELECT id, name, price, stock, created_at FROM products ORDER BY id")
            return [_norm(r) for r in cur.fetchall()]

    def get_product(self, product_id):
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, name, price, stock, created_at FROM products WHERE id = %s",
                (product_id,),
            )
            row = cur.fetchone()
        if not row:
            raise NotFound()
        return _norm(row)

    def create_product(self, name, price, stock):
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO products (name, price, stock) VALUES (%s, %s, %s) "
                "RETURNING id, name, price, stock, created_at",
                (name, price, stock),
            )
            return _norm(cur.fetchone())

    def create_order(self, product_id, quantity):
        with self._cursor() as cur:
            # lock the row so two orders cannot oversell the same stock
            cur.execute(
                "SELECT id, price, stock FROM products WHERE id = %s FOR UPDATE",
                (product_id,),
            )
            product = cur.fetchone()
            if not product:
                raise NotFound()
            if product["stock"] < quantity:
                raise OutOfStock()
            cur.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (quantity, product_id),
            )
            cur.execute(
                "INSERT INTO orders (product_id, quantity, total) VALUES (%s, %s, %s) "
                "RETURNING id, product_id, quantity, total, created_at",
                (product_id, quantity, product["price"] * quantity),
            )
            return _norm(cur.fetchone())

    def list_orders(self):
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, product_id, quantity, total, created_at FROM orders ORDER BY id"
            )
            return [_norm(r) for r in cur.fetchall()]


class MemoryRepo:
    def __init__(self):
        self._lock = threading.Lock()
        self._products = {}
        self._orders = []
        self._next_product = 1
        self._next_order = 1

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def ping(self):
        return True

    def list_products(self):
        return [dict(p) for p in self._products.values()]

    def get_product(self, product_id):
        if product_id not in self._products:
            raise NotFound()
        return dict(self._products[product_id])

    def create_product(self, name, price, stock):
        with self._lock:
            product = {
                "id": self._next_product,
                "name": name,
                "price": float(price),
                "stock": stock,
                "created_at": self._now(),
            }
            self._products[product["id"]] = product
            self._next_product += 1
            return dict(product)

    def create_order(self, product_id, quantity):
        with self._lock:
            if product_id not in self._products:
                raise NotFound()
            product = self._products[product_id]
            if product["stock"] < quantity:
                raise OutOfStock()
            product["stock"] -= quantity
            order = {
                "id": self._next_order,
                "product_id": product_id,
                "quantity": quantity,
                "total": round(product["price"] * quantity, 2),
                "created_at": self._now(),
            }
            self._orders.append(order)
            self._next_order += 1
            return dict(order)

    def list_orders(self):
        return [dict(o) for o in self._orders]
