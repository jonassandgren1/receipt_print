"""
client.py - Skickar utskriftsjobb till Raspberry Pi Zero över Tailscale.
"""

import os
import httpx

DEFAULT_PRINTER_URL = os.getenv("PRINTER_URL", "http://pos-zero:8000")


class PrinterClient:
    def __init__(self, base_url: str = DEFAULT_PRINTER_URL):
        self.base_url = base_url.rstrip("/")

    async def check_health(self) -> dict:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self.base_url}/health")
            resp.raise_for_status()
            return resp.json()

    async def send_raw(self, raw_bytes: bytes) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/print/raw",
                content=raw_bytes,
                headers={"Content-Type": "application/octet-stream"}
            )
            resp.raise_for_status()
            return resp.json()

    async def send_json(self, payload: dict) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.base_url}/print/json",
                json=payload
            )
            resp.raise_for_status()
            return resp.json()
