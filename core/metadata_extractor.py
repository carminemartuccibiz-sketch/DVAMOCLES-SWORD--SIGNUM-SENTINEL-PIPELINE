# core/metadata_extractor.py

import os
import json
import subprocess
from pathlib import Path
from PIL import Image

EXIFTOOL_PATH = Path("config/exiftool.exe")  # ← posizione corretta

VALID_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr"}

# -------------------------
# EXIFTOOL
# -------------------------
def extract_with_exiftool(file_path):
    try:
        result = subprocess.run(
            ["exiftool", "-j", file_path],   # ← QUI
            capture_output=True,
            text=True
        )

        if not result.stdout:
            return None

        data = json.loads(result.stdout)[0]

        return {
            "metadata_raw": data,
            "source": "exiftool"
        }

    except Exception:
        return None

# -------------------------
# PILLOW FALLBACK
# -------------------------
def extract_with_pillow(file_path: str):
    try:
        with Image.open(file_path) as img:
            return {
                "resolution": {
                    "width": img.width,
                    "height": img.height
                },
                "mode": img.mode,
                "format": img.format,
                "channels": len(img.getbands()),
                "has_alpha": "A" in img.getbands(),
                "source": "pillow"
            }
    except Exception as e:
        return {"error": str(e), "source": "error"}

# -------------------------
# MAIN API
# -------------------------
def extract_metadata(file_path: str) -> dict:
    data = extract_with_exiftool(file_path)
    if data:
        return data

    return extract_with_pillow(file_path)