import os
import logging
import tempfile
import shutil

from src.storage import Storage
from src.services import Services


def make_services():
    root = tempfile.mkdtemp(prefix='cafestock_services_')
    logger = logging.getLogger('t')
    storage = Storage(root, logger)
    storage.ensure_initial_files()
    services = Services(storage, logger)
    return root, services


def cleanup(root):
    shutil.rmtree(root)


def test_sku_generation_and_crud():
    root, s = make_services()
    try:
        it = s.add_item({'name': 'Milk', 'category': 'Ingredient', 'unit': 'L', 'stock_qty': 0})
        assert it.id.startswith('SKU-')
        it2 = s.update_item(it.id, {'reorder_level': 5})
        assert it2.reorder_level == 5
        # name uniqueness
        s.add_item({'name': 'Sugar', 'category': 'Ingredient', 'unit': 'kg', 'stock_qty': 1})
        try:
            s.add_item({'name': 'sugar', 'category': 'Ingredient', 'unit': 'kg', 'stock_qty': 1})
            assert False, 'should fail'
        except Exception:
            pass
        # delete
        s.delete_item(it.id, confirm_delete_transactions=True)
        assert all(x.id != it.id for x in s.app_data.items)
    finally:
        cleanup(root)


def test_stock_ops_and_negative_prevention():
    root, s = make_services()
    try:
        it = s.add_item({'name': 'Cups', 'category': 'Packaging', 'unit': 'piece', 'stock_qty': 10})
        s.stock_in(it.id, 5, reason='Purchase')
        assert s._get_item_or_raise(it.id).stock_qty == 15
        s.stock_out(it.id, 4, reason='Sale')
        assert s._get_item_or_raise(it.id).stock_qty == 11
        try:
            s.stock_out(it.id, 100)
            assert False, 'should fail negative'
        except Exception:
            pass
        s.stock_adjust(it.id, 20, mode='set')
        assert s._get_item_or_raise(it.id).stock_qty == 20
        try:
            s.stock_adjust(it.id, -30, mode='delta')
            assert False, 'should fail below zero'
        except Exception:
            pass
    finally:
        cleanup(root)


def test_import_upsert_behavior():
    root, s = make_services()
    try:
        it = s.add_item({'name': 'Beans', 'category': 'Ingredient', 'unit': 'bag', 'stock_qty': 2})
        # create a CSV
        csv_path = os.path.join(root, 'imp.csv')
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write('id,name,category,unit,unit_cost,unit_price,stock_qty,reorder_level,supplier,barcode,notes\n')
            f.write(f'{it.id},Beans,Ingredient,bag,,,5,0,,,\n')  # update existing
            f.write(',Milk,Ingredient,L,,,3,0,,,\n')  # new by name
        summary = s.import_csv(csv_path)
        assert summary['updated'] >= 1 and summary['added'] >= 1
    finally:
        cleanup(root)
