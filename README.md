# ESP32 MAC Address Collector and Flasher

Automatically collect Bluetooth MAC addresses from ESP32 boards and flash firmware.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### 1. Collect MAC Addresses Only

Connect ESP32 boards one by one, press RESET button when prompted:

```bash
python esp32_mac_collector.py --collect
```

The script will:
- Detect new ESP32 boards when connected
- Wait for you to press RESET button
- Capture boot messages and extract WiFi MAC
- Calculate BT MAC (WiFi MAC + 2)
- Save to `esp32_mac_database.json`

### 2. Collect MACs with Auto-Flash

Automatically flash firmware after collecting each MAC:

```bash
python esp32_mac_collector.py --collect --auto-flash firmware.bin
```

### 3. Flash a Specific Board

Flash firmware to a specific port:

```bash
python esp32_mac_collector.py --flash firmware.bin --port /dev/ttyUSB0
```

With custom flash address:

```bash
python esp32_mac_collector.py --flash firmware.bin --port /dev/ttyUSB0 --address 0x1000
```

### 4. View Collected Database

```bash
python esp32_mac_collector.py --show
```

## Database Format

The collected data is stored in `esp32_mac_database.json`:

```json
{
  "devices": [
    {
      "id": 1,
      "wifi_mac": "AA:BB:CC:DD:EE:FF",
      "bt_mac": "AA:BB:CC:DD:EF:01",
      "timestamp": "2025-11-16T10:30:00",
      "port": "/dev/ttyUSB0"
    }
  ],
  "next_id": 2,
  "last_updated": "2025-11-16T10:30:00"
}
```

## Workflow for 100 Boards

1. Start collection mode:
   ```bash
   python esp32_mac_collector.py --collect --auto-flash firmware.bin
   ```

2. For each board:
   - Connect ESP32 via USB
   - Wait for detection message
   - Press RESET button when prompted
   - Script collects MAC and flashes firmware
   - Disconnect board
   - Connect next board

3. View results:
   ```bash
   python esp32_mac_collector.py --show
   ```

## Options

- `--collect` - Run in collection mode
- `--flash BINARY` - Flash binary file
- `--port PORT` - Serial port (for flash mode)
- `--auto-flash BINARY` - Auto-flash after MAC collection
- `--address ADDR` - Flash address (default: 0x10000)
- `--chip TYPE` - Chip type (default: esp32)
- `--show` - Display collected database

## Notes

- The script automatically calculates BT MAC as WiFi MAC + 2
- Database is saved after each successful collection
- Press Ctrl+C to exit collection mode
- Compatible with ESP32, ESP32-S2, ESP32-S3, ESP32-C3, etc.

## Troubleshooting

**MAC not detected:**
- Ensure RESET button is pressed after prompt
- Check baud rate (default: 115200)
- Verify USB cable supports data transfer

**Flash fails:**
- Check binary file path
- Verify correct flash address for your bootloader
- Try lower baud rate: edit `baudrate` in flash command

**Port not detected:**
- Check USB connection
- Install USB-to-serial drivers (CP210x, CH340, etc.)
- Check permissions: `sudo usermod -a -G dialout $USER`
