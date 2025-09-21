# ESP32 Attiny13 Programmer

Dieses Projekt ermöglicht es, einen ATtiny13 Mikrocontroller direkt über einen ESP32 (z.B. ESP32-C3) per In-Circuit-Programming (ICP) zu programmieren – und das mit MicroPython! Damit können Firmware-Updates für den ATtiny13 sogar "Over the Air" (OTA) ausgeliefert werden, solange der ESP32 mit dem Internet verbunden ist.

## Funktionsweise

Das Skript `esp.py` implementiert das serielle ISP-Protokoll (In-System-Programming) für den ATtiny13. Der ESP32 steuert dabei die nötigen Pins (SCK, MOSI, MISO, RESET) direkt an und kann so den ATtiny13 flashen, verifizieren und auslesen.

## Vorteile
- **OTA-Updates:** Firmware für den ATtiny13 kann remote über den ESP32 aktualisiert werden.
- **Einfache Integration:** Keine zusätzliche Hardware nötig, nur die Verbindung zwischen ESP32 und ATtiny13.
- **MicroPython:** Das Skript läuft direkt auf dem ESP32 mit MicroPython.

## Schaltplan / Pinbelegung

| ATtiny13 Pin | Funktion | ESP32 Pin (im Skript) |
|-------------|----------|-----------------------|
| RESET       | Reset    | GPIO20                |
| SCK         | Clock    | GPIO8                 |
| MOSI        | Daten in | GPIO10                |
| MISO        | Daten out| GPIO9                 |
| VCC, GND    | Strom    | 3.3V, GND             |

> **Hinweis:** Die verwendeten GPIOs können je nach ESP32-Modell variieren. Passe ggf. die Pin-Nummern in `esp.py` an.

### Verdrahtung (Mermaid-Diagramm)

```mermaid
flowchart LR
    ESP32[ESP32] -->|SCK (GPIO8)| ATTINY[ATtiny13]
    ESP32 -->|MOSI (GPIO10)| ATTINY
    ESP32 -->|MISO (GPIO9)| ATTINY
    ESP32 -->|RESET (GPIO20)| ATTINY
    ESP32 -->|VCC (3.3V)| ATTINY
    ESP32 -->|GND| ATTINY
```

## Nutzung
1. **Verkabelung:**
   - Verbinde die oben genannten Pins des ESP32 mit dem ATtiny13.
   - Achte auf die richtige Stromversorgung (3.3V oder 5V, je nach ATtiny13).
2. **MicroPython auf ESP32 installieren:**
   - Flashe MicroPython auf deinen ESP32 (z.B. mit [esptool](https://micropython.org/download/esp32/)).
3. **Skript hochladen:**
   - Lade `esp.py` auf den ESP32 (z.B. mit [ampy](https://github.com/scientifichackers/ampy), Thonny oder mpremote).
4. **Skript ausführen:**
   - Starte das Skript auf dem ESP32. Es programmiert den ATtiny13 mit dem im Skript hinterlegten Intel HEX-File.
   - Die Ausgabe zeigt den Programmier- und Verifizierungsstatus.

## Eigene Firmware flashen
- Ersetze den Inhalt der Variable `hex_file_content` in `esp.py` durch dein eigenes HEX-File.
- Das Skript übernimmt das Parsen und Flashen automatisch.

## Hinweise
- Die Programmierung erfolgt mit ca. 100 kHz SCK.
- Das Skript prüft die Signatur des ATtiny13 und verifiziert den Flash-Inhalt nach dem Schreiben.
- Für andere ATtiny-Modelle sind ggf. Anpassungen nötig (z.B. Page Size, Signature).

## Beispiel-Ausgabe
```
Starting ATtiny13 programming...
Programming mode entered successfully.
Read signature: [30, 144, 7] (hex: ['0x1e', '0x90', '0x7'])
Performing chip erase...
Chip erase complete.
Programming page 0 at address 0x0000...
...
Verification PASSED ✅
ATtiny13 programming + verification successful!
```

## Lizenz
Apache License 2.0




