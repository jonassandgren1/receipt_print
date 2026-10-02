#!/usr/bin/env python3
"""
02_test_graphics.py - Testar bildbehandling och grafikutskrift på POS58-01.

Krav:
  - Max 384 pixlars bredd (exakt radbredd för 58 mm / 203 DPI)
  - 1-bits monokrom konvertering med Floyd-Steinberg dithering
"""

import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from escpos.printer import Usb


def create_sample_logo(filename="sample_logo.png", width=384, height=140):
    """Skapar en snygg demonstrationsbild i exakt 384 pixlars bredd."""
    # Skapa RGB-bild med vit bakgrund
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    # Rita en dekorativ ram
    draw.rectangle([(4, 4), (width - 5, height - 5)], outline="black", width=3)
    draw.rectangle([(8, 8), (width - 9, height - 9)], outline="black", width=1)

    # Rita en liten cirkelsymbol / stjärna i mitten
    center_x = width // 2
    draw.ellipse([(center_x - 18, 16), (center_x + 18, 52)], fill="black")
    draw.ellipse([(center_x - 10, 24), (center_x + 10, 44)], fill="white")

    # Text
    draw.text((center_x, 70), "POS58 GRAFIKTEST", fill="black", anchor="mm")
    draw.text((center_x, 92), "Floyd-Steinberg Dithering", fill="black", anchor="mm")
    draw.text((center_x, 114), "384 px Monokrom Raster", fill="black", anchor="mm")

    # Rita små dekorativa hörn
    draw.polygon([(14, 14), (28, 14), (14, 28)], fill="black")
    draw.polygon([(width - 15, 14), (width - 29, 14), (width - 15, 28)], fill="black")
    draw.polygon([(14, height - 15), (28, height - 15), (14, height - 29)], fill="black")
    draw.polygon([(width - 15, height - 15), (width - 29, height - 15), (width - 15, height - 29)], fill="black")

    img.save(filename)
    print(f"[*] Skapade testbild: {filename} ({width}x{height} px)")
    return filename


def prepare_image_for_pos58(image_path, target_width=384):
    """
    Öppnar en bild, skalar om till 384 px med bevarat bildförhållande,
    och konverterar till 1-bit monokrom med Floyd-Steinberg dithering.
    """
    with Image.open(image_path) as img:
        # Konvertera till RGB först om bilden är RGBA eller palette
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert("RGB")

        # Beräkna ny höjd med bibehållet bildförhållande
        orig_w, orig_h = img.size
        aspect = orig_h / orig_w
        target_height = int(target_width * aspect)
        
        resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Floyd-Steinberg dithering till 1-bit monokrom
        dithered = resized.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
        return dithered

def run_graphics_test(image_path=None, vendor_id=0x28e9, product_id=0x0289, in_ep=0x81, out_ep=0x01):
    if not image_path:
        image_path = '/Volumes/Ugreen 2TB/Develop/kvitto_skrivare/coker.jpg'

    print(f"[*] Behandlar bild: {image_path}...")
    processed_img = prepare_image_for_pos58(image_path)

    print(f"[*] Ansluter till skrivare (0x{vendor_id:04x}:0x{product_id:04x})...")
    try:
        printer = Usb(vendor_id, product_id, in_ep=in_ep, out_ep=out_ep)
    except Exception as e:
        print(f"[!] Kunde inte ansluta till skrivaren: {e}")
        sys.exit(1)

    try:
        printer.hw("INIT")
        printer.set(align="center")

        print("[*] Skriver ut grafik...")
        # center alignment och raster image
        printer.image(processed_img, impl="bitImageRaster")

        printer.text("\nLook at this good dog!\n")
        printer.text("--------------------------------\n")
        printer.text(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n\n\n")

        print("[✓] Grafikutskrift klar!")
    except Exception as e:
        print(f"[!] Fel vid utskrift av bild: {e}")
    finally:
        printer.close()
        print("[*] Skrivaren stängd.")


if __name__ == "__main__":
    img_file = sys.argv[1] if len(sys.argv) > 1 else None
    run_graphics_test(img_file)
