# Docker Flask + Postgres lab

Two-container app with Docker Compose: a Flask API image and Postgres with a persistent volume and healthcheck.

Run: docker compose up -d --build
Test: http://localhost:8080/add?text=hello then http://localhost:8080/notes