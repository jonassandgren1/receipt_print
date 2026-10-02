#!/usr/bin/env python3
"""
main.py - Lättviktig FastAPI-daemon för Raspberry Pi Zero 2 W.
Tar emot utskriftsanrop via HTTP och vidarebefordrar till POS58-01.
"""

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from escpos.printer import Usb

app = FastAPI(title="POS58 Printer Daemon", version="1.0.0")

VENDOR_ID = 0x28e9
PRODUCT_ID = 0x0289
IN_EP = 0x81
OUT_EP = 0x01


class ReceiptItem(BaseModel):
    name: str
    price: float


class PrintJsonRequest(BaseModel):
    title: str = "KVITTO"
    subtitle: Optional[str] = None
    items: List[ReceiptItem] = []
    total: Optional[float] = None
    vat: Optional[float] = None
    footer: Optional[str] = "Tack för besöket!"


def get_printer():
    """Skapar en anslutning till skrivaren."""
    try:
        printer = Usb(VENDOR_ID, PRODUCT_ID, in_ep=IN_EP, out_ep=OUT_EP)
        return printer
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Skrivaren är inte tillgänglig: {e}")


@app.get("/health")
def health_check():
    """Hälsokontroll för att verifiera kontakt med Pi och skrivare."""
    try:
        printer = get_printer()
        printer.close()
        return {"status": "ok", "printer": "connected", "vendor": hex(VENDOR_ID), "product": hex(PRODUCT_ID)}
    except Exception as e:
        return {"status": "warning", "printer": "disconnected", "error": str(e)}


@app.post("/print/raw")
async def print_raw(request: Request):
    """Tar emot rå ESC/POS-byteström och skickar direkt till skrivaren."""
    raw_data = await request.body()
    if not raw_data:
        raise HTTPException(status_code=400, detail="Ingen data skickades.")

    printer = get_printer()
    try:
        printer._raw(raw_data)
        return {"status": "success", "bytes_printed": len(raw_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Utskriftsfel: {e}")
    finally:
        printer.close()


@app.post("/print/json")
def print_json(payload: PrintJsonRequest):
    """Formaterar strukturerad data och skriver ut ett kvitto."""
    printer = get_printer()
    try:
        printer.hw("INIT")
        printer.set(align="center", bold=True, double_height=True, double_width=True)
        printer.text(f"{payload.title}\n")

        printer.set(align="center", bold=False, double_height=False, double_width=False)
        if payload.subtitle:
            printer.text(f"{payload.subtitle}\n")
        printer.text("--------------------------------\n")

        printer.set(align="left")
        computed_total = 0.0
        for item in payload.items:
            price_str = f"{item.price:.2f} kr"
            col_price = len(price_str)
            col_name = 32 - col_price - 1
            name = item.name[:col_name]
            printer.text(f"{name:<{col_name}} {price_str:>{col_price}}\n")
            computed_total += item.price

        printer.text("--------------------------------\n")
        final_total = payload.total if payload.total is not None else computed_total
        total_str = f"{final_total:.2f} kr"
        p_len = len(total_str)
        l_len = 32 - p_len - 1
        printer.set(bold=True)
        printer.text(f"{'TOTALT':<{l_len}} {total_str:>{p_len}}\n")

        if payload.vat is not None:
            printer.set(bold=False)
            vat_str = f"{payload.vat:.2f} kr"
            vl = len(vat_str)
            ll = 32 - vl - 1
            printer.text(f"{'Varav moms':<{ll}} {vat_str:>{vl}}\n")

        printer.set(align="center", bold=False)
        printer.text("--------------------------------\n")
        if payload.footer:
            printer.text(f"{payload.footer}\n")

        printer.text("\n\n\n\n")
        return {"status": "success", "printed_items": len(payload.items), "total": final_total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Utskriftsfel: {e}")
    finally:
        printer.close()
