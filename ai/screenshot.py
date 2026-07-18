from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path


def capture_screenshot() -> Path:
    try:
        from PIL import ImageGrab
    except Exception as exc:
        raise RuntimeError("Pillow is required for screenshots. Install requirements.txt.") from exc

    target = Path(tempfile.gettempdir()) / f"RiftShell_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    try:
        image = ImageGrab.grab(all_screens=True)
    except TypeError:
        image = ImageGrab.grab()

    image.save(target)
    return target

