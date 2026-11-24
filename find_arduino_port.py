"""
Utility: Find Arduino COM Port
Run this script to see all serial devices connected to your computer.
It will help you identify which COM port your Arduino Uno is using.
"""

import serial.tools.list_ports


def find_arduino_port():
    """List all serial ports and try to identify the Arduino."""

    print("=" * 55)
    print("  Serial Port Scanner - Find Your Arduino")
    print("=" * 55)
    print()

    # Get a list of all serial ports on this computer
    ports = serial.tools.list_ports.comports()

    if not ports:
        print("No serial ports found!")
        print("Make sure your Arduino is plugged in via USB.")
        return None

    print(f"Found {len(ports)} serial port(s):\n")

    arduino_port = None

    for port in ports:
        # Print detailed info about each port
        print(f"  Port:         {port.device}")
        print(f"  Description:  {port.description}")
        print(f"  Manufacturer: {port.manufacturer}")
        print(f"  Hardware ID:  {port.hwid}")
        print()

        # Arduino Uno typically shows up with these identifiers
        desc_lower = (port.description or "").lower()
        mfr_lower = (port.manufacturer or "").lower()

        if "arduino" in desc_lower or "arduino" in mfr_lower:
            arduino_port = port.device
        elif "ch340" in desc_lower or "ch340" in mfr_lower:
            # Many Arduino clones use the CH340 USB-to-Serial chip
            arduino_port = port.device
        elif "usb-serial" in desc_lower or "usb serial" in desc_lower:
            arduino_port = port.device

    print("-" * 55)

    if arduino_port:
        print(f"  Arduino likely on: {arduino_port}")
    else:
        print("  Could not auto-detect Arduino.")
        print("  Look at the list above and find the port that")
        print("  appears/disappears when you plug/unplug the Arduino.")

    print()
    return arduino_port


if __name__ == "__main__":
    find_arduino_port()

