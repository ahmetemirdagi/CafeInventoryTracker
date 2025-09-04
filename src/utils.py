import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import tempfile
import traceback
import platform

try:
    import PySimpleGUI as sg  # For clipboard in runtime
except Exception:  # pragma: no cover - tests don't require GUI
    sg = None


APP_NAME = "Cafe Stock Tracker"
APP_VERSION = "1.0.0"


def get_app_root() -> str:
    """Return the directory where data/logs/backups live.

    - Frozen (PyInstaller): folder of the executable
    - Development: project root (parent of src)
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def get_logs_dir(app_root: str) -> str:
    path = os.path.join(app_root, "logs")
    ensure_dir(path)
    return path


def get_backups_dir(app_root: str) -> str:
    path = os.path.join(app_root, "backups")
    ensure_dir(path)
    return path


def get_data_file_path(app_root: str) -> str:
    return os.path.join(app_root, "items.json")


def get_lock_file_path(app_root: str) -> str:
    return os.path.join(app_root, "app.lock")


def setup_logging(app_root: str, level: int = logging.INFO) -> logging.Logger:
    logs_dir = get_logs_dir(app_root)
    log_file = os.path.join(logs_dir, "app.log")

    logger = logging.getLogger("cafestock")
    logger.setLevel(level)
    logger.handlers.clear()

    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    file_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(file_formatter)
    logger.addHandler(console_handler)

    logger.debug("Logging initialized")
    return logger


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_write_text(target_path: str, content: str) -> None:
    dirname = os.path.dirname(target_path)
    ensure_dir(dirname)
    fd, tmp_path = tempfile.mkstemp(dir=dirname, prefix=".tmp_items_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(content)
        os.replace(tmp_path, target_path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


class SingleInstanceLock:
    """Simple single-instance file lock using exclusive creation.

    Creates `app.lock` with the current PID. If the file already exists, raises RuntimeError.
    """

    def __init__(self, app_root: str):
        self.app_root = app_root
        self.lock_path = get_lock_file_path(app_root)
        self.fd = None

    def acquire(self) -> None:
        try:
            # O_EXCL ensures exclusive creation; fails if file exists
            self.fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self.fd, str(os.getpid()).encode("utf-8"))
            os.fsync(self.fd)
        except FileExistsError:
            raise RuntimeError("Another instance appears to be running. If not, delete app.lock.")

    def release(self) -> None:
        try:
            if self.fd is not None:
                try:
                    os.close(self.fd)
                except Exception:
                    pass
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except Exception:
            pass


def copy_to_clipboard(text: str) -> None:
    try:
        if sg is not None:
            sg.clipboard_set(text)
            return
    except Exception:
        pass
    # Fallback using tkinter (not imported at top to avoid GUI deps in tests)
    try:  # pragma: no cover - tests skip GUI
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
    except Exception:
        pass


def open_folder(path: str) -> None:
    try:
        system = platform.system()
        if system == "Windows":  # pragma: no cover (CI may not be Windows)
            os.startfile(path)
        elif system == "Darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception:
        pass


def format_exception(e: BaseException) -> str:
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))
