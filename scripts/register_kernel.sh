#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

.venv/bin/python -m ipykernel install --user --name fear-of-temperature --display-name "Python (Fear of Temperature)"
echo "Remove with: .venv/bin/jupyter kernelspec uninstall fear-of-temperature"
