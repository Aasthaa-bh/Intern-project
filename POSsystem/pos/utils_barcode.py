import os
import re
from barcode import Code128
from barcode.writer import ImageWriter
from django.conf import settings


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "")
    return value.strip("._-") or "barcode"


def generate_barcode_image(barcode_text, file_name):
    """
    Generate a barcode PNG inside MEDIA_ROOT/barcodes/
    and return its relative media path like:
    'barcodes/variant_1_CLTH-000001.png'
    """
    barcode_dir = os.path.join(settings.MEDIA_ROOT, "barcodes")
    os.makedirs(barcode_dir, exist_ok=True)

    safe_name = _safe_filename(file_name)
    file_path_without_ext = os.path.join(barcode_dir, safe_name)

    barcode_obj = Code128(str(barcode_text), writer=ImageWriter())
    saved_path = barcode_obj.save(file_path_without_ext)

    return os.path.relpath(saved_path, settings.MEDIA_ROOT).replace("\\", "/")


def delete_barcode_file(relative_path):
    """
    Delete old barcode file if it exists.
    """
    if not relative_path:
        return

    absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    if os.path.exists(absolute_path):
        os.remove(absolute_path)