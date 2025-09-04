import sys
import logging
import os

# Add src directory to path for PyInstaller
if getattr(sys, 'frozen', False):
    # Running as PyInstaller executable
    src_dir = os.path.join(os.path.dirname(sys.executable), 'src')
else:
    # Running as script
    src_dir = os.path.dirname(__file__)

sys.path.insert(0, src_dir)

from utils import get_app_root, setup_logging, SingleInstanceLock
from storage import Storage
from services import Services
from ui import run_ui


def main():
    app_root = get_app_root()
    logger = setup_logging(app_root, level=logging.INFO)
    lock = SingleInstanceLock(app_root)
    try:
        lock.acquire()
        storage = Storage(app_root, logger)
        storage.ensure_initial_files()
        services = Services(storage, logger)
        run_ui(services, logger)
    finally:
        lock.release()


if __name__ == '__main__':
    main()
