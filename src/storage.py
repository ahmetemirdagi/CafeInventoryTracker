import os
import json
import csv
from typing import Dict, Any, Tuple

from utils import (
    get_data_file_path,
    get_backups_dir,
    ensure_dir,
    now_utc_iso,
    atomic_write_text,
)
from models import AppData, Settings


BACKUP_KEEP = 20


class Storage:
    def __init__(self, app_root: str, logger):
        self.app_root = app_root
        self.logger = logger
        ensure_dir(get_backups_dir(self.app_root))

    def _template(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "items": [],
            "transactions": [],
            "settings": Settings().__dict__,
        }

    def ensure_initial_files(self) -> None:
        path = get_data_file_path(self.app_root)
        if not os.path.exists(path):
            self.logger.info("Creating initial items.json at %s", path)
            content = json.dumps(self._template(), ensure_ascii=False, indent=2)
            atomic_write_text(path, content)

    def load(self) -> AppData:
        path = get_data_file_path(self.app_root)
        if not os.path.exists(path):
            self.ensure_initial_files()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = self._migrate_if_needed(data)
        return AppData.from_dict(data)

    def save(self, app_data: AppData, backup_before: bool = False) -> None:
        path = get_data_file_path(self.app_root)
        if backup_before and os.path.exists(path):
            self._write_backup()
        content = json.dumps(app_data.to_dict(), ensure_ascii=False, indent=2)
        atomic_write_text(path, content)
        # Backup after each save as well (spec: on every save create a backup)
        self._write_backup()
        self._rotate_backups()

    def _write_backup(self) -> None:
        src = get_data_file_path(self.app_root)
        if not os.path.exists(src):
            return
        backups_dir = get_backups_dir(self.app_root)
        ts = now_utc_iso().replace(":", "").replace("-", "").replace("T", "_").replace("Z", "")
        name = f"items_{ts}.json"
        dst = os.path.join(backups_dir, name)
        try:
            with open(src, "r", encoding="utf-8") as fsrc:
                content = fsrc.read()
            atomic_write_text(dst, content)
            self.logger.info("Backup written: %s", dst)
        except Exception as e:
            self.logger.error("Failed to write backup: %s", e)

    def _rotate_backups(self) -> None:
        backups_dir = get_backups_dir(self.app_root)
        files = [os.path.join(backups_dir, f) for f in os.listdir(backups_dir) if f.startswith("items_") and f.endswith(".json")]
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for old in files[BACKUP_KEEP:]:
            try:
                os.remove(old)
            except Exception:
                pass

    def _migrate_if_needed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        version = int(data.get("version", 1))
        # Migration stub: current version is 1
        if version < 1:
            data["version"] = 1
        return data

    # CSV
    def export_csv(self, app_data: AppData, file_path: str) -> None:
        delimiter = app_data.settings.csv_delimiter
        headers = [
            "id",
            "name",
            "category",
            "unit",
            "unit_cost",
            "unit_price",
            "stock_qty",
            "reorder_level",
            "supplier",
            "barcode",
            "notes",
        ]
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=delimiter)
            writer.writeheader()
            for i in app_data.items:
                writer.writerow({
                    "id": i.id,
                    "name": i.name,
                    "category": i.category,
                    "unit": i.unit,
                    "unit_cost": i.unit_cost if i.unit_cost is not None else "",
                    "unit_price": i.unit_price if i.unit_price is not None else "",
                    "stock_qty": i.stock_qty,
                    "reorder_level": i.reorder_level,
                    "supplier": i.supplier or "",
                    "barcode": i.barcode or "",
                    "notes": i.notes or "",
                })

    def import_csv(self, app_data: AppData, file_path: str) -> Tuple[AppData, Dict[str, Any]]:
        # Backup before import
        self._write_backup()
        delimiter = app_data.settings.csv_delimiter
        summary = {"added": 0, "updated": 0, "skipped": 0, "skipped_rows": []}
        def normalize_num(v):
            if v is None or v == "":
                return None
            try:
                if "." in v:
                    return float(v)
                return float(v)
            except Exception:
                raise ValueError("Invalid number")
        def normalize_int(v, default=None):
            if v is None or v == "":
                return default if default is not None else 0
            return int(float(v))
        # Build indexes
        id_index = {i.id: idx for idx, i in enumerate(app_data.items)}
        name_index = {i.name.strip().lower(): idx for idx, i in enumerate(app_data.items)}
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for rownum, row in enumerate(reader, start=2):
                try:
                    name = (row.get("name") or "").strip()
                    if not name:
                        raise ValueError("Missing name")
                    item_id = (row.get("id") or "").strip()
                    key_idx = None
                    if item_id and item_id in id_index:
                        key_idx = id_index[item_id]
                    elif name.strip().lower() in name_index:
                        key_idx = name_index[name.strip().lower()]
                    # Build fields
                    category = (row.get("category") or "Other").strip() or "Other"
                    unit = (row.get("unit") or "piece").strip() or "piece"
                    unit_cost = normalize_num((row.get("unit_cost") or "").strip())
                    unit_price = normalize_num((row.get("unit_price") or "").strip())
                    stock_qty = normalize_int((row.get("stock_qty") or "").strip(), default=0)
                    reorder_level = normalize_int((row.get("reorder_level") or "").strip(), default=0)
                    supplier = (row.get("supplier") or "").strip() or None
                    barcode = (row.get("barcode") or "").strip() or None
                    notes = (row.get("notes") or "").strip() or None
                    if key_idx is None:
                        # Add new with provided id if present
                        new_id = item_id or self._generate_temp_id(app_data)
                        from models import Item
                        item = Item(
                            id=new_id,
                            name=name,
                            category=category,
                            unit=unit,
                            unit_cost=unit_cost,
                            unit_price=unit_price,
                            stock_qty=stock_qty,
                            reorder_level=reorder_level,
                            supplier=supplier,
                            barcode=barcode,
                            notes=notes,
                            last_updated=now_utc_iso(),
                        )
                        item.validate()
                        app_data.items.append(item)
                        id_index[item.id] = len(app_data.items) - 1
                        name_index[item.name.strip().lower()] = len(app_data.items) - 1
                        summary["added"] += 1
                    else:
                        item = app_data.items[key_idx]
                        item.name = name
                        item.category = category
                        item.unit = unit
                        item.unit_cost = unit_cost
                        item.unit_price = unit_price
                        item.stock_qty = stock_qty
                        item.reorder_level = reorder_level
                        item.supplier = supplier
                        item.barcode = barcode
                        item.notes = notes
                        item.last_updated = now_utc_iso()
                        item.validate()
                        summary["updated"] += 1
                except Exception as e:
                    summary["skipped"] += 1
                    summary["skipped_rows"].append({"row": rownum, "reason": str(e)})
        return app_data, summary

    def _generate_temp_id(self, app_data: AppData) -> str:
        # Temporary ID for import if SKU missing; services will normalize later if needed
        base = "SKU-TEMP-"
        n = 1
        existing = {i.id for i in app_data.items}
        while f"{base}{n:04d}" in existing:
            n += 1
        return f"{base}{n:04d}"
