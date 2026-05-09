"""Generate assets/devnex.ico — run once before building the executable.

Usage:
    python generate_icon.py

Requires: PyQt6   (already in requirements.txt)
Optional: Pillow  (pip install pillow)  — produces a proper multi-resolution ICO.
          Without Pillow a single 256-px ICO is saved via Qt.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Make sure the project root is in sys.path so imports work
sys.path.insert(0, str(Path(__file__).parent))

_SIZES = [256, 128, 64, 48, 32, 16]


def _pixmap_to_pil(pixmap):
    """Convert a QPixmap to a PIL Image (RGBA)."""
    from PIL import Image
    from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
    ba  = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buf, "PNG")
    buf.close()
    return Image.open(io.BytesIO(bytes(ba))).convert("RGBA")


def generate() -> None:
    from PyQt6.QtWidgets import QApplication
    from interfaces.gui.icon import make_hex_pixmap

    app = QApplication.instance() or QApplication(sys.argv)

    assets = Path("assets")
    assets.mkdir(exist_ok=True)

    # ── Try Pillow for a proper multi-resolution ICO ───────────────────────────
    try:
        from PIL import Image  # noqa: F401
        use_pillow = True
    except ImportError:
        use_pillow = False
        print("  [WARN] Pillow not installed — single-resolution ICO will be saved.")
        print("         Run  pip install pillow  for a full multi-size ICO.\n")

    if use_pillow:
        print(f"  Rendering {len(_SIZES)} icon sizes: {_SIZES}")
        pil_images = [_pixmap_to_pil(make_hex_pixmap(s)) for s in _SIZES]

        ico_path = assets / "devnex.ico"
        pil_images[0].save(
            ico_path,
            format="ICO",
            sizes=[(s, s) for s in _SIZES],
            append_images=pil_images[1:],
        )
        print(f"  ✓ {ico_path}  ({', '.join(str(s) for s in _SIZES)} px)\n")
    else:
        # Qt single-resolution fallback
        pix = make_hex_pixmap(256)
        ico_path = assets / "devnex.ico"
        ok  = pix.save(str(ico_path), "ICO")
        if ok:
            print(f"  ✓ {ico_path}  (256 px via Qt)\n")
        else:
            # Qt ICO plugin unavailable — save PNG and warn
            ico_path = assets / "devnex.png"
            pix.save(str(ico_path))
            print(f"  ✓ {ico_path}  (PNG — Qt ICO plugin not available)")
            print("  NOTE: PyInstaller needs a real .ico; install Pillow and re-run.\n")

    # Always export PNG previews for README / documentation
    for s in (256, 64, 32):
        png = assets / f"devnex_{s}.png"
        make_hex_pixmap(s).save(str(png))
        print(f"  ✓ {png}")

    print("\nDone.")


if __name__ == "__main__":
    print("\n━━  DevNex Icon Generator  ━━\n")
    generate()
