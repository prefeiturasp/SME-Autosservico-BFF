#!/usr/bin/env bash
# Executa a suíte de testes com cobertura dentro do container de desenvolvimento.
set -euo pipefail

docker compose -f docker-compose-dev.yml run --rm web sh -c "coverage run -m pytest && coverage report"
