"""
Serial Communication Test - Robotic Hand
=========================================
Sends FIXED servo angle values to Arduino over serial.
Use this to verify the serial link works BEFORE integrating MediaPipe.

Steps to use:
  1. Upload arduino_servo_control.ino to your Arduino Uno.
  2. Run find_arduino_port.py to find your COM port.
  3. Set ARDUINO_PORT below to that COM port.
  4. Run this script.
"""

import serial
import time
import sys

# ----------------------------------------------------------------
# CONFIGURATION - Change these to match your setup!
# ----------------------------------------------------------------
ARDUINO_PORT = "COM3"   # <-- Change to YOUR port (run find_arduino_port.py)
BAUD_RATE = 9600        # Must match Serial.begin(9600) in Arduino code
# ----------------------------------------------------------------


def connect_to_arduino(port, baud_rate):
    """
    Open a serial connection to the Arduino.
    Returns the serial object if successful, None otherwise.
    """
    try:
        print(f"Connecting to Arduino on {port} at {baud_rate} baud...")
        arduino = serial.Serial(
            port=port,
            baudrate=baud_rate,
            timeout=2  # Wait up to 2 seconds for a response
        )

        # IMPORTANT: Arduino resets when you open a serial connection.
        # We must wait for it to reboot and run setup().
        time.sleep(2)

        # Read the "READY" message that Arduino sends in setup()
        while arduino.in_waiting > 0:
            line = arduino.readline().decode("utf-8").strip()
            print(f"  Arduino says: {line}")

        print("Connected successfully!\n")
        return arduino

    except serial.SerialException as e:
        print(f"ERROR: Could not connect to {port}")
        print(f"  Reason: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Is the Arduino plugged in?")
        print("  2. Is the correct COM port set? Run find_arduino_port.py")
        print("  3. Is another program (Arduino IDE Serial Monitor) using the port?")
        return None


def send_angles(arduino, angles):
    """
    Send five servo angles to the Arduino.
    Format: "30,45,60,90,20\n"
    """
    # Build the comma-separated string
    message = ",".join(str(a) for a in angles) + "\n"

    # Send it as bytes over the serial connection
    arduino.write(message.encode("utf-8"))

    # Give Arduino a moment to process
    time.sleep(0.05)

    # Read any response from Arduino
    while arduino.in_waiting > 0:
        response = arduino.readline().decode("utf-8").strip()
        print(f"  Arduino response: {response}")


def test_fixed_values(arduino):
    """Test with several fixed angle positions."""

    # Each set is [Thumb, Index, Middle, Ring, Pinky]
    test_positions = [
        ("All at 90 (middle)",    [90,  90,  90,  90,  90]),
        ("All open at 0",        [0,   0,   0,   0,   0]),
        ("All closed at 180",    [180, 180, 180, 180, 180]),
        ("Fingers spread",       [30,  60,  90, 120, 150]),
        ("Only index pointing",  [180, 0,  180, 180, 180]),
        ("Back to middle",       [90,  90,  90,  90,  90]),
    ]

    for name, angles in test_positions:
        print(f"Position: {name}  ->  {angles}")
        send_angles(arduino, angles)
        time.sleep(2)  # Wait 2 seconds so you can observe the servos
        print()


def test_sweep(arduino):
    """Slowly sweep all servos from 0 to 180 and back."""

    print("Sweeping all servos 0 -> 180...")
    for angle in range(0, 181, 10):
        angles = [angle] * 5
        print(f"  All servos at {angle} degrees")
        send_angles(arduino, angles)
        time.sleep(0.3)

    print()
    print("Sweeping all servos 180 -> 0...")
    for angle in range(180, -1, -10):
        angles = [angle] * 5
        print(f"  All servos at {angle} degrees")
        send_angles(arduino, angles)
        time.sleep(0.3)

    print()


def main():
    # --- Step 1: Connect ---
    arduino = connect_to_arduino(ARDUINO_PORT, BAUD_RATE)
    if arduino is None:
        sys.exit(1)

    try:
        # --- Step 2: Test fixed positions ---
        print("=" * 50)
        print("  TEST 1: Fixed Positions")
        print("=" * 50)
        test_fixed_values(arduino)

        # --- Step 3: Test sweep ---
        print("=" * 50)
        print("  TEST 2: Servo Sweep")
        print("=" * 50)
        test_sweep(arduino)

        print("All tests completed successfully!")

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        # Always close the serial connection when done
        arduino.close()
        print("Serial connection closed.")


if __name__ == "__main__":
    main()

