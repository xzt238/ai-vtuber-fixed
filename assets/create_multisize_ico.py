#!/usr/bin/env python3
"""
Create a multi-size ICO file from a PNG image.
Supports 16x16, 32x32, 48x48, 64x64, 128x128, 256x256 sizes.
"""

import struct
import zlib
from PIL import Image
import io

def create_ico_from_png(png_path, ico_path):
    """Create a multi-size ICO file from a PNG image."""

    # Open the source image
    img = Image.open(png_path)
    img = img.convert('RGBA')

    # Define sizes for the ICO file
    sizes = [16, 32, 48, 64, 128, 256]

    # Store all icon images
    icon_images = []

    for size in sizes:
        # Resize image
        resized = img.resize((size, size), Image.Resampling.LANCZOS)

        # Convert to PNG format in memory
        png_buffer = io.BytesIO()
        resized.save(png_buffer, 'PNG')
        png_data = png_buffer.getvalue()
        png_buffer.close()

        icon_images.append((size, png_data))

    # Write ICO file
    with open(ico_path, 'wb') as f:
        # ICO header
        f.write(struct.pack('<HHH', 0, 1, len(icon_images)))  # Reserved, Type, Count

        # Directory entries
        data_offset = 6 + len(icon_images) * 16  # Header + directory entries
        directory_entries = []

        for size, png_data in icon_images:
            # ICO directory entry
            width = size if size < 256 else 0  # 0 means 256
            height = size if size < 256 else 0
            color_palette = 0  # No color palette
            reserved = 0
            color_planes = 1  # Must be 1 for PNG
            bits_per_pixel = 32  # RGBA
            data_size = len(png_data)
            data_offset_bytes = data_offset

            entry = struct.pack('<BBBBHHII',
                             width, height, color_palette, reserved,
                             color_planes, bits_per_pixel,
                             data_size, data_offset_bytes)
            f.write(entry)

            data_offset += data_size
            directory_entries.append((png_data, data_offset_bytes))

        # Write image data
        for png_data, _ in directory_entries:
            f.write(png_data)

    print(f"✓ Created multi-size ICO: {ico_path}")
    print(f"  Sizes: {', '.join(str(s) + 'x' + str(s) for s in sizes)}")

if __name__ == '__main__':
    png_path = 'gugugaga_logo.png'
    ico_path = 'gugugaga_logo.ico'

    create_ico_from_png(png_path, ico_path)
