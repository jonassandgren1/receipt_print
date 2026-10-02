"""
main.py - Central API och webhook-mottagare på hemservern.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from .client import PrinterClient

app = FastAPI(title="POS Receipt Server", version="1.0.0")
client = PrinterClient()


class MessagePrintRequest(BaseModel):
    title: str = "MEDDELANDE"
    message: str
    sender: Optional[str] = None


@app.get("/health")
async def health():
    printer_health = {}
    try:
        printer_health = await client.check_health()
    except Exception as e:
        printer_health = {"error": str(e)}
    return {"server": "online", "printer_connection": printer_health}


@app.post("/webhook/message")
async def print_message(req: MessagePrintRequest):
    """Tar emot textmeddelande och skickar det formaterat till kvittoskrivaren."""
    items = []
    # Bryt upp texten i rader
    for line in req.message.split("\n"):
        items.append({"name": line[:31], "price": 0.0})

    payload = {
        "title": req.title,
        "subtitle": f"Från: {req.sender}" if req.sender else None,
        "items": items,
        "footer": "Skickat via POS-Server Webhook"
    }

    try:
        res = await client.send_json(payload)
        return {"status": "dispatched", "detail": res}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Kunde inte nå skrivarservertjänsten: {e}")
