"""
main.py - Robotic Hand Integration
=====================================
The main program that connects everything together:

  Webcam → MediaPipe → Finger Angles → Serial → Arduino → Servos

This is the ONLY file you run. It imports all other modules.

Controls:
  q       - Quit
  o       - Calibrate open hand (hold hand flat and open, then press)
  c       - Calibrate closed hand (make a fist, then press)
  p       - Pause/resume serial sending (servos hold position)
  d       - Toggle debug overlay on the video
  SPACE   - Send a single test command (all servos to 90 degrees)

Usage:
  1. Upload arduino_servo_control.ino to your Arduino.
  2. Find your COM port: python find_arduino_port.py
  3. Set ARDUINO_PORT below (or set to None for auto-detect).
  4. Run: python main.py
"""

import cv2
import time
import sys

# Import our modules
from webcam import WebcamCapture
from hand_tracking import HandDetector
from finger_angles import FingerAngleCalculator
from serial_communication import ArduinoConnection


# ====================================================================
# CONFIGURATION — Adjust these for your setup
# ====================================================================

# Serial port: Set to your COM port, or None to auto-detect
ARDUINO_PORT = "COM7"       # <-- CHANGE THIS (or use None)
BAUD_RATE = 9600

# Camera
CAMERA_INDEX = 0            # 0 = default laptop webcam

# Servo limits per finger [Thumb, Index, Middle, Ring, Pinky]
# Adjust these to match YOUR robotic hand's mechanical range!
# servo_min = servo angle when finger is OPEN (0% bend)
# servo_max = servo angle when finger is CLOSED (100% bend)
SERVO_LIMITS = [
    {"servo_min": 0, "servo_max": 180},   # Thumb
    {"servo_min": 0, "servo_max": 180},   # Index
    {"servo_min": 0, "servo_max": 180},   # Middle
    {"servo_min": 0, "servo_max": 180},   # Ring
    {"servo_min": 0, "servo_max": 180},   # Pinky
]

# Smoothing factor (0-1): lower = smoother but more lag
SMOOTHING_ALPHA = 0.35

# How many milliseconds between serial sends (rate limiting)
# 50ms = 20 updates/second, plenty for smooth servo movement
SEND_INTERVAL_MS = 50

# ====================================================================


def draw_hud(frame, fps, percentages, servo_angles, finger_names,
             hand_detected, serial_connected, is_paused, is_calibrated,
             show_debug):
    """Draw the heads-up display overlay on the video frame."""

    h, w = frame.shape[:2]

    # --- Status bar at top ---
    # Hand status
    if hand_detected:
        cv2.putText(frame, "Hand: Detected", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "Hand: Not found", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # Serial status
    if not serial_connected:
        serial_text, serial_color = "Serial: Disconnected", (0, 0, 255)
    elif is_paused:
        serial_text, serial_color = "Serial: PAUSED", (0, 165, 255)
    else:
        serial_text, serial_color = "Serial: Active", (0, 255, 0)

    cv2.putText(frame, serial_text, (w - 280, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, serial_color, 2)

    # --- Finger data ---
    if percentages is not None and show_debug:
        for i in range(5):
            # Finger name, bending %, and servo angle
            text = f"{finger_names[i]}: {percentages[i]:5.1f}%  servo:{servo_angles[i]:3d}"
            cv2.putText(frame, text, (10, 70 + i * 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)

            # Visual bar showing bending percentage
            bar_x = 350
            bar_w = 150
            bar_y = 58 + i * 28
            filled = int(bar_w * percentages[i] / 100)

            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 16),
                          (100, 100, 100), 1)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + filled, bar_y + 16),
                          (0, 255, 255), -1)

    # --- Bottom status bar ---
    cv2.putText(frame, f"FPS: {int(fps)}", (10, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cal_text = "CAL: Yes" if is_calibrated else "CAL: Default"
    cv2.putText(frame, cal_text, (130, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    controls = "Q:Quit  O:CalOpen  C:CalClose  P:Pause  D:Debug"
    cv2.putText(frame, controls, (10, h - 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    return frame


def main():
    print("=" * 60)
    print("  ROBOTIC HAND - Vision-Based Servo Control")
    print("=" * 60)
    print()

    # ----------------------------------------------------------------
    # Step 1: Initialize all modules
    # ----------------------------------------------------------------

    # Webcam
    try:
        cam = WebcamCapture(camera_index=CAMERA_INDEX)
    except RuntimeError as e:
        print(f"FATAL: {e}")
        sys.exit(1)

    # Hand detector (MediaPipe)
    detector = HandDetector(max_hands=1, detection_con=0.7, track_con=0.5)

    # Finger angle calculator (with per-finger servo limits)
    calculator = FingerAngleCalculator(
        smoothing_alpha=SMOOTHING_ALPHA,
        servo_limits=SERVO_LIMITS
    )

    # Arduino serial connection
    arduino = ArduinoConnection(port=ARDUINO_PORT, baud_rate=BAUD_RATE)
    serial_ok = arduino.connect()

    if not serial_ok:
        print("\nWARNING: Running without Arduino. Vision will work, servos won't.")
        print("  Fix the connection and restart, or continue for testing.\n")

    # ----------------------------------------------------------------
    # Step 2: Main loop state
    # ----------------------------------------------------------------

    is_paused = False       # Pause serial sending
    show_debug = True       # Show debug overlay
    last_send_time = 0      # Rate limiting for serial sends

    # What to do when the hand disappears:
    # Hold the last known servo angles (don't snap to zero)
    last_servo_angles = [0, 0, 0, 180, 180]
    last_percentages = [0.0, 0.0, 0.0, 0.0, 0.0]

    # Track how many consecutive frames with no hand
    frames_without_hand = 0
    HAND_TIMEOUT_FRAMES = 30  # After this many frames, consider hand gone

    print("System ready! Show your hand to the camera.")
    print("Press 'o' with hand open to calibrate, 'c' with fist to calibrate.\n")

    # ----------------------------------------------------------------
    # Step 3: Main loop
    # ----------------------------------------------------------------

    try:
        while cam.is_open():
            # --- Read frame ---
            frame = cam.read_frame()
            if frame is None:
                print("Failed to read frame. Camera disconnected?")
                break

            # --- Detect hand ---
            landmarks, hand_label = detector.find_hand(frame, target_hand="Left")
            frame = detector.draw_landmarks(frame)

            hand_detected = landmarks is not None
            current_percentages = None
            current_servo_angles = None

            if hand_detected:
                frames_without_hand = 0

                # --- Calculate finger angles ---
                percentages, servo_angles = calculator.process_landmarks(landmarks)

                current_percentages = percentages
                current_servo_angles = servo_angles
                last_percentages = percentages
                last_servo_angles = servo_angles

                # --- Send to Arduino (rate-limited) ---
                current_time_ms = time.time() * 1000

                if (not is_paused
                        and arduino.is_connected
                        and current_time_ms - last_send_time >= SEND_INTERVAL_MS):

                    arduino.send_angles(servo_angles)
                    last_send_time = current_time_ms

            else:
                frames_without_hand += 1

                # Show last known values in the HUD even when hand is gone
                current_percentages = last_percentages
                current_servo_angles = last_servo_angles

                # The servos keep their last position automatically
                # (we simply stop sending new commands)

            # --- Draw HUD ---
            frame = draw_hud(
                frame,
                fps=cam.fps,
                percentages=current_percentages,
                servo_angles=current_servo_angles,
                finger_names=calculator.finger_names,
                hand_detected=hand_detected,
                serial_connected=arduino.is_connected,
                is_paused=is_paused,
                is_calibrated=calculator.is_calibrated,
                show_debug=show_debug
            )

            # --- Display ---
            cv2.imshow("Robotic Hand Control", frame)

            # --- Handle keyboard input ---
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("Quit requested.")
                break

            elif key == ord('o'):
                # Calibrate open hand
                if landmarks is not None:
                    calculator.calibrate_open(landmarks)
                else:
                    print("Cannot calibrate: no hand detected!")

            elif key == ord('c'):
                # Calibrate closed hand (fist)
                if landmarks is not None:
                    calculator.calibrate_closed(landmarks)
                else:
                    print("Cannot calibrate: no hand detected!")

            elif key == ord('p'):
                # Toggle pause
                is_paused = not is_paused
                state = "PAUSED" if is_paused else "RESUMED"
                print(f"Serial sending {state}")

            elif key == ord('d'):
                # Toggle debug overlay
                show_debug = not show_debug

            elif key == ord(' '):
                # Test: send all servos to 90°
                if arduino.is_connected:
                    print("Test: sending all servos to 90°")
                    arduino.send_angles([90, 90, 90, 90, 90], force=True)

    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl+C).")

    # ----------------------------------------------------------------
    # Step 4: Cleanup
    # ----------------------------------------------------------------

    print("\nShutting down...")

    # Move servos to safe neutral position before disconnecting
    if arduino.is_connected:
        print("Moving servos to neutral position (90°)...")
        arduino.send_angles([90, 90, 90, 90, 90], force=True)
        time.sleep(0.5)

    arduino.disconnect()
    cam.release()
    print("Done.")


if __name__ == "__main__":
    main()

