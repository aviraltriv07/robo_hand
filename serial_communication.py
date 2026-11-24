"""
serial_communication.py - Arduino Serial Communication Module
===============================================================
Manages the serial link to the Arduino: connecting, sending servo
angles, reading responses, and handling errors.

What changed from serial_test.py:
  - Wrapped in a reusable class (ArduinoConnection)
  - Added duplicate-send prevention (won't re-send identical angles)
  - Non-blocking response reading (doesn't slow down the main loop)
  - Automatic port discovery option
  - Designed for real-time use (no time.sleep in send path)

Usage:
    from serial_communication import ArduinoConnection

    arduino = ArduinoConnection(port="COM3")
    if arduino.connect():
        arduino.send_angles([90, 90, 90, 90, 90])
        ...
        arduino.disconnect()
"""

import serial
import serial.tools.list_ports
import time


class ArduinoConnection:
    """Manages serial communication with the Arduino servo controller."""

    def __init__(self, port=None, baud_rate=9600):
        """
        Args:
            port: COM port string (e.g., "COM3"). If None, auto-detects.
            baud_rate: Must match Serial.begin() in the Arduino sketch.
        """
        self.port = port
        self.baud_rate = baud_rate
        self._serial = None
        self._connected = False

        # Track last sent values to avoid redundant sends
        self._last_sent = None

        # Count for diagnostics
        self.send_count = 0
        self.skip_count = 0  # How many times we skipped a duplicate

    # ----------------------------------------------------------------
    # Connection
    # ----------------------------------------------------------------

    def connect(self):
        """
        Open the serial connection to Arduino.

        Returns:
            True if connected successfully, False otherwise.
        """
        # Auto-detect port if not specified
        if self.port is None:
            self.port = self._find_arduino_port()
            if self.port is None:
                print("ERROR: Could not auto-detect Arduino port.")
                print("  Plug in your Arduino and try again, or specify the port manually.")
                return False

        try:
            print(f"Connecting to Arduino on {self.port} at {self.baud_rate} baud...")

            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=2
            )

            # Arduino resets on serial open — wait for it to boot
            time.sleep(2)

            # Read the READY message
            self._read_all_responses()

            self._connected = True
            print(f"Connected to Arduino on {self.port}!\n")
            return True

        except serial.SerialException as e:
            print(f"ERROR: Could not connect to {self.port}")
            print(f"  {e}")
            print()
            print("Troubleshooting:")
            print("  1. Is the Arduino plugged in?")
            print("  2. Run find_arduino_port.py to check the port.")
            print("  3. Close Arduino IDE Serial Monitor if it's open.")
            self._connected = False
            return False

    def disconnect(self):
        """Close the serial connection."""
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._connected = False
            print(f"Arduino disconnected. Sent {self.send_count} commands "
                  f"({self.skip_count} duplicates skipped).")

    @property
    def is_connected(self):
        return self._connected and self._serial and self._serial.is_open

    # ----------------------------------------------------------------
    # Sending Data
    # ----------------------------------------------------------------

    def send_angles(self, angles, force=False):
        """
        Send five servo angles to the Arduino.

        Args:
            angles: List of 5 integers (0-180).
            force: If True, send even if angles haven't changed.

        Returns:
            True if sent, False if skipped (duplicate) or error.
        """
        if not self.is_connected:
            return False

        # Validate: exactly 5 integer values
        if len(angles) != 5:
            print(f"WARNING: Expected 5 angles, got {len(angles)}")
            return False

        # Convert to list of ints and clamp to 0-180
        safe_angles = [max(0, min(180, int(a))) for a in angles]

        # Skip if identical to last sent (reduces serial traffic and jitter)
        if not force and self._last_sent == safe_angles:
            self.skip_count += 1
            return False

        try:
            # Build and send the message
            message = ",".join(str(a) for a in safe_angles) + "\n"
            self._serial.write(message.encode("utf-8"))

            self._last_sent = safe_angles[:]
            self.send_count += 1

            # Non-blocking: read responses without waiting
            self._read_all_responses()

            return True

        except serial.SerialException as e:
            print(f"Serial send error: {e}")
            self._connected = False
            return False

    def _read_all_responses(self):
        """Read and print any available responses from Arduino (non-blocking)."""
        try:
            while self._serial and self._serial.in_waiting > 0:
                line = self._serial.readline().decode("utf-8", errors="replace").strip()
                if line:
                    # Only print errors; suppress OK in real-time mode to keep console clean
                    if line.startswith("ERROR"):
                        print(f"  Arduino: {line}")
        except serial.SerialException:
            pass

    # ----------------------------------------------------------------
    # Port Discovery
    # ----------------------------------------------------------------

    @staticmethod
    def _find_arduino_port():
        """Auto-detect Arduino COM port."""
        ports = serial.tools.list_ports.comports()

        for port in ports:
            desc = (port.description or "").lower()
            mfr = (port.manufacturer or "").lower()

            if "arduino" in desc or "arduino" in mfr:
                print(f"  Auto-detected Arduino on {port.device}")
                return port.device
            if "ch340" in desc or "ch340" in mfr:
                print(f"  Auto-detected CH340 (Arduino clone) on {port.device}")
                return port.device

        return None

    @staticmethod
    def list_ports():
        """Print all available serial ports (same as find_arduino_port.py)."""
        ports = serial.tools.list_ports.comports()
        if not ports:
            print("No serial ports found.")
            return

        print(f"Found {len(ports)} serial port(s):")
        for port in ports:
            print(f"  {port.device} - {port.description}")


# --- Standalone test ---
if __name__ == "__main__":
    print("Testing serial communication module standalone...")
    print("This sends fixed test angles to the Arduino.\n")

    # Try to auto-detect, or set your port here
    conn = ArduinoConnection(port=None)  # Auto-detect

    if not conn.connect():
        print("\nCould not connect. Available ports:")
        ArduinoConnection.list_ports()
        exit(1)

    try:
        test_positions = [
            ("Middle position",  [90,  90,  90,  90,  90]),
            ("All open",         [0,   0,   0,   0,   0]),
            ("All closed",       [180, 180, 180, 180, 180]),
            ("Back to middle",   [90,  90,  90,  90,  90]),
        ]

        for name, angles in test_positions:
            print(f"  {name}: {angles}")
            conn.send_angles(angles, force=True)
            time.sleep(2)

        # Test duplicate prevention
        print("\nDuplicate prevention test:")
        conn.send_angles([90, 90, 90, 90, 90])  # Already at 90 → should skip
        print(f"  Skipped {conn.skip_count} duplicate(s)")

        print("\nAll tests passed!")

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        conn.disconnect()

