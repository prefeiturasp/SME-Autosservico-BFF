#!/usr/bin/env bash
# Instala e executa os hooks de pre-commit em todos os arquivos do repositório.
set -euo pipefail

pre-commit install
pre-commit run --all-files
