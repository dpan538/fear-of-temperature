#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

output_dir="$project_dir/outputs/demo/notebooks"
mkdir -p "$output_dir"

for notebook in notebooks/[0-9][0-9]_*.ipynb; do
  output_name="$(basename "$notebook")"
  .venv/bin/jupyter nbconvert \
    --to notebook \
    --execute "$notebook" \
    --ExecutePreprocessor.kernel_name=fear-of-temperature \
    --ExecutePreprocessor.timeout=900 \
    --output "$output_name" \
    --output-dir "$output_dir"
done
