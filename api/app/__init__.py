import os
import time
from decimal import Decimal, InvalidOperation

from flask import Flask, jsonify, request

from .repo import NotFound, OutOfStock, PgRepo


def create_app(repo=None):
    app = Flask(__name__)
    app.json.sort_keys = False
    repo = repo or PgRepo.from_env()

    version = os.environ.get("APP_VERSION", "dev")
    environment = os.environ.get("APP_ENV", "dev")
    started = time.time()
    counters = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}

    @app.after_request
    def count_requests(response):
        bucket = f"{response.status_code // 100}xx"
        counters[bucket] = counters.get(bucket, 0) + 1
        return response

    def bad(message, code=400):
        return jsonify(error=message), code

    # ---------- health and info ----------
    @app.get("/api/health")
    def health():
        """Liveness: the process is up. Does not touch the database."""
        return jsonify(status="ok")

    @app.get("/api/ready")
    def ready():
        """Readiness: the app can reach its database."""
        try:
            repo.ping()
            return jsonify(status="ready")
        except Exception as exc:  # noqa: BLE001
            return jsonify(status="not ready", error=str(exc)), 503

    @app.get("/api/version")
    def get_version():
        return jsonify(version=version, environment=environment)

    @app.get("/api/metrics")
    def metrics():
        lines = [
            "# HELP shop_http_requests_total HTTP responses by status class",
            "# TYPE shop_http_requests_total counter",
        ]
        for bucket, value in sorted(counters.items()):
            lines.append(f'shop_http_requests_total{{status="{bucket}"}} {value}')
        lines += [
            "# HELP shop_uptime_seconds Seconds since the process started",
            "# TYPE shop_uptime_seconds gauge",
            f"shop_uptime_seconds {time.time() - started:.0f}",
            "# HELP shop_app_info Build information",
            "# TYPE shop_app_info gauge",
            f'shop_app_info{{version="{version}",environment="{environment}"}} 1',
        ]
        return "\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; version=0.0.4"}

    # ---------- products ----------
    @app.get("/api/products")
    def list_products():
        return jsonify(repo.list_products())

    @app.get("/api/products/<int:product_id>")
    def get_product(product_id):
        try:
            return jsonify(repo.get_product(product_id))
        except NotFound:
            return bad("product not found", 404)

    @app.post("/api/products")
    def create_product():
        data = request.get_json(silent=True) or {}
        name = data.get("name")
        price = data.get("price")
        stock = data.get("stock", 0)

        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            return bad("name must be a non-empty string up to 100 characters")
        if isinstance(price, bool) or not isinstance(price, (int, float, str)):
            return bad("price must be a number")
        try:
            price = Decimal(str(price)).quantize(Decimal("0.01"))
        except InvalidOperation:
            return bad("price must be a number")
        if price < 0:
            return bad("price must not be negative")
        if isinstance(stock, bool) or not isinstance(stock, int) or stock < 0:
            return bad("stock must be a whole number, zero or more")

        return jsonify(repo.create_product(name.strip(), price, stock)), 201

    # ---------- orders ----------
    @app.get("/api/orders")
    def list_orders():
        return jsonify(repo.list_orders())

    @app.post("/api/orders")
    def create_order():
        data = request.get_json(silent=True) or {}
        product_id = data.get("product_id")
        quantity = data.get("quantity")

        if isinstance(product_id, bool) or not isinstance(product_id, int):
            return bad("product_id must be a whole number")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            return bad("quantity must be a whole number, 1 or more")

        try:
            return jsonify(repo.create_order(product_id, quantity)), 201
        except NotFound:
            return bad("product not found", 404)
        except OutOfStock:
            return bad("not enough stock", 409)

    return app
