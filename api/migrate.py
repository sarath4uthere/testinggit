"""Tiny migration runner (the idea behind Flyway / Liquibase).

Applies every migrations/*.sql file once, in name order, and records it in
the schema_migrations table. An advisory lock makes it safe when several
copies of the app start at the same time (for example in Kubernetes).
"""
import glob
import os
import sys
import time

import psycopg2

LOCK_ID = 727274
HERE = os.path.dirname(os.path.abspath(__file__))


def connect():
    last_error = None
    for attempt in range(1, 31):
        try:
            return psycopg2.connect(
                host=os.environ.get("DB_HOST", "db"),
                port=int(os.environ.get("DB_PORT", "5432")),
                dbname=os.environ.get("DB_NAME", "shop"),
                user=os.environ.get("DB_USER", "shop"),
                password=os.environ.get("DB_PASSWORD", ""),
                connect_timeout=3,
            )
        except psycopg2.OperationalError as exc:
            last_error = exc
            print(f"[migrate] database not ready (attempt {attempt}/30): {exc}".strip(), flush=True)
            time.sleep(2)
    print(f"[migrate] giving up: {last_error}", flush=True)
    sys.exit(1)


def main():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
    cur.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    conn.commit()

    cur.execute("SELECT version FROM schema_migrations")
    applied = {row[0] for row in cur.fetchall()}

    files = sorted(glob.glob(os.path.join(HERE, "migrations", "*.sql")))
    pending = [f for f in files if os.path.basename(f) not in applied]
    if not pending:
        print("[migrate] database is up to date", flush=True)

    for path in pending:
        name = os.path.basename(path)
        print(f"[migrate] applying {name}", flush=True)
        with open(path, encoding="utf-8") as handle:
            sql = handle.read()
        try:
            cur.execute(sql)
            cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (name,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    cur.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    conn.commit()
    conn.close()
    print("[migrate] done", flush=True)


if __name__ == "__main__":
    main()
