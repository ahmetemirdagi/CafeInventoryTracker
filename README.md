# Cafe Stock Tracker

A simple, offline-first desktop inventory app for small cafes. Built with Python 3.11 and PySimpleGUI. Stores all data in a single local JSON file `items.json` alongside the executable.

## Features
- CRUD items with validation (name unique, non-negative stock)
- Stock In/Out/Adjust with transaction history
- Search by name/SKU/supplier; filter by category; show Low Stock toggle
- CSV export/import (append/upsert); automatic JSON backup and rotation (keep last 20)
- Single-file Windows/macOS executable via PyInstaller
- Rotating logs to `logs/app.log`
- Single-instance lock file to prevent concurrent writes

## Quick Start (Development)

### Using uv (recommended)
```bash
# install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh
# or: pipx install uv

# create and activate a Python 3.11 venv managed by uv
uv venv -p 3.11
source .venv/bin/activate  # macOS/Linux
# Windows: .venv\Scripts\activate

# install dependencies from pyproject.toml (prod deps)
uv pip install .
# dev deps (pytest, pyinstaller)
uv pip install .[dev]

# run the app
python src/main.py
```

### Using pip (alternative)
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

## Build Executables

### macOS (app or single binary)
```bash
# in activated venv
uv pip install .[dev]  # ensures pyinstaller installed
# app bundle (double-clickable)
pyinstaller --windowed --name "CafeStockTracker" --icon assets/icon.icns src/main.py
# one-file GUI binary
pyinstaller --onefile --windowed --name "CafeStockTracker" --icon assets/icon.icns src/main.py
```
Outputs in `dist/` as `CafeStockTracker.app` or `CafeStockTracker` (binary).

If you don’t have an `.icns`, omit `--icon`.

Gatekeeper (unsigned app):
```bash
xattr -dr com.apple.quarantine "dist/CafeStockTracker.app"
```

### Windows (single-file exe)
```bash
uv pip install .[dev]
pyinstaller --onefile --noconsole --name "CafeStockTracker" --icon assets/icon.ico src/main.py
```
Output: `dist/CafeStockTracker.exe`.

## CSV Format
Exported CSV columns:
- id, name, category, unit, unit_cost, unit_price, stock_qty, reorder_level, supplier, barcode, notes

Import rules:
- Upsert by SKU (`id`). If `id` missing, upsert by lowercase `name`.
- Numeric fields are validated. Invalid rows are skipped with a reason in summary.
- A timestamped backup of `items.json` is created before import.

## Backups and Restore
- On every save, a backup is created under `backups/items_YYYYMMDD_HHMMSS.json`.
- Only the 20 newest backups are kept.
- To restore, close the app, copy a chosen backup over `items.json`, then reopen the app.

## Troubleshooting
- Prefer a clean venv with `uv venv` to avoid global/conda conflicts (e.g., `pathlib` backport).
- If the app says another instance is running, delete `app.lock` only if you are certain no other instance is open.
- Check `logs/app.log` for details. In-app errors include a "Copy details" button.

## Tests
```bash
uv pip install .[dev]
pytest -q
```

## License
MIT
