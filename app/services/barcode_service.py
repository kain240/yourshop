import os
import barcode
from barcode.writer import ImageWriter
from flask import current_app


def generate_barcode(barcode_value: str, product_name: str = '') -> str:
    """
    Generate a barcode PNG image and return its file path.
    Supports EAN-13 (13 digits), CODE128 (everything else).
    """
    upload_folder = current_app.config['UPLOAD_FOLDER']
    barcode_folder = os.path.join(upload_folder, 'barcodes')
    os.makedirs(barcode_folder, exist_ok=True)

    safe_value = barcode_value.replace('/', '_').replace('\\', '_')
    output_path = os.path.join(barcode_folder, safe_value)

    # Choose barcode format
    digits_only = barcode_value.replace(' ', '').isdigit()
    if digits_only and len(barcode_value) == 13:
        bc_class = barcode.get_barcode_class('ean13')
    elif digits_only and len(barcode_value) == 8:
        bc_class = barcode.get_barcode_class('ean8')
    else:
        bc_class = barcode.get_barcode_class('code128')

    writer_options = {
        'module_height': 15.0,
        'module_width': 0.8,
        'quiet_zone': 6.5,
        'font_size': 10,
        'text_distance': 5.0,
        'write_text': True,
    }

    writer = ImageWriter()
    bc = bc_class(barcode_value, writer=writer)
    saved_path = bc.save(output_path, options=writer_options)
    return saved_path  # returns path with .png extension
