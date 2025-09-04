import os
import customtkinter as ctk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional

from services import Services
from models import Item
from utils import APP_NAME, APP_VERSION, get_app_root, open_folder, copy_to_clipboard, format_exception
from dialogs import ItemDialog, StockDialog, AdjustDialog, SettingsDialog, HelpDialog


class CafeStockTrackerApp:
    def __init__(self, services: Services, logger):
        self.services = services
        self.logger = logger
        self.app_root = services.storage.app_root
        
        # Set appearance mode and color theme
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title(f"Kafe Stok Takip v{APP_VERSION}")
        self.root.geometry("1200x700")
        
        # Variables
        self.search_var = ctk.StringVar()
        self.category_var = ctk.StringVar(value="Tümü")
        self.low_stock_var = ctk.BooleanVar()
        
        self.setup_ui()
        self.refresh_table()
        
    def setup_ui(self):
        # Main frame
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top controls frame
        controls_frame = ctk.CTkFrame(main_frame)
        controls_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Search and filters
        ctk.CTkLabel(controls_frame, text="Ara:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        search_entry = ctk.CTkEntry(controls_frame, textvariable=self.search_var, width=200)
        search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        search_entry.bind("<KeyRelease>", lambda e: self.refresh_table())
        
        ctk.CTkLabel(controls_frame, text="Kategori:").grid(row=0, column=2, padx=(20, 5), pady=5, sticky="w")
        self.category_combo = ctk.CTkComboBox(controls_frame, variable=self.category_var, width=150)
        self.category_combo.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.category_combo.configure(command=self.refresh_table)
        
        self.low_stock_check = ctk.CTkCheckBox(controls_frame, text="Düşük Stok Göster", variable=self.low_stock_var, command=self.refresh_table)
        self.low_stock_check.grid(row=0, column=4, padx=20, pady=5, sticky="w")
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x", padx=10, pady=5)
        
        # Button row 1
        ctk.CTkButton(buttons_frame, text="Ürün Ekle", command=self.add_item, width=100).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkButton(buttons_frame, text="Düzenle", command=self.edit_item, width=100).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(buttons_frame, text="Sil", command=self.delete_item, width=100).grid(row=0, column=2, padx=5, pady=5)
        ctk.CTkButton(buttons_frame, text="Stok Girişi", command=self.stock_in, width=100).grid(row=0, column=3, padx=5, pady=5)
        ctk.CTkButton(buttons_frame, text="Stok Çıkışı", command=self.stock_out, width=100).grid(row=0, column=4, padx=5, pady=5)
        ctk.CTkButton(buttons_frame, text="Stok Düzelt", command=self.adjust_stock, width=100).grid(row=0, column=5, padx=5, pady=5)
        
        # Button row 2
        ctk.CTkButton(buttons_frame, text="Ayarlar", command=self.settings, width=100).grid(row=1, column=0, padx=5, pady=5)
        ctk.CTkButton(buttons_frame, text="Yardım/Hakkında", command=self.help_about, width=100).grid(row=1, column=1, padx=5, pady=5)
        
        # Table frame
        table_frame = ctk.CTkFrame(main_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create treeview for the table
        columns = ("SKU", "Ürün Adı", "Kategori", "Birim", "Stok", "Sipariş Seviyesi", "Tedarikçi", "Son Güncelleme")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, minwidth=80)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Status bar
        self.status_label = ctk.CTkLabel(main_frame, text="", height=30)
        self.status_label.pack(fill="x", padx=10, pady=(5, 10))
        
        # Update categories
        self.update_categories()
        
    def update_categories(self):
        categories = ["Tümü"] + self.services.app_data.settings.categories
        self.category_combo.configure(values=categories)
        if not self.category_var.get() or self.category_var.get() not in categories:
            self.category_var.set("Tümü")
    
    def refresh_table(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get filtered items
        query = self.search_var.get()
        category = self.category_var.get()
        low_only = self.low_stock_var.get()
        
        items = self.services.search_items(query, category, low_only)
        
        # Add items to table
        for item in items:
            self.tree.insert("", "end", values=(
                item.id,
                item.name,
                item.category,
                item.unit,
                item.stock_qty,
                item.reorder_level,
                item.supplier or "",
                item.last_updated
            ))
        
        # Update status
        total, low_count = self.services.counts()
        self.status_label.configure(text=f"Ürünler: {total} | Düşük Stok: {low_count} | Veri: {os.path.join(self.app_root, 'items.json')}")
    
    def get_selected_item_id(self):
        selection = self.tree.selection()
        if not selection:
            return None
        item = self.tree.item(selection[0])
        return item['values'][0]  # SKU is first column
    
    def add_item(self):
        dialog = ItemDialog(self.root, self.services, "Ürün Ekle")
        if dialog.result:
            self.refresh_table()
            messagebox.showinfo("Başarılı", "Ürün başarıyla eklendi!")
    
    def edit_item(self):
        item_id = self.get_selected_item_id()
        if not item_id:
            messagebox.showwarning("Uyarı", "Düzenlemek için bir ürün seçin.")
            return
        
        item = next(i for i in self.services.app_data.items if i.id == item_id)
        dialog = ItemDialog(self.root, self.services, "Ürün Düzenle", item)
        if dialog.result:
            self.refresh_table()
            messagebox.showinfo("Başarılı", "Ürün başarıyla güncellendi!")
    
    def delete_item(self):
        item_id = self.get_selected_item_id()
        if not item_id:
            messagebox.showwarning("Uyarı", "Silmek için bir ürün seçin.")
            return
        
        has_tx = any(tx.sku == item_id for tx in self.services.app_data.transactions)
        if has_tx:
            if not messagebox.askyesno("Silme Onayı", 
                                     "Bu ürünün işlemleri var. Ürünü ve ilgili işlemleri silmek istiyor musunuz? Bu işlem geri alınamaz."):
                return
            confirm = True
        else:
            if not messagebox.askyesno("Silme Onayı", "Bu ürünü silmek istiyor musunuz?"):
                return
            confirm = False
        
        try:
            self.services.delete_item(item_id, confirm_delete_transactions=confirm)
            self.refresh_table()
            messagebox.showinfo("Başarılı", "Ürün başarıyla silindi!")
        except Exception as e:
            self.show_error(e)
    
    def stock_in(self):
        item_id = self.get_selected_item_id()
        if not item_id:
            messagebox.showwarning("Uyarı", "Lütfen bir ürün seçin.")
            return
        
        dialog = StockDialog(self.root, self.services, item_id, "in")
        if dialog.result:
            self.refresh_table()
            messagebox.showinfo("Başarılı", "Stok başarıyla güncellendi!")
    
    def stock_out(self):
        item_id = self.get_selected_item_id()
        if not item_id:
            messagebox.showwarning("Uyarı", "Lütfen bir ürün seçin.")
            return
        
        dialog = StockDialog(self.root, self.services, item_id, "out")
        if dialog.result:
            self.refresh_table()
            messagebox.showinfo("Başarılı", "Stok başarıyla güncellendi!")
    
    def adjust_stock(self):
        item_id = self.get_selected_item_id()
        if not item_id:
            messagebox.showwarning("Uyarı", "Lütfen bir ürün seçin.")
            return
        
        dialog = AdjustDialog(self.root, self.services, item_id)
        if dialog.result:
            self.refresh_table()
            messagebox.showinfo("Başarılı", "Stok başarıyla düzeltildi!")
    
    
    def settings(self):
        dialog = SettingsDialog(self.root, self.services)
        if dialog.result:
            self.update_categories()
            self.refresh_table()
    
    def help_about(self):
        dialog = HelpDialog(self.root, self.app_root)
    
    def show_error(self, e: Exception):
        details = format_exception(e)
        error_window = ctk.CTkToplevel(self.root)
        error_window.title("Hata")
        error_window.geometry("600x400")
        
        ctk.CTkLabel(error_window, text="Bir hata oluştu:").pack(pady=10)
        
        text_widget = ctk.CTkTextbox(error_window, width=550, height=250)
        text_widget.pack(pady=10, padx=10, fill="both", expand=True)
        text_widget.insert("1.0", str(e))
        text_widget.configure(state="disabled")
        
        button_frame = ctk.CTkFrame(error_window)
        button_frame.pack(pady=10)
        
        ctk.CTkButton(button_frame, text="Detayları Kopyala", command=lambda: copy_to_clipboard(details)).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Kapat", command=error_window.destroy).pack(side="left", padx=5)
    
    def run(self):
        self.root.mainloop()


# Dialog classes will be added in the next part...
def run_ui(services: Services, logger):
    app = CafeStockTrackerApp(services, logger)
    app.run()
