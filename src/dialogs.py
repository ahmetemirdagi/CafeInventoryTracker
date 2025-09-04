import os
import customtkinter as ctk
from tkinter import messagebox
from typing import Optional

from services import Services
from models import Item
from utils import open_folder


class ItemDialog:
    def __init__(self, parent, services: Services, title: str, item: Item = None):
        self.services = services
        self.result = False
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_ui(item)
        
    def setup_ui(self, item: Item = None):
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Form fields
        fields = [
            ("SKU", "id", item.id if item else self.services.generate_next_sku(), item is not None),
            ("Ürün Adı", "name", item.name if item else "", False),
            ("Kategori", "category", item.category if item else self.services.app_data.settings.categories[0], False),
            ("Birim", "unit", item.unit if item else "adet", False),
            ("Birim Maliyet", "unit_cost", str(item.unit_cost) if item and item.unit_cost else "", False),
            ("Birim Fiyat", "unit_price", str(item.unit_price) if item and item.unit_price else "", False),
            ("Stok Miktarı", "stock_qty", str(item.stock_qty) if item else "0", False),
            ("Sipariş Seviyesi", "reorder_level", str(item.reorder_level) if item else "0", False),
            ("Tedarikçi", "supplier", item.supplier if item else "", False),
            ("Barkod", "barcode", item.barcode if item else "", False),
            ("Notlar", "notes", item.notes if item else "", False),
        ]
        
        self.entries = {}
        for i, (label, key, value, disabled) in enumerate(fields):
            ctk.CTkLabel(main_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            
            if key == "category":
                entry = ctk.CTkComboBox(main_frame, values=self.services.app_data.settings.categories)
                entry.set(value)
            elif key == "unit":
                # Common Turkish units for cafe/restaurant
                units = ["adet", "kg", "gram", "litre", "ml", "paket", "kutu", "şişe", "bardak", "tabak", "çatal", "kaşık", "bıçak", "peçete", "poşet"]
                entry = ctk.CTkComboBox(main_frame, values=units)
                entry.set(value)
            elif key == "notes":
                entry = ctk.CTkTextbox(main_frame, height=60, width=300)
                entry.insert("1.0", value)
            else:
                entry = ctk.CTkEntry(main_frame, width=300)
                entry.insert(0, value)
                if disabled:
                    entry.configure(state="disabled")
            
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            self.entries[key] = entry
        
        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)
        
        ctk.CTkButton(button_frame, text="Kaydet", command=self.save, width=100).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="İptal", command=self.dialog.destroy, width=100).pack(side="left", padx=5)
        
        main_frame.grid_columnconfigure(1, weight=1)
    
    def save(self):
        try:
            data = {}
            for key, entry in self.entries.items():
                if key == "notes":
                    data[key] = entry.get("1.0", "end-1c")
                else:
                    data[key] = entry.get()
            
            if hasattr(self, 'item') and self.item:
                self.services.update_item(data['id'], data)
            else:
                self.services.add_item(data)
            
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Hata", str(e))


class StockDialog:
    def __init__(self, parent, services: Services, item_id: str, mode: str):
        self.services = services
        self.item_id = item_id
        self.mode = mode
        self.result = False
        
        item = next(i for i in services.app_data.items if i.id == item_id)
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(f"Stok {'Girişi' if mode == 'in' else 'Çıkışı'}")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="SKU:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(main_frame, text=item.id).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(main_frame, text="Ürün Adı:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(main_frame, text=item.name).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(main_frame, text="Miktar:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.qty_entry = ctk.CTkEntry(main_frame, width=100)
        self.qty_entry.insert(0, "1")
        self.qty_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(main_frame, text="Sebep:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        reasons = ['Satın Alma', 'Satış', 'Fire', 'Sayım Düzeltmesi', 'Diğer']
        self.reason_combo = ctk.CTkComboBox(main_frame, values=reasons, width=200)
        self.reason_combo.set(reasons[0] if mode == 'in' else reasons[1])
        self.reason_combo.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(main_frame, text="Not:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.note_entry = ctk.CTkEntry(main_frame, width=200)
        self.note_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        ctk.CTkButton(button_frame, text="Kaydet", command=self.save, width=100).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="İptal", command=self.dialog.destroy, width=100).pack(side="left", padx=5)
    
    def save(self):
        try:
            qty = int(self.qty_entry.get())
            reason = self.reason_combo.get()
            note = self.note_entry.get()
            
            if self.mode == 'in':
                self.services.stock_in(self.item_id, qty, reason=reason, note=note)
            else:
                self.services.stock_out(self.item_id, qty, reason=reason, note=note)
            
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Hata", str(e))


class AdjustDialog:
    def __init__(self, parent, services: Services, item_id: str):
        self.services = services
        self.item_id = item_id
        self.result = False
        
        item = next(i for i in services.app_data.items if i.id == item_id)
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Stok Düzelt")
        self.dialog.geometry("400x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="SKU:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(main_frame, text=item.id).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(main_frame, text="Ürün Adı:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(main_frame, text=item.name).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Mode selection
        self.mode_var = ctk.StringVar(value="set")
        ctk.CTkRadioButton(main_frame, text="Değere Ayarla", variable=self.mode_var, value="set").grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        ctk.CTkRadioButton(main_frame, text="Değiştir (fark)", variable=self.mode_var, value="delta").grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(main_frame, text="Miktar:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.qty_entry = ctk.CTkEntry(main_frame, width=100)
        self.qty_entry.insert(0, str(item.stock_qty))
        self.qty_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(main_frame, text="Sebep:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        reasons = ['Sayım Düzeltmesi', 'Fire', 'Diğer']
        self.reason_combo = ctk.CTkComboBox(main_frame, values=reasons, width=200)
        self.reason_combo.set(reasons[0])
        self.reason_combo.grid(row=5, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(main_frame, text="Not:").grid(row=6, column=0, padx=5, pady=5, sticky="w")
        self.note_entry = ctk.CTkEntry(main_frame, width=200)
        self.note_entry.grid(row=6, column=1, padx=5, pady=5, sticky="w")
        
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        ctk.CTkButton(button_frame, text="Kaydet", command=self.save, width=100).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="İptal", command=self.dialog.destroy, width=100).pack(side="left", padx=5)
    
    def save(self):
        try:
            qty = int(self.qty_entry.get())
            mode = self.mode_var.get()
            reason = self.reason_combo.get()
            note = self.note_entry.get()
            
            self.services.stock_adjust(self.item_id, qty, mode=mode, reason=reason, note=note)
            
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Hata", str(e))


class SettingsDialog:
    def __init__(self, parent, services: Services):
        self.services = services
        self.result = False
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Ayarlar")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="Kategoriler (her satıra bir tane, özel kategoriler ekleyebilirsiniz):").pack(pady=(0, 5))
        self.categories_text = ctk.CTkTextbox(main_frame, height=150, width=400)
        self.categories_text.pack(pady=(0, 5), fill="x")
        self.categories_text.insert("1.0", "\n".join(services.app_data.settings.categories))
        
        # Add example text
        example_label = ctk.CTkLabel(main_frame, text="Örnek: Malzeme, İçecek, Ambalaj, Temizlik, Ofis Malzemeleri, Diğer", 
                                   font=ctk.CTkFont(size=12), text_color="gray")
        example_label.pack(pady=(0, 10))
        
        self.inclusive_var = ctk.BooleanVar(value=services.app_data.settings.low_stock_inclusive)
        ctk.CTkCheckBox(main_frame, text="Düşük stok eşiği dahil (<=)", variable=self.inclusive_var).pack(pady=5)
        
        ctk.CTkLabel(main_frame, text="CSV ayırıcı:").pack(pady=(10, 5))
        self.delim_entry = ctk.CTkEntry(main_frame, width=50)
        self.delim_entry.insert(0, services.app_data.settings.csv_delimiter)
        self.delim_entry.pack(pady=(0, 10))
        
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=20)
        
        ctk.CTkButton(button_frame, text="Kaydet", command=self.save, width=100).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="İptal", command=self.dialog.destroy, width=100).pack(side="left", padx=5)
    
    def save(self):
        try:
            categories = [line.strip() for line in self.categories_text.get("1.0", "end-1c").splitlines() if line.strip()]
            inclusive = self.inclusive_var.get()
            delimiter = self.delim_entry.get() or ","
            
            self.services.update_settings(categories, inclusive, delimiter)
            
            self.result = True
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Hata", str(e))


class HelpDialog:
    def __init__(self, parent, app_root: str):
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Hakkında")
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        main_frame = ctk.CTkFrame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text=f"Kafe Stok Takip v1.0.0", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        ctk.CTkLabel(main_frame, text=f"Veri dosyası: {os.path.join(app_root, 'items.json')}").pack(pady=5)
        
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=20)
        
        ctk.CTkButton(button_frame, text="Veri Klasörünü Aç", command=lambda: open_folder(app_root), width=150).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Kapat", command=self.dialog.destroy, width=100).pack(side="left", padx=5)
