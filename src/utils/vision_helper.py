import base64
import os

def encode_image(image_path):
    """Encodes a local image file to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def is_image_file(filename):
    """Checks if a file is a supported image."""
    return filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))