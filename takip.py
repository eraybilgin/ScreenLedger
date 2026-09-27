"""Windows otomatik başlangıcı için sabit konumlu giriş dosyası."""

import runpy
import sys
from pathlib import Path


if __name__ == "__main__":
    uygulama = Path(__file__).resolve().parent / "app"
    sys.path.insert(0, str(uygulama))
    runpy.run_path(str(uygulama / "takip.py"), run_name="__main__")
