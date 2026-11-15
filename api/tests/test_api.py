import pytest

from app import create_app
from app.repo import MemoryRepo


@pytest.fixture()
def client():
    app = create_app(repo=MemoryRepo())
    return app.test_client()


def add_product(client, name="Widget", price=10.0, stock=5):
    return client.post("/api/products", json={"name": name, "price": price, "stock": stock})


def test_health_is_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_ready_ok_with_working_repo(client):
    assert client.get("/api/ready").status_code == 200


def test_ready_fails_when_database_is_down():
    class BrokenRepo(MemoryRepo):
        def ping(self):
            raise RuntimeError("database unreachable")

    client = create_app(repo=BrokenRepo()).test_client()
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert "database unreachable" in response.get_json()["error"]


def test_version_comes_from_environment(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "abc12345")
    monkeypatch.setenv("APP_ENV", "test")
    client = create_app(repo=MemoryRepo()).test_client()
    assert client.get("/api/version").get_json() == {"version": "abc12345", "environment": "test"}


def test_products_start_empty(client):
    assert client.get("/api/products").get_json() == []


def test_create_and_fetch_product(client):
    created = add_product(client, name="Mouse", price=19.5, stock=3)
    assert created.status_code == 201
    body = created.get_json()
    assert body["name"] == "Mouse" and body["price"] == 19.5 and body["stock"] == 3

    fetched = client.get(f"/api/products/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.get_json()["name"] == "Mouse"
    assert len(client.get("/api/products").get_json()) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": "", "price": 5},
        {"name": "X", "price": -1},
        {"name": "X", "price": "abc"},
        {"name": "X", "price": True},
        {"name": "X", "price": 5, "stock": -2},
        {"name": "X", "price": 5, "stock": 1.5},
        {"name": "A" * 101, "price": 5},
    ],
)
def test_product_validation_rejects_bad_input(client, payload):
    assert client.post("/api/products", json=payload).status_code == 400


def test_unknown_product_returns_404(client):
    assert client.get("/api/products/999").status_code == 404


def test_order_reduces_stock(client):
    product_id = add_product(client, price=10.0, stock=10).get_json()["id"]
    order = client.post("/api/orders", json={"product_id": product_id, "quantity": 3})
    assert order.status_code == 201
    assert order.get_json()["total"] == 30.0
    assert client.get(f"/api/products/{product_id}").get_json()["stock"] == 7
    assert len(client.get("/api/orders").get_json()) == 1


def test_order_with_too_much_quantity_is_rejected(client):
    product_id = add_product(client, stock=2).get_json()["id"]
    response = client.post("/api/orders", json={"product_id": product_id, "quantity": 5})
    assert response.status_code == 409
    assert client.get(f"/api/products/{product_id}").get_json()["stock"] == 2


def test_order_for_unknown_product_returns_404(client):
    assert client.post("/api/orders", json={"product_id": 42, "quantity": 1}).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [{}, {"product_id": "x", "quantity": 1}, {"product_id": 1, "quantity": 0}, {"product_id": 1, "quantity": True}],
)
def test_order_validation_rejects_bad_input(client, payload):
    assert client.post("/api/orders", json=payload).status_code == 400


def test_metrics_exposes_prometheus_text(client):
    client.get("/api/health")
    response = client.get("/api/metrics")
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "shop_http_requests_total" in text
    assert "shop_app_info" in text
