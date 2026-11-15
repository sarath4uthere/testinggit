#!/bin/sh
set -e
echo "[entrypoint] running migrations"
python migrate.py
echo "[entrypoint] starting gunicorn (version ${APP_VERSION})"
exec gunicorn --bind 0.0.0.0:8000 --workers 1 --threads 4 --access-logfile - "app:create_app()"
