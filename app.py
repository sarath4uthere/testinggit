import os
import time
import psycopg2
from flask import Flask, jsonify, request

app = Flask(__name__)


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        dbname=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
        connect_timeout=3,
    )


def run(sql, params=None, fetch=False):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows
    finally:
        conn.close()


def init_db():
    for _ in range(10):
        try:
            run(
                "CREATE TABLE IF NOT EXISTS notes ("
                "id SERIAL PRIMARY KEY, "
                "text TEXT NOT NULL, "
                "created_at TIMESTAMP DEFAULT now())"
            )
            print("database ready next 2", flush=True)
            return
        except Exception as e:
            print("waiting for database:", e, flush=True)
            time.sleep(2)
    raise RuntimeError("database never became available")


@app.get("/")
def home():
    try:
        count = run("SELECT count(*) FROM notes", fetch=True)[0][0]
        return f"API is running. Database reachable. Notes stored: {count}\n"
    except Exception as e:
        return f"API is running, but database error: {e}\n", 500


@app.get("/add")
def add():
    text = request.args.get("text", "").strip()
    if not text:
        return "Use /add?text=hello\n", 400
    run("INSERT INTO notes (text) VALUES (%s)", (text,))
    return f"Saved: {text}\n"


@app.get("/notes")
def notes():
    rows = run("SELECT id, text, created_at FROM notes ORDER BY id", fetch=True)
    return jsonify(
        [{"id": r[0], "text": r[1], "created_at": r[2].isoformat()} for r in rows]
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)