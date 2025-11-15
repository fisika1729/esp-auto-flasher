#!/usr/bin/env python3
"""
ESP32 MAC Address Collector and Flasher
Detects new ESP32 boards, collects BT MAC addresses, and flashes firmware
"""

import serial
import serial.tools.list_ports
import time
import re
import json
import subprocess
from datetime import datetime
from pathlib import Path


class ESP32Manager:
    def __init__(self, baudrate=115200, timeout=30):
        self.baudrate = baudrate
        self.timeout = timeout
        self.mac_database = []
        self.device_counter = 1
        self.db_file = "esp32_mac_database.json"
        
        # Load existing database if available
        self.load_database()
    
    def load_database(self):
        """Load existing MAC database from file"""
        if Path(self.db_file).exists():
            with open(self.db_file, 'r') as f:
                data = json.load(f)
                self.mac_database = data.get('devices', [])
                self.device_counter = data.get('next_id', 1)
            print(f"Loaded {len(self.mac_database)} devices from database")
    
    def save_database(self):
        """Save MAC database to file"""
        data = {
            'devices': self.mac_database,
            'next_id': self.device_counter,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.db_file, 'w') as f:
            json.dump(data, indent=2, fp=f)
        print(f"Database saved to {self.db_file}")
    
    def detect_esp32_port(self, known_ports=None):
        """Detect new ESP32 port connection"""
        print("Waiting for ESP32 to be connected...")
        
        if known_ports is None:
            known_ports = set()
        
        while True:
            current_ports = set([port.device for port in serial.tools.list_ports.comports()])
            new_ports = current_ports - known_ports
            
            if new_ports:
                port = list(new_ports)[0]
                print(f"New port detected: {port}")
                return port, current_ports
            
            time.sleep(0.5)
    
    def parse_mac_from_boot_message(self, line):
        """Extract MAC address from ESP32 boot messages"""
        # Look for MAC address patterns like "MAC: xx:xx:xx:xx:xx:xx" or similar
        mac_patterns = [
            r'[Mm][Aa][Cc][:\s]+([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',
            r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',
        ]
        
        for pattern in mac_patterns:
            match = re.search(pattern, line)
            if match:
                mac = match.group(0)
                # Normalize MAC address format
                mac = mac.replace('MAC:', '').replace('Mac:', '').replace('mac:', '').strip()
                mac = mac.replace('-', ':').upper()
                return mac
        return None
    
    def increment_mac(self, mac_str, increment=2):
        """Increment MAC address by specified value"""
        # Remove colons and convert to integer
        mac_int = int(mac_str.replace(':', ''), 16)
        # Add increment
        new_mac_int = mac_int + increment
        # Convert back to MAC format
        mac_hex = format(new_mac_int, '012X')
        # Format as MAC address
        new_mac = ':'.join([mac_hex[i:i+2] for i in range(0, 12, 2)])
        return new_mac
    
    def collect_mac_from_reset(self, port):
        """Wait for ESP32 reset and collect MAC address"""
        print(f"\n{'='*60}")
        print(f"Device #{self.device_counter}")
        print(f"{'='*60}")
        print(f"Opening port: {port}")
        print("Press RESET button on ESP32 now...")
        
        try:
            ser = serial.Serial(port, self.baudrate, timeout=2)
            time.sleep(0.5)
            
            # Clear any existing data
            ser.reset_input_buffer()
            
            start_time = time.time()
            wifi_mac = None
            
            while time.time() - start_time < self.timeout:
                if ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            print(f"  {line}")
                            
                            # Try to extract MAC address
                            mac = self.parse_mac_from_boot_message(line)
                            if mac and not wifi_mac:
                                wifi_mac = mac
                                print(f"\n✓ WiFi MAC detected: {wifi_mac}")
                                bt_mac = self.increment_mac(wifi_mac, 2)
                                print(f"✓ BT MAC calculated: {bt_mac}")
                                
                                # Store in database
                                device_info = {
                                    'id': self.device_counter,
                                    'wifi_mac': wifi_mac,
                                    'bt_mac': bt_mac,
                                    'timestamp': datetime.now().isoformat(),
                                    'port': port
                                }
                                self.mac_database.append(device_info)
                                self.device_counter += 1
                                self.save_database()
                                
                                ser.close()
                                return device_info
                    except UnicodeDecodeError:
                        continue
            
            ser.close()
            print("\n✗ Timeout waiting for MAC address")
            return None
            
        except serial.SerialException as e:
            print(f"Error opening port: {e}")
            return None
    
    def flash_firmware(self, port, binary_path, flash_address='0x10000', chip='esp32'):
        """Flash firmware to ESP32 using esptool"""
        print(f"\n{'='*60}")
        print(f"Flashing firmware to {port}")
        print(f"{'='*60}")
        
        if not Path(binary_path).exists():
            print(f"✗ Error: Binary file not found: {binary_path}")
            return False
        
        try:
            # Erase flash (optional - comment out if not needed)
            print("Erasing flash...")
            erase_cmd = [
                'esptool.py',
                '--chip', chip,
                '--port', port,
                'erase_flash'
            ]
            subprocess.run(erase_cmd, check=True)
            
            # Flash firmware
            print(f"Flashing {binary_path}...")
            flash_cmd = [
                'esptool.py',
                '--chip', chip,
                '--port', port,
                '--baud', '460800',
                'write_flash',
                '-z',
                flash_address,
                binary_path
            ]
            
            result = subprocess.run(flash_cmd, check=True)
            print("✓ Flash complete!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Flash failed: {e}")
            return False
        except FileNotFoundError:
            print("✗ Error: esptool.py not found. Install it with: pip install esptool")
            return False
    
    def run_collection_mode(self, auto_flash=False, binary_path=None):
        """Run in collection mode - detect boards and collect MACs"""
        print("\n" + "="*60)
        print("ESP32 MAC Address Collection Mode")
        print("="*60)
        
        if auto_flash and binary_path:
            print(f"Auto-flash enabled: {binary_path}")
        
        known_ports = set([port.device for port in serial.tools.list_ports.comports()])
        
        while True:
            print(f"\nWaiting for new ESP32 board (Total collected: {len(self.mac_database)})...")
            port, known_ports = self.detect_esp32_port(known_ports)
            
            # Wait a moment for the port to stabilize
            time.sleep(1)
            
            # Collect MAC
            device_info = self.collect_mac_from_reset(port)
            
            if device_info:
                print(f"\n✓ Device #{device_info['id']} added to database")
                
                # Auto-flash if enabled
                if auto_flash and binary_path:
                    response = input("\nFlash firmware now? (Y/n): ").strip().lower()
                    if response != 'n':
                        self.flash_firmware(port, binary_path)
                
                print("\nReady for next board. Remove current board and connect next one.")
            else:
                print("\n✗ Failed to collect MAC. Please try again.")
            
            # Option to quit
            print("\nPress Ctrl+C to stop collection mode")
    
    def print_database(self):
        """Print all collected MAC addresses"""
        print(f"\n{'='*80}")
        print(f"ESP32 MAC Address Database ({len(self.mac_database)} devices)")
        print(f"{'='*80}")
        print(f"{'ID':<5} {'WiFi MAC':<20} {'BT MAC':<20} {'Timestamp':<25}")
        print("-"*80)
        
        for device in self.mac_database:
            print(f"{device['id']:<5} {device['wifi_mac']:<20} {device['bt_mac']:<20} {device['timestamp']:<25}")
        print("="*80)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ESP32 MAC Collector and Flasher')
    parser.add_argument('--collect', action='store_true', help='Run in collection mode')
    parser.add_argument('--flash', type=str, help='Flash binary file to ESP32')
    parser.add_argument('--port', type=str, help='Serial port (required for flash mode)')
    parser.add_argument('--auto-flash', type=str, help='Auto-flash binary after MAC collection')
    parser.add_argument('--address', type=str, default='0x10000', help='Flash address (default: 0x10000)')
    parser.add_argument('--chip', type=str, default='esp32', help='Chip type (default: esp32)')
    parser.add_argument('--show', action='store_true', help='Show collected MAC database')
    
    args = parser.parse_args()
    
    manager = ESP32Manager()
    
    if args.show:
        manager.print_database()
    elif args.collect:
        manager.run_collection_mode(auto_flash=bool(args.auto_flash), binary_path=args.auto_flash)
    elif args.flash:
        if not args.port:
            print("Error: --port required for flash mode")
            return
        manager.flash_firmware(args.port, args.flash, args.address, args.chip)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
