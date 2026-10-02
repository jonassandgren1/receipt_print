#!/usr/bin/env python3
"""
01_test_text.py - Hårdvarutest för text och formatering på POS58-01.

Identifierade USB-parametrar:
  Vendor ID:  0x28e9
  Product ID: 0x0289
  Endpoints:  0x81 (IN), 0x01 (OUT)
"""

import sys
from datetime import datetime
from escpos.printer import Usb


def run_text_test(vendor_id=0x28e9, product_id=0x0289, in_ep=0x81, out_ep=0x01):
    print(f"[*] Ansluter till skrivare (Vendor: 0x{vendor_id:04x}, Product: 0x{product_id:04x})...")
    
    try:
        printer = Usb(vendor_id, product_id, in_ep=in_ep, out_ep=out_ep)
    except Exception as e:
        print(f"[!] Kunde inte ansluta till skrivaren: {e}")
        print("    Kontrollera att skrivaren är påslagen och USB-kabeln är ansluten.")
        sys.exit(1)

    print("[*] Anslutning lyckades! Skickar testutskrift...")

    try:
        # Återställ skrivaren till standardläge
        printer.hw("INIT")

        # Rubrik (Centrerad, dubbel höjd & bredd, fetstil)
        printer.set(align="center", bold=True, double_height=True, double_width=True)
        printer.text("POS58-01 TEST\n")

        # Underrubrik
        printer.set(align="center", bold=False, double_height=False, double_width=False)
        printer.text("Maskinvaruverifiering\n")
        printer.text(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
        printer.text("--------------------------------\n")  # 32 tecken

        # Vänsterjusterad text & egenskaper
        printer.set(align="left")
        printer.text("Normal text:   32 tecken per rad\n")
        
        printer.set(bold=True)
        printer.text("Fetstil text:  AKTIVERAD\n")
        
        printer.set(bold=False, underline=1)
        printer.text("Understruken:  AKTIVERAD\n")
        
        printer.set(underline=0)
        printer.text("Svenska tecken: Å Ä Ö å ä ö\n")
        printer.text("--------------------------------\n")

        # Enkel tabell / Kvitto-layout
        printer.set(bold=True)
        printer.text(f"{'Artikel':<20}{'Pris':>12}\n")
        printer.set(bold=False)
        printer.text(f"{'Kaffe':<20}{'28.00 kr':>12}\n")
        printer.text(f"{'Kanelbulle':<20}{'25.00 kr':>12}\n")
        printer.text("--------------------------------\n")
        printer.set(bold=True)
        printer.text(f"{'TOTALT':<20}{'53.00 kr':>12}\n")
        
        # Avslutande hälsning & QR-kod test (om skrivaren stödjer det)
        printer.set(align="center", bold=False)
        printer.text("--------------------------------\n")
        printer.text("Testet slutfört utan fel!\n")

        # Mata fram papper så det enkelt kan rivas av (4 rader)
        printer.text("\n\n\n\n")

        print("[✓] Utskriftsjobbet har skickats till skrivaren.")
    except Exception as e:
        print(f"[!] Ett fel uppstod under utskrift: {e}")
    finally:
        printer.close()
        print("[*] Skrivaren stängd.")


if __name__ == "__main__":
    run_text_test()
