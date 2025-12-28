#!/bin/bash
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Downloading stub model (if not present)..."
python -m app.model_download

echo "Running batch clean..."
python cli/clean_table.py data/mock_inputs.csv -o data/mock_outputs.csv --model-path "$PWD/models/TinyLlama-1.1B-1T-instruct.Q4_K_M.gguf" --workers 2

echo "Results:"
cat data/mock_outputs.csv
