# Kafe Stok Takip (Cafe Stock Tracker)

Modern, offline-first desktop inventory management app for cafes and restaurants. Built with Python 3.11 and CustomTkinter with a beautiful Turkish interface. Stores all data in a local JSON file with automatic backups.

## ✨ Features

### 🎯 Core Functionality
- **CRUD Operations**: Add, edit, delete inventory items with validation
- **Stock Management**: Stock in/out/adjust with transaction history
- **Search & Filter**: Search by name/SKU/supplier, filter by category, low stock toggle
- **Turkish Interface**: Complete Turkish localization for Turkish users
- **Customizable Categories**: Add your own product categories
- **Smart Units**: Predefined Turkish units (adet, kg, litre, paket, etc.)

### 🔧 Technical Features
- **Modern UI**: Beautiful CustomTkinter interface with rounded corners
- **Offline-First**: All data stored locally in `items.json`
- **Automatic Backups**: Rotating backup system (keeps last 20 backups)
- **Single Instance**: Prevents multiple app instances from running
- **Logging**: Comprehensive logging to `logs/app.log`
- **Data Validation**: Robust validation for all inputs

## 🚀 Quick Start

### Using uv (Recommended)
```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv -p 3.11
source .venv/bin/activate  # macOS/Linux
# Windows: .venv\Scripts\activate

# Install dependencies
uv pip install .

# Run the app
python src/main.py
```

### Using pip (Alternative)
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

## 🎨 Interface Overview

### Main Window
- **Search Bar**: "Ara" - Search items by name, SKU, or supplier
- **Category Filter**: "Kategori" - Filter by product categories
- **Low Stock Toggle**: "Düşük Stok Göster" - Show only low stock items

### Action Buttons
- **Ürün Ekle**: Add new inventory items
- **Düzenle**: Edit existing items
- **Sil**: Delete items (with confirmation)
- **Stok Girişi**: Record stock incoming
- **Stok Çıkışı**: Record stock outgoing
- **Stok Düzelt**: Adjust stock quantities
- **Ayarlar**: Configure categories and settings
- **Yardım/Hakkında**: Help and about information

### Data Table
- **SKU**: Product identifier
- **Ürün Adı**: Product name
- **Kategori**: Category
- **Birim**: Unit of measurement
- **Stok**: Current stock quantity
- **Sipariş Seviyesi**: Reorder level
- **Tedarikçi**: Supplier
- **Son Güncelleme**: Last updated

## ⚙️ Settings & Customization

### Categories
- **Default Categories**: Malzeme, İçecek, Ambalaj, Diğer
- **Custom Categories**: Add your own categories in Settings
- **Examples**: Temizlik, Ofis Malzemeleri, Kahve, Çay, Tatlı, Atıştırmalık

### Units
Predefined Turkish units for easy selection:
- **Weight**: kg, gram
- **Volume**: litre, ml
- **Count**: adet, paket, kutu, şişe
- **Tableware**: bardak, tabak, çatal, kaşık, bıçak
- **Disposables**: peçete, poşet

## 📁 Data Management

### File Structure
```
stockTracker/
├── src/                    # Source code
│   ├── main.py            # Application entry point
│   ├── ui.py              # Main UI (CustomTkinter)
│   ├── dialogs.py         # Dialog windows
│   ├── models.py          # Data models
│   ├── services.py        # Business logic
│   ├── storage.py         # Data persistence
│   └── utils.py           # Utilities
├── tests/                 # Test files
├── backups/               # Automatic backups
├── logs/                  # Application logs
├── items.json             # Main data file
└── app.lock              # Single instance lock
```

### Backups
- **Automatic**: Created before every save operation
- **Location**: `backups/items_YYYYMMDD_HHMMSS.json`
- **Retention**: Keeps last 20 backups
- **Restore**: Copy backup over `items.json` and restart app

## 🔧 Build Executables

### macOS
```bash
# Install build dependencies
uv pip install .[dev]

# Create app bundle (recommended)
pyinstaller --windowed --name "KafeStokTakip" --icon assets/icon.icns src/main.py

# Create single binary
pyinstaller --onefile --windowed --name "KafeStokTakip" --icon assets/icon.icns src/main.py
```

### Windows
```bash
uv pip install .[dev]
pyinstaller --onefile --noconsole --name "KafeStokTakip" --icon assets/icon.ico src/main.py
```

## 🧪 Testing
```bash
uv pip install .[dev]
pytest -q
```

## 🐛 Troubleshooting

### Common Issues
- **Another instance running**: Delete `app.lock` if no other instance is open
- **Import errors**: Use clean virtual environment with `uv venv`
- **UI not loading**: Check `logs/app.log` for error details

### Logs
- **Location**: `logs/app.log`
- **Level**: INFO by default
- **Rotation**: Automatic log rotation

## 📋 Requirements

- **Python**: 3.11 or higher
- **Dependencies**: CustomTkinter, standard library modules
- **OS**: macOS, Windows, Linux
- **Storage**: ~50MB for app + data

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - feel free to use, modify, and distribute.

## 🙏 Acknowledgments

- Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the modern UI
- Designed specifically for Turkish cafe and restaurant owners
- Inspired by the need for simple, offline inventory management

---

**Made with ❤️ for Turkish cafe owners**