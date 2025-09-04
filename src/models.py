from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum


class TransactionType(str, Enum):
    IN = "in"
    OUT = "out"
    ADJUST = "adjust"


@dataclass
class Item:
    id: str
    name: str
    category: str
    unit: str
    unit_cost: Optional[float] = None
    unit_price: Optional[float] = None
    stock_qty: int = 0
    reorder_level: int = 0
    supplier: Optional[str] = None
    barcode: Optional[str] = None
    notes: Optional[str] = None
    last_updated: str = ""

    def validate(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Name is required")
        if not isinstance(self.stock_qty, int) or self.stock_qty < 0:
            raise ValueError("stock_qty must be an integer >= 0")
        if not isinstance(self.reorder_level, int) or self.reorder_level < 0:
            raise ValueError("reorder_level must be an integer >= 0")
        if self.unit_cost is not None and self.unit_cost < 0:
            raise ValueError("unit_cost must be >= 0")
        if self.unit_price is not None and self.unit_price < 0:
            raise ValueError("unit_price must be >= 0")


@dataclass
class Transaction:
    id: str
    type: TransactionType
    sku: str
    qty: int
    timestamp: str
    reason: str
    note: Optional[str] = None

    def validate(self) -> None:
        if self.qty is None or not isinstance(self.qty, int) or self.qty <= 0:
            raise ValueError("qty must be an integer > 0")


@dataclass
class Settings:
    categories: List[str] = field(default_factory=lambda: ["Malzeme", "İçecek", "Ambalaj", "Diğer"])
    low_stock_inclusive: bool = True  # True: <=, False: <
    csv_delimiter: str = ","


@dataclass
class AppData:
    version: int = 1
    items: List[Item] = field(default_factory=list)
    transactions: List[Transaction] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "items": [asdict(i) for i in self.items],
            "transactions": [
                {
                    **asdict(t),
                    "type": t.type.value,
                }
                for t in self.transactions
            ],
            "settings": asdict(self.settings),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AppData":
        items_raw = data.get("items", [])
        transactions_raw = data.get("transactions", [])
        settings_raw = data.get("settings", {})
        items = [Item(**i) for i in items_raw]
        txs = [
            Transaction(
                id=t["id"],
                type=TransactionType(t["type"]),
                sku=t["sku"],
                qty=int(t["qty"]),
                timestamp=t["timestamp"],
                reason=t.get("reason", ""),
                note=t.get("note"),
            )
            for t in transactions_raw
        ]
        settings = Settings(**settings_raw) if settings_raw else Settings()
        app = AppData(version=int(data.get("version", 1)), items=items, transactions=txs, settings=settings)
        return app
