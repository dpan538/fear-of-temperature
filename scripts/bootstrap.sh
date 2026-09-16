#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

export UV_CACHE_DIR="${UV_CACHE_DIR:-$project_dir/.cache/uv}"
export UV_PYTHON_INSTALL_DIR="${UV_PYTHON_INSTALL_DIR:-$project_dir/.cache/uv/python}"
export UV_PYTHON_BIN_DIR="${UV_PYTHON_BIN_DIR:-$project_dir/.cache/uv/bin}"
mkdir -p "$UV_CACHE_DIR" "$UV_PYTHON_INSTALL_DIR" "$UV_PYTHON_BIN_DIR"

command -v uv >/dev/null 2>&1 || {
  echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
}

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

uv python install 3.12
uv sync --locked --all-extras --group dev
.venv/bin/python scripts/download_models.py
.venv/bin/python -m ipykernel install --user --name fear-of-temperature --display-name "Python (Fear of Temperature)"
.venv/bin/fear-temperature-demo --offline
.venv/bin/python -m fear_temperature.doctor --full-models
