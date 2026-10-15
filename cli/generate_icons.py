#!/usr/bin/env python3
"""
Genera icon.ico e icon.png a partir del logo de Kognito AI para Windows y Linux.
"""
import os
from PIL import Image

def generate_icons():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    src_logo = os.path.join(project_root, "public", "kognito-labs-logo.png")

    if not os.path.exists(src_logo):
        print(f"Error: No se encontró el logo en {src_logo}")
        return

    im = Image.open(src_logo).convert("RGBA")
    
    # icon.png (256x256)
    png_path = os.path.join(base_dir, "icon.png")
    im.resize((256, 256), Image.Resampling.LANCZOS).save(png_path, format="PNG")
    print(f"Generado: {png_path}")

    # icon.ico multi-resolución para Windows
    ico_path = os.path.join(base_dir, "icon.ico")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    im.save(ico_path, format="ICO", sizes=sizes)
    print(f"Generado: {ico_path}")

if __name__ == "__main__":
    generate_icons()
