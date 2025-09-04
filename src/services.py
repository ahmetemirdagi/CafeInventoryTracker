import os
import re
from typing import List, Optional, Dict, Any, Tuple

from models import AppData, Item, Transaction, TransactionType
from utils import now_utc_iso
from storage import Storage


class Services:
    def __init__(self, storage: Storage, logger):
        self.storage = storage
        self.logger = logger
        self.app_data: AppData = self.storage.load()

    def save(self, backup_before: bool = False) -> None:
        self.storage.save(self.app_data, backup_before=backup_before)

    # ---------- ID generation ----------
    def generate_next_sku(self) -> str:
        pattern = re.compile(r"^SKU-(\d{4,})$")
        max_num = 0
        for it in self.app_data.items:
            m = pattern.match(it.id)
            if m:
                max_num = max(max_num, int(m.group(1)))
        return f"SKU-{max_num + 1:04d}"

    def generate_next_tx_id(self) -> str:
        pattern = re.compile(r"^TX-(\d{6,})$")
        max_num = 0
        for tx in self.app_data.transactions:
            m = pattern.match(tx.id)
            if m:
                max_num = max(max_num, int(m.group(1)))
        return f"TX-{max_num + 1:06d}"

    # ---------- CRUD Items ----------
    def add_item(self, data: Dict[str, Any]) -> Item:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("Name is required")
        # unique name
        if any(i.name.strip().lower() == name.lower() for i in self.app_data.items):
            raise ValueError("An item with this name already exists")
        item_id = (data.get("id") or "").strip() or self.generate_next_sku()
        if any(i.id == item_id for i in self.app_data.items):
            raise ValueError("Item ID already exists")
        item = Item(
            id=item_id,
            name=name,
            category=(data.get("category") or "Other").strip() or "Other",
            unit=(data.get("unit") or "piece").strip() or "piece",
            unit_cost=self._to_float_or_none(data.get("unit_cost")),
            unit_price=self._to_float_or_none(data.get("unit_price")),
            stock_qty=self._to_int_or_default(data.get("stock_qty"), 0),
            reorder_level=self._to_int_or_default(data.get("reorder_level"), 0),
            supplier=((data.get("supplier") or "").strip() or None),
            barcode=((data.get("barcode") or "").strip() or None),
            notes=((data.get("notes") or "").strip() or None),
            last_updated=now_utc_iso(),
        )
        item.validate()
        self.app_data.items.append(item)
        self.save()
        return item

    def update_item(self, item_id: str, updates: Dict[str, Any]) -> Item:
        item = self._get_item_or_raise(item_id)
        # Validate name uniqueness if changed
        new_name = updates.get("name")
        if new_name is not None:
            nn = new_name.strip()
            if not nn:
                raise ValueError("Name is required")
            if any(i.name.strip().lower() == nn.lower() and i.id != item.id for i in self.app_data.items):
                raise ValueError("An item with this name already exists")
            item.name = nn
        if "category" in updates:
            item.category = (updates.get("category") or "Other").strip() or "Other"
        if "unit" in updates:
            item.unit = (updates.get("unit") or "piece").strip() or "piece"
        if "unit_cost" in updates:
            item.unit_cost = self._to_float_or_none(updates.get("unit_cost"))
        if "unit_price" in updates:
            item.unit_price = self._to_float_or_none(updates.get("unit_price"))
        if "stock_qty" in updates:
            item.stock_qty = self._to_int_or_default(updates.get("stock_qty"), item.stock_qty)
        if "reorder_level" in updates:
            item.reorder_level = self._to_int_or_default(updates.get("reorder_level"), item.reorder_level)
        if "supplier" in updates:
            item.supplier = (updates.get("supplier") or "").strip() or None
        if "barcode" in updates:
            item.barcode = (updates.get("barcode") or "").strip() or None
        if "notes" in updates:
            item.notes = (updates.get("notes") or "").strip() or None
        item.last_updated = now_utc_iso()
        item.validate()
        self.save()
        return item

    def delete_item(self, item_id: str, confirm_delete_transactions: bool) -> None:
        idx = self._find_item_index(item_id)
        if idx < 0:
            raise ValueError("Item not found")
        has_tx = any(tx.sku == item_id for tx in self.app_data.transactions)
        if has_tx and not confirm_delete_transactions:
            raise ValueError("Item has transactions. Confirmation required to delete.")
        # Remove
        del self.app_data.items[idx]
        if has_tx:
            self.app_data.transactions = [tx for tx in self.app_data.transactions if tx.sku != item_id]
        self.save()

    # ---------- Stock operations ----------
    def stock_in(self, item_id: str, qty: int, reason: str = "Purchase", note: Optional[str] = None) -> Transaction:
        if qty <= 0:
            raise ValueError("Quantity must be > 0")
        item = self._get_item_or_raise(item_id)
        item.stock_qty += qty
        item.last_updated = now_utc_iso()
        tx = Transaction(
            id=self.generate_next_tx_id(),
            type=TransactionType.IN,
            sku=item.id,
            qty=qty,
            timestamp=now_utc_iso(),
            reason=reason,
            note=note,
        )
        tx.validate()
        self.app_data.transactions.append(tx)
        item.validate()
        self.save()
        return tx

    def stock_out(self, item_id: str, qty: int, reason: str = "Sale", note: Optional[str] = None) -> Transaction:
        if qty <= 0:
            raise ValueError("Quantity must be > 0")
        item = self._get_item_or_raise(item_id)
        if item.stock_qty - qty < 0:
            raise ValueError("Cannot reduce stock below 0")
        item.stock_qty -= qty
        item.last_updated = now_utc_iso()
        tx = Transaction(
            id=self.generate_next_tx_id(),
            type=TransactionType.OUT,
            sku=item.id,
            qty=qty,
            timestamp=now_utc_iso(),
            reason=reason,
            note=note,
        )
        tx.validate()
        self.app_data.transactions.append(tx)
        item.validate()
        self.save()
        return tx

    def stock_adjust(self, item_id: str, qty: int, mode: str = "set", reason: str = "Count correction", note: Optional[str] = None) -> Transaction:
        """Adjust stock. mode="set" sets to value qty; mode="delta" adds qty (can be +/-).
        For transactions, we record the absolute magnitude in qty due to schema (>0).
        """
        item = self._get_item_or_raise(item_id)
        if mode == "set":
            if qty < 0:
                raise ValueError("New quantity must be >= 0")
            delta = qty - item.stock_qty
            new_qty = qty
        elif mode == "delta":
            delta = qty
            new_qty = item.stock_qty + qty
            if new_qty < 0:
                raise ValueError("Cannot reduce stock below 0")
        else:
            raise ValueError("Invalid adjust mode")
        item.stock_qty = new_qty
        item.last_updated = now_utc_iso()
        magnitude = abs(delta)
        if magnitude == 0:
            # No-op; but still update last_updated? Choose to return without tx.
            self.save()
            raise ValueError("No change in quantity")
        tx = Transaction(
            id=self.generate_next_tx_id(),
            type=TransactionType.ADJUST,
            sku=item.id,
            qty=magnitude,
            timestamp=now_utc_iso(),
            reason=reason,
            note=(note or (f"Set to {new_qty}" if mode == "set" else f"Delta {delta:+d}")),
        )
        tx.validate()
        self.app_data.transactions.append(tx)
        item.validate()
        self.save()
        return tx

    # ---------- Search / Filter ----------
    def search_items(self, query: str = "", category: Optional[str] = None, low_only: bool = False) -> List[Item]:
        q = (query or "").strip().lower()
        low_inclusive = self.app_data.settings.low_stock_inclusive
        def matches(i: Item) -> bool:
            ok = True
            if q:
                ok = (
                    q in i.name.lower() or q in i.id.lower() or (i.supplier or "").lower().find(q) >= 0
                )
            if ok and category and category != "All":
                ok = i.category == category
            if ok and low_only:
                ok = (i.stock_qty <= i.reorder_level) if low_inclusive else (i.stock_qty < i.reorder_level)
            return ok
        return [i for i in self.app_data.items if matches(i)]

    def counts(self) -> Tuple[int, int]:
        total = len(self.app_data.items)
        low_inclusive = self.app_data.settings.low_stock_inclusive
        if low_inclusive:
            low = sum(1 for i in self.app_data.items if i.stock_qty <= i.reorder_level)
        else:
            low = sum(1 for i in self.app_data.items if i.stock_qty < i.reorder_level)
        return total, low

    # ---------- Import/Export ----------
    def export_csv(self, file_path: str) -> None:
        self.storage.export_csv(self.app_data, file_path)

    def import_csv(self, file_path: str) -> Dict[str, Any]:
        self.app_data, summary = self.storage.import_csv(self.app_data, file_path)
        # Normalize IDs for any temporary ones
        used = {i.id for i in self.app_data.items}
        for it in self.app_data.items:
            if it.id.startswith("SKU-TEMP-"):
                new_id = self._unique_generated_sku_not_in(used)
                used.add(new_id)
                old_id = it.id
                it.id = new_id
                # Update any transactions that reference this id
                for tx in self.app_data.transactions:
                    if tx.sku == old_id:
                        tx.sku = new_id
        self.save()
        return summary

    def _unique_generated_sku_not_in(self, used: set) -> str:
        # Generate next available SKU not in used
        pattern = re.compile(r"^SKU-(\d{4,})$")
        max_num = 0
        for s in used:
            m = pattern.match(s)
            if m:
                max_num = max(max_num, int(m.group(1)))
        n = max_num + 1
        while True:
            cand = f"SKU-{n:04d}"
            if cand not in used:
                return cand
            n += 1

    # ---------- Settings ----------
    def update_settings(self, categories: List[str], low_stock_inclusive: bool, csv_delimiter: str) -> None:
        cats = [c.strip() for c in categories if c.strip()]
        if not cats:
            cats = ["Ingredient", "Beverage", "Packaging", "Other"]
        delim = (csv_delimiter or ",").strip()
        if len(delim) != 1:
            delim = ","
        self.app_data.settings.categories = cats
        self.app_data.settings.low_stock_inclusive = bool(low_stock_inclusive)
        self.app_data.settings.csv_delimiter = delim
        self.save()

    # ---------- Undo ----------
    def undo_last_action(self) -> bool:
        backups_dir = os.path.join(self.storage.app_root, "backups")
        if not os.path.isdir(backups_dir):
            return False
        files = [os.path.join(backups_dir, f) for f in os.listdir(backups_dir) if f.startswith("items_") and f.endswith(".json")]
        if not files:
            return False
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        latest = files[0]
        target = os.path.join(self.storage.app_root, "items.json")
        try:
            with open(latest, "r", encoding="utf-8") as f:
                content = f.read()
            from utils import atomic_write_text
            atomic_write_text(target, content)
            self.app_data = self.storage.load()
            return True
        except Exception:
            return False

    # ---------- Helpers ----------
    def _get_item_or_raise(self, item_id: str) -> Item:
        for it in self.app_data.items:
            if it.id == item_id:
                return it
        raise ValueError("Item not found")

    def _find_item_index(self, item_id: str) -> int:
        for idx, it in enumerate(self.app_data.items):
            if it.id == item_id:
                return idx
        return -1

    @staticmethod
    def _to_float_or_none(v: Any) -> Optional[float]:
        if v is None or v == "":
            return None
        return float(v)

    @staticmethod
    def _to_int_or_default(v: Any, default: int) -> int:
        if v is None or v == "":
            return default
        return int(v)
