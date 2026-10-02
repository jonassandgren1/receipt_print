#!/usr/bin/env python3
"""
03_receipt_builder.py - Modulär och objektorienterad kvittobyggare för POS58-01.

Denna klass hanterar:
  - 32-kolumns layout (standardbredd för POS58 med Font A)
  - Rubriker och underrubriker
  - Tabellrader för artiklar, priser och summor
  - Logotyp / grafik i 384 px bredd
  - QR-koder och streckkoder
  - Säker utskrift via USB eller export till byte-ström
"""

import sys
from datetime import datetime
from PIL import Image
from escpos.printer import Usb


class ReceiptBuilder:
    LINE_WIDTH = 32  # Standard antal tecken per rad för POS58 (Font A)

    def __init__(self, vendor_id=0x28e9, product_id=0x0289, in_ep=0x81, out_ep=0x01):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.in_ep = in_ep
        self.out_ep = out_ep
        self.printer = None

    def connect(self):
        """Initierar anslutningen till skrivaren."""
        try:
            self.printer = Usb(self.vendor_id, self.product_id, in_ep=self.in_ep, out_ep=self.out_ep)
            self.printer.hw("INIT")
            return True
        except Exception as e:
            print(f"[!] Anslutningsfel: {e}")
            return False

    def close(self):
        """Stänger USB-anslutningen."""
        if self.printer:
            try:
                self.printer.close()
            except Exception:
                pass
            self.printer = None

    def print_logo(self, image_path):
        """Skriver ut en logotyp/bild."""
        if not self.printer:
            return
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")

            # Skala till max 384 px bredd
            target_width = 384
            aspect = img.size[1] / img.size[0]
            target_height = int(target_width * aspect)
            resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            dithered = resized.convert("1", dither=Image.Dither.FLOYDSTEINBERG)

            self.printer.set(align="center")
            self.printer.image(dithered, impl="bitImageRaster")

    def print_header(self, title, subtitle=None):
        """Skriver ut kvittohuvud."""
        if not self.printer:
            return
        self.printer.set(align="center", bold=True, double_height=True, double_width=True)
        self.printer.text(f"{title}\n")
        self.printer.set(align="center", bold=False, double_height=False, double_width=False)
        if subtitle:
            self.printer.text(f"{subtitle}\n")
        self.printer.text(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
        self.print_divider("=")

    def print_divider(self, char="-"):
        """Skriver ut en skiljelinje."""
        if not self.printer:
            return
        self.printer.set(align="left", bold=False)
        self.printer.text((char * self.LINE_WIDTH)[:self.LINE_WIDTH] + "\n")

    def print_item(self, name, price):
        """Skriver ut en rad med artikelnamn och pris (max 32 tecken)."""
        if not self.printer:
            return
        # Formatera vänster artikelnamn och höger pris
        price_str = f"{price:.2f} kr" if isinstance(price, (int, float)) else str(price)
        col_price = len(price_str)
        col_name = self.LINE_WIDTH - col_price - 1

        truncated_name = name[:col_name]
        line = f"{truncated_name:<{col_name}} {price_str:>{col_price}}\n"
        self.printer.set(align="left", bold=False)
        self.printer.text(line)

    def print_total(self, total, vat=None):
        """Skriver ut summan och ev. moms."""
        if not self.printer:
            return
        self.print_divider("-")
        self.printer.set(align="left", bold=True)
        total_str = f"{total:.2f} kr" if isinstance(total, (int, float)) else str(total)
        price_len = len(total_str)
        label_len = self.LINE_WIDTH - price_len - 1
        self.printer.text(f"{'TOTALT':<{label_len}} {total_str:>{price_len}}\n")

        if vat is not None:
            self.printer.set(bold=False)
            vat_str = f"{vat:.2f} kr" if isinstance(vat, (int, float)) else str(vat)
            v_len = len(vat_str)
            l_len = self.LINE_WIDTH - v_len - 1
            self.printer.text(f"{'Varav moms (25%)':<{l_len}} {vat_str:>{v_len}}\n")

        self.print_divider("=")

    def print_footer(self, message="Tack för besöket! Välkommen åter.", feed_lines=4):
        """Skriver ut kvittofot och matar fram papper."""
        if not self.printer:
            return
        self.printer.set(align="center", bold=False)
        self.printer.text(f"\n{message}\n")
        self.printer.text("\n" * feed_lines)


def run_demo():
    builder = ReceiptBuilder()
    if not builder.connect():
        sys.exit(1)

    try:
        print("[*] Genererar och skriver ut demonstrationskvitto...")
        builder.print_header("KAFÉ AGY", "Storgatan 12, Karlstad")
        builder.print_item("Espresso Dubbel", 36.00)
        builder.print_item("Havre Cappuccino", 45.00)
        builder.print_item("Kardemummabulle", 32.00)
        builder.print_item("Smörgås med ost", 49.00)
        builder.print_total(162.00, vat=32.40)
        builder.print_footer("Välkommen åter!\nWifi: KafeGuest / Lösen: kaffe2026")
        print("[✓] Kvittoutskrift klar!")
    finally:
        builder.close()


if __name__ == "__main__":
    run_demo()
