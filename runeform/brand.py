"""Brand kit persistence — zip export/import.

A brand kit zip contains:
  brand.json   — BrandKit metadata (name, address, colors, description, logo_filename)
  logo.*       — Logo image file (if provided)
"""

import json
import zipfile
from io import BytesIO
from pathlib import Path

from .models import BrandKit

BRAND_DIR = Path(__file__).parent.parent / "brand_data"


def export_zip(brand: BrandKit, logo_path: Path | None = None) -> BytesIO:
    """Export a brand kit as a zip file in memory."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("brand.json", brand.model_dump_json(indent=2))
        if logo_path and logo_path.exists():
            zf.write(logo_path, f"logo{logo_path.suffix}")
    buf.seek(0)
    return buf


def import_zip(zip_bytes: bytes) -> tuple[BrandKit, Path | None]:
    """Import a brand kit from zip bytes. Returns (brand, logo_path_or_none)."""
    BRAND_DIR.mkdir(exist_ok=True)

    buf = BytesIO(zip_bytes)
    logo_path = None

    with zipfile.ZipFile(buf, "r") as zf:
        brand_json = zf.read("brand.json")
        brand = BrandKit.model_validate_json(brand_json)

        for name in zf.namelist():
            if name.startswith("logo"):
                logo_data = zf.read(name)
                logo_path = BRAND_DIR / name
                logo_path.write_bytes(logo_data)
                brand.logo_filename = name

    return brand, logo_path


def save_brand(brand: BrandKit, logo_path: Path | None = None) -> Path:
    """Save brand kit to disk (brand_data/ directory)."""
    BRAND_DIR.mkdir(exist_ok=True)

    if logo_path and logo_path.exists():
        dest = BRAND_DIR / f"logo{logo_path.suffix}"
        if dest != logo_path:
            dest.write_bytes(logo_path.read_bytes())
        brand.logo_filename = dest.name
    elif not brand.logo_filename:
        # Preserve existing logo if caller didn't set one
        meta_path = BRAND_DIR / "brand.json"
        if meta_path.exists():
            existing = BrandKit.model_validate_json(meta_path.read_text())
            if existing.logo_filename and (BRAND_DIR / existing.logo_filename).exists():
                brand.logo_filename = existing.logo_filename
        # Fall back to scanning for logo files on disk
        if not brand.logo_filename:
            for ext in (".svg", ".png", ".jpg", ".jpeg", ".webp"):
                candidate = BRAND_DIR / f"logo{ext}"
                if candidate.exists():
                    brand.logo_filename = candidate.name
                    break

    meta_path = BRAND_DIR / "brand.json"
    meta_path.write_text(brand.model_dump_json(indent=2))

    return BRAND_DIR


def load_brand() -> tuple[BrandKit, Path | None] | None:
    """Load brand kit from disk. Returns None if not configured."""
    meta_path = BRAND_DIR / "brand.json"
    if not meta_path.exists():
        return None

    brand = BrandKit.model_validate_json(meta_path.read_text())

    logo_path = None
    if brand.logo_filename:
        candidate = BRAND_DIR / brand.logo_filename
        if candidate.exists():
            logo_path = candidate

    return brand, logo_path
