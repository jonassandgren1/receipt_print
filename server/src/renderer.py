"""
renderer.py - Mallmotor och bildbehandling för kvitton.
"""

from io import BytesIO
from PIL import Image


class ReceiptRenderer:
    TARGET_WIDTH = 384  # 384 dots for POS58 203 DPI

    @staticmethod
    def process_image(image_bytes: bytes) -> Image.Image:
        """
        Tar råa bildbytes, skalar om till 384 px bredd och konverterar
        till 1-bit monokrom med Floyd-Steinberg dithering.
        """
        with Image.open(BytesIO(image_bytes)) as img:
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")

            orig_w, orig_h = img.size
            aspect = orig_h / orig_w
            target_h = int(ReceiptRenderer.TARGET_WIDTH * aspect)

            resized = img.resize((ReceiptRenderer.TARGET_WIDTH, target_h), Image.Resampling.LANCZOS)
            return resized.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
