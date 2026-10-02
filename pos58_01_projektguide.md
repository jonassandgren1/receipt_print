# Utvecklingsplan & Projektguide: Trådlös POS-kvittoskrivare (POS58-01)

Denna projektguide är utformad för att ge en logisk och pedagogisk genomgång av hur vi bygger ett heltäckande utskriftssystem för termokvittoskrivaren POS58-01. Guiden är uppdelad i faser där du först testar och kontrollerar hårdvaran lokalt i Antigravity, och därefter kopplar ihop nätverk, Docker och Raspberry Pi Zero 2 W manuellt.

---

## 1. Systemarkitektur & Arbetsflöde

Utskriftssystemet delas upp i två huvudsakliga komponenter: **Sändaren (Hemserver/Docker)** och **Mottagaren (Raspberry Pi Zero 2 W)**.

```text
[ Trigger / Klient / Webhook ]
              │
              ▼
┌──────────────────────────────────────────────────┐
│  Hemserver (Docker)                              │
│  - Mallhantering (Kvittolayout, text, ikoner)    │
│  - Bildbehandling (Skalning, 1-bit dithering)    │
│  - Köhantering & felhantering                    │
└───────────────────────┬──────────────────────────┘
                        │
                        ▼ (Krypterat via Tailscale Mesh)
┌──────────────────────────────────────────────────┐
│  Raspberry Pi Zero 2 W (Mottagande Daemon)       │
│  - Lättviktigt REST API (FastAPI / Flask)        │
│  - Maskinnära skrivarkontroll (ESC/POS)          │
└───────────────────────┬──────────────────────────┘
                        │
                        ▼ (USB OTG: /dev/usb/lp0 eller PyUSB)
┌──────────────────────────────────────────────────┐
│  POS58-01 Termoskrivare                          │
└──────────────────────────────────────────────────┘
```

### Varför dela upp ansvaret så här?
1. **Resurssnål mottagare:** Raspberry Pi Zero 2 W har begränsat med CPU och RAM. Genom att låta hemservern göra all tung bildbehandling och layoutkompilering behöver Pi:n endast fungera som en stabil relästation för rådata.
2. **Säkerhet:** Skrivaren exponeras aldrig direkt mot internet, utan endast mot ditt interna nätverk via Tailscale.
3. **Modularitet:** Du kan bygga om gränssnittet eller ändra dina kvittomallar på hemservern utan att behöva röra installationen på din Raspberry Pi.

---

## 2. Hårdvaruspecifikationer för POS58-01

- **Pappersbredd:** 58 mm
- **Effektiv utskriftsbredd:** 48 mm
- **Upplösning:** 203 DPI (8 dots per mm) $\rightarrow$ **Exakt 384 punkter per rad**
- **Tecken per rad:**
  - Standard (Font A, 12x24 px): 32 tecken
  - Kompakt (Font B, 9x17 px): 42 tecken
- **Styrprotokoll:** ESC/POS (standardiserade kontrollsekvenser i bytes)
- **Grafikformat:** 1-bit monokrom rasterbitmapp (svart eller vitt, inga gråskalor direkt från hårdvaran)

---

## 3. Utvecklingsfaser

---

### Fas 1: Lokal Maskinvaruverifiering & ESC/POS-motor (Antigravity)
**Mål:** Verifiera att skrivaren tar emot rådata, förstå hur text och grafik byggs upp i kod, samt ta fram testskript innan nätverket blandas in.

#### Steg 1.1: Identifiering av USB-enhet
När skrivaren ansluts med USB till din dator eller testmaskin skapar Linux-kärnan oftast en enhetsnod.
1. Kör följande i terminalen för att identifiera Vendor ID och Product ID:
   ```bash
   lsusb
   ```
   *Exempelutdata:* `Bus 001 Device 004: ID 0416:5011 Winbond Electronics Corp.`
2. Kontrollera om kärnmodulen `usblp` skapade en fil:
   ```bash
   ls -l /dev/usb/lp*
   ```
3. Ge användaren rättigheter att läsa/skriva till enheten utan `sudo`:
   ```bash
   sudo chmod 666 /dev/usb/lp0
   ```

#### Steg 1.2: Rå byte-test (Bash)
Ett enkelt sätt att bekräfta att skrivhuvudet fungerar är att skicka ren text följt av radbrytningar och pappersmatning direkt till skrivarfilen:
```bash
echo -e "HALLÅ VÄRLDEN!\nDetta är ett direkttest.\n\n\n" > /dev/usb/lp0
```

#### Steg 1.3: Python-miljö för utveckling
Skapa och aktivera ett virtuellt bibliotek i Antigravity:
```bash
python3 -m venv venv
source venv/bin/activate
pip install python-escpos pillow pydantic
```

#### Steg 1.4: Skapa testsvit i Python
Bygg tre skript för att förstå skrivarens kapacitet:
1. `01_test_text.py`: Testa rubriker, fetstil, understrykning, dubbel höjd, centrering och tabeller (32 tecken bredd).
2. `02_test_graphics.py`:
   - Läs in en bild (t.ex. PNG/JPG).
   - Skala om bilden till max 384 pixlars bredd med bevarat bildförhållande.
   - Konvertera till monokrom med Floyd-Steinberg dithering för att efterlikna gråskalor.
   - Skriv ut via `escpos.image()`.
3. `03_receipt_builder.py`: Ett objektorienterat skript som sätter ihop text, dekorativa skiljelinjer (`--------------------------------`), kvittoposter och en bildlogotyp i ett sammanhängande utskriftsjobb.

*Acceptanskriterium för Fas 1:* Du kan köra ett skript som skriver ut ett prydligt, centrerat kvitto med både text och bild utan felmeddelanden.

---

### Fas 2: Konfigurera Raspberry Pi Zero 2 W som Print Server
**Mål:** Göra Zero 2 W till en nätverksansluten skrivarenhet med en bakgrundstjänst.

#### Steg 2.1: Förbered operativsystemet
1. Installera **Raspberry Pi OS Lite (64-bit)** på ett MicroSD-kort.
2. Aktivera SSH och Wi-Fi i konfigurationen (via Raspberry Pi Imager).
3. Koppla skrivaren till Zero 2 W via en USB OTG-kabel (anslut till den inre micro-USB-porten som stödjer data, inte den rena strömporten).

#### Steg 2.2: Skapa udev-regel för stabil enhetsidentifiering
För att slippa rättighetsproblem och garantera att skrivaren alltid har samma sökväg:
1. Skapa `/etc/udev/rules.d/99-pos-printer.rules`:
   ```udev
   SUBSYSTEM=="usb", ATTRS{idVendor}=="0416", ATTRS{idProduct}=="5011", MODE="0666", GROUP="dialout"
   ```
   *(Ersätt idVendor och idProduct med värdena från `lsusb` på din Pi).*
2. Ladda om udev-reglerna:
   ```bash
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```

#### Steg 2.3: Utveckla Utskrifts-Daemon (FastAPI på Pi Zero)
Skapa en minimal API-tjänst på Pi:n:
- **Endpoint:** `POST /print/raw` (tar emot färdig ESC/POS-byteström)
- **Endpoint:** `POST /print/json` (tar emot strukturerad JSON med text och rader)
- **Endpoint:** `GET /health` (returnerar status för att verifiera kontakt)

#### Steg 2.4: Skapa systemd-service
Skapa filen `/etc/systemd/system/pos-daemon.service`:
```ini
[Unit]
Description=POS Printer Daemon
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/pos-daemon
ExecStart=/home/pi/pos-daemon/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```
Aktivera och starta:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pos-daemon
```

*Acceptanskriterium för Fas 2:* Ett anrop med `curl` från din lokala dator till `http://<PI-IP>:8000/health` svarar `{"status": "ok"}` och en POST-begäran skriver ut ett kvitto.

---

### Fas 3: Nätverk & Säkerhet via Tailscale
**Mål:** Etablera en krypterad punkt-till-punkt-anslutning mellan hemservern och Pi Zero 2 W utan öppna portar i din router.

#### Steg 3.1: Installera Tailscale på Pi Zero 2 W
1. Kör installationsskriptet:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```
2. Koppla upp noden:
   ```bash
   sudo tailscale up --hostname=pos-zero
   ```
3. Notera Pi-nodens Tailscale IP (t.ex. `100.x.y.z`) eller använd nodnamnet direkt med Tailscale MagicDNS.

#### Steg 3.2: Begränsa daemonens nätverksgränssnitt
För maximal säkerhet ska skrivartjänsten på Pi:n endast lyssna på Tailscale-interfacet (`tailscale0`) eller `127.0.0.1`, inte på hela det lokala Wi-Fi-nätverket.

*Acceptanskriterium för Fas 3:* Du kan skicka utskriftsanrop från valfri maskin i ditt Tailscale-nätverk till `http://pos-zero:8000/print`.

---

### Fas 4: Hemserver (Docker) & Utskriftshantering
**Mål:** Bygga en centraliserad container på hemservern som tar emot innehåll, genererar kvitton och skickar dem vidare till Pi Zero.

#### Steg 4.1: Projektstruktur för Docker-containern
```text
pos-server/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── src/
│   ├── main.py          # Huvud-API / Webhook-lyssnare
│   ├── renderer.py      # Mallmotor och bildbehandling (Pillow/Jinja)
│   └── client.py        # Tailscale HTTP-klient mot Pi Zero
└── templates/           # Kvittomallar (textmallar eller bildmallar)
```

#### Steg 4.2: Uppgiftsflöde i containern
1. **Mottagning:** Containern tar emot en POST med ett meddelande, en inköpslista eller en bild.
2. **Kompilering:** `renderer.py` formaterar texten till exakt 32/42 kolumner och konverterar eventuella bilder till 384 px breda monokroma bitmappar.
3. **Transport:** `client.py` skickar den färdiga datan till `http://pos-zero:8000/print/raw`.
4. **Felhantering:** Om Pi:n är offline sparas jobbet i en lokal kö och försöker igen när noden är tillgänglig.

*Acceptanskriterium för Fas 4:* Du startar containern med `docker compose up -d`, skickar en webhook från mobilen eller hemservern, och kvittot skrivs ut automatiskt via Tailscale.

---

## 4. Felsökning & Kända Fallgropar

| Problem | Orsak | Lösning |
| :--- | :--- | :--- |
| **Skrivaren matar bara ut vitt papper** | Pappersrullen är felvänd | Termopapper har endast kemisk beläggning på ena sidan. Vänd rullen 180 grader. |
| **`Permission denied: /dev/usb/lp0`** | Rättigheter saknas för användaren | Lägg till din användare i gruppen `lp`/`dialout` eller skapa en udev-regel enligt Steg 2.2. |
| **`Resource Busy` i Python** | Kärnmodulen `usblp` låser enheten för PyUSB | Skriv antingen direkt till `/dev/usb/lp0` som fil, eller avinstallera/svartlista `usblp` om PyUSB används. |
| **Utskriften bryts mitt i en bild** | Skrivarens buffert blir överfull | Skicka inte hela bildströmmen i ett enda anrop. Lägg in mikropauser eller dela upp bilden i band om 24–48 linjer. |
| **Skrivaren startar om vid utskrift** | Otillräcklig strömförsörjning | Termoelementen drar upp till 1.5–2A stötvis. Skrivaren måste drivas med sin medföljande strömadapter, inte via 5V från Pi:n. |

---

## 5. Nästa Steg i Utvecklingen

När grundkedjan fungerar kan du expandera systemet med:
- **Morgonrapport:** Automatisk utskrift varje morgon med väderprognos, dagens kalenderhändelser och en slumpad nyhet.
- **Inkorgslapp:** Skriv ut inkommande meddelanden från Telegram, Home Assistant eller e-post.
- **QR-kodskvitto:** Generera dynamiska QR-koder (t.ex. direktlänk till en Spotify-låt eller ett Wi-Fi-gästnätverk).