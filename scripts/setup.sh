#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Install Docker first'; exit 1; }
docker info >/dev/null
[[ -f .env ]] || cp .env.example .env
# Core demo needs no external credentials. Generate the optional Grafana password.
if grep -q '^GRAFANA_ADMIN_PASSWORD=$' .env; then
  secret=$(openssl rand -hex 32)
  sed "s/^GRAFANA_ADMIN_PASSWORD=$/GRAFANA_ADMIN_PASSWORD=$secret/" .env > .env.tmp
  mv .env.tmp .env
fi
docker compose config --quiet
docker compose up --build -d --wait --wait-timeout 240
echo 'Dashboard http://localhost:3000 | API http://localhost:8000/docs | AI http://localhost:8001/docs'
