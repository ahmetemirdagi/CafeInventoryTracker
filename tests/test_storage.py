import os
import json
import tempfile
import shutil
import logging

from src.storage import Storage
from src.models import AppData


def make_tmp_root():
    d = tempfile.mkdtemp(prefix='cafestock_tests_')
    os.makedirs(os.path.join(d, 'backups'), exist_ok=True)
    os.makedirs(os.path.join(d, 'logs'), exist_ok=True)
    return d


def test_initial_create_and_load():
    root = make_tmp_root()
    try:
        storage = Storage(root, logging.getLogger('t'))
        storage.ensure_initial_files()
        data = storage.load()
        assert isinstance(data, AppData)
        path = os.path.join(root, 'items.json')
        assert os.path.exists(path)
    finally:
        shutil.rmtree(root)


def test_backup_and_rotation():
    root = make_tmp_root()
    try:
        storage = Storage(root, logging.getLogger('t'))
        storage.ensure_initial_files()
        data = storage.load()
        # write many backups
        for _ in range(25):
            storage.save(data)
        backups = [f for f in os.listdir(os.path.join(root, 'backups')) if f.endswith('.json')]
        assert len(backups) <= 20
    finally:
        shutil.rmtree(root)


def test_export_import_roundtrip():
    root = make_tmp_root()
    try:
        storage = Storage(root, logging.getLogger('t'))
        storage.ensure_initial_files()
        data = storage.load()
        # add one item
        from src.models import Item
        data.items.append(Item(id='SKU-0001', name='Espresso Beans 1kg', category='Ingredient', unit='bag', stock_qty=8, reorder_level=3, last_updated='2025-09-01T12:00:00Z'))
        storage.save(data)
        csv_path = os.path.join(root, 'export.csv')
        storage.export_csv(data, csv_path)
        assert os.path.exists(csv_path)
        # import modifies name
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read().replace('Espresso Beans 1kg', 'Espresso Beans 1kg X')
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(content)
        data2 = storage.load()
        data2, summary = storage.import_csv(data2, csv_path)
        assert summary['updated'] >= 1
    finally:
        shutil.rmtree(root)
