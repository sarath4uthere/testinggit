const rows = document.getElementById("product-rows");
const message = document.getElementById("message");

function say(text, kind) {
  message.textContent = text;
  message.className = kind || "";
}

async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error || `request failed (${response.status})`);
  return body;
}

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text; // textContent, never innerHTML: product names are untrusted input
  return td;
}

async function loadProducts() {
  const products = await api("/api/products");
  rows.replaceChildren();
  for (const p of products) {
    const tr = document.createElement("tr");
    tr.append(cell(p.id), cell(p.name), cell(Number(p.price).toFixed(2)), cell(p.stock));
    const action = document.createElement("td");
    const button = document.createElement("button");
    button.textContent = "Buy 1";
    button.disabled = p.stock < 1;
    button.addEventListener("click", () => buy(p.id));
    action.append(button);
    tr.append(action);
    rows.append(tr);
  }
}

async function buy(productId) {
  try {
    const order = await api("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: productId, quantity: 1 }),
    });
    say(`Order #${order.id} placed, total ${order.total}`, "ok");
    await loadProducts();
  } catch (err) {
    say(err.message, "error");
  }
}

document.getElementById("product-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: document.getElementById("p-name").value,
        price: Number(document.getElementById("p-price").value),
        stock: Number(document.getElementById("p-stock").value),
      }),
    });
    event.target.reset();
    say("Product added", "ok");
    await loadProducts();
  } catch (err) {
    say(err.message, "error");
  }
});

(async () => {
  try {
    const info = await api("/api/version");
    document.getElementById("api-version").textContent = info.version;
    document.getElementById("env-badge").textContent = info.environment;
    await loadProducts();
  } catch (err) {
    say("Cannot reach the API: " + err.message, "error");
  }
})();
