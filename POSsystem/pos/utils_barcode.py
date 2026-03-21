import os
from barcode import Code128
from barcode.writer import ImageWriter
from django.conf import settings


def generate_barcode_image(barcode_text, file_name):
    """
    Generates a barcode PNG image and saves it inside media/barcodes/
    Returns relative file path.
    """
    barcode_dir = os.path.join(settings.MEDIA_ROOT, "barcodes")
    os.makedirs(barcode_dir, exist_ok=True)

    file_path = os.path.join(barcode_dir, file_name)

    barcode_obj = Code128(barcode_text, writer=ImageWriter())
    saved_path = barcode_obj.save(file_path)

    # Return relative media path
    return os.path.relpath(saved_path, settings.MEDIA_ROOT).replace("\\", "/")