"""
finger_angles.py - Finger Angle Calculation & Servo Mapping
=============================================================
Takes raw MediaPipe landmarks and produces servo angles.

Pipeline:
  landmarks → joint angles → bending % → smoothing → servo angles

What this module handles:
  - Calculating the bend angle of each finger from 3 joint points
  - Converting angles to bending percentages (0% = open, 100% = closed)
  - Exponential Moving Average (EMA) smoothing to reduce jitter
  - Per-finger calibration (each finger's open/closed range)
  - Per-finger servo mapping (each servo can have different limits)
  - Safety clamping to prevent mechanical damage

Design decisions:
  - Smoothing lives here (not in hand_tracking) because smoothing
    is about servo stability, not about hand detection quality.
  - Each finger has its OWN servo limits because real robotic hands
    have different mechanical ranges per finger.
  - Calibration is a simple open/closed capture — hold your hand
    open, press 'o'; make a fist, press 'c'. The system learns
    YOUR hand's range and maps it perfectly to YOUR servos.
"""

import math
import numpy as np


# ====================================================================
# FINGER CONFIGURATION
# ====================================================================
# Each finger uses 3 MediaPipe landmark indices to form an angle.
# Format: (name, point_A, point_B_vertex, point_C)
# The angle is measured AT point_B.
#
# MediaPipe landmark map:
#   Thumb:  2(MCP) → 3(IP) → 4(Tip)
#   Index:  5(MCP) → 6(PIP) → 7(DIP)
#   Middle: 9(MCP) → 10(PIP) → 11(DIP)
#   Ring:   13(MCP) → 14(PIP) → 15(DIP)
#   Pinky:  17(MCP) → 18(PIP) → 19(DIP)
# ====================================================================

FINGER_JOINTS = [
    {"name": "Thumb",  "points": (2, 3, 4)},
    {"name": "Index",  "points": (5, 6, 7)},
    {"name": "Middle", "points": (9, 10, 11)},
    {"name": "Ring",   "points": (13, 14, 15)},
    {"name": "Pinky",  "points": (17, 18, 19)},
]

# Default angle ranges for bending percentage calculation.
# "open_angle" = typical joint angle when finger is straight (open hand).
# "closed_angle" = typical joint angle when finger is fully bent (fist).
# These are starting defaults — calibration overrides them.
DEFAULT_ANGLE_RANGES = [
    {"open_angle": 165, "closed_angle": 110},   # Thumb (smaller range)
    {"open_angle": 175, "closed_angle": 90},     # Index
    {"open_angle": 175, "closed_angle": 90},     # Middle
    {"open_angle": 175, "closed_angle": 90},     # Ring
    {"open_angle": 175, "closed_angle": 90},     # Pinky
]

# Default servo limits per finger (degrees).
# YOUR robotic hand may need different values!
# servo_min = angle when finger is fully OPEN (0% bend)
# servo_max = angle when finger is fully CLOSED (100% bend)
# If a servo moves the wrong way, swap min and max.
DEFAULT_SERVO_LIMITS = [
    {"servo_min": 0, "servo_max": 180},   # Thumb
    {"servo_min": 0, "servo_max": 180},   # Index
    {"servo_min": 0, "servo_max": 180},   # Middle
    {"servo_min": 0, "servo_max": 180},   # Ring
    {"servo_min": 0, "servo_max": 180},   # Pinky
]


class FingerAngleCalculator:
    """Calculates finger bending and maps to servo angles."""

    def __init__(self, smoothing_alpha=0.35, servo_limits=None, angle_ranges=None):
        """
        Args:
            smoothing_alpha: EMA factor (0-1). Lower = smoother but slower.
                             0.35 is a good balance for real-time control.
            servo_limits: List of 5 dicts with 'servo_min' and 'servo_max'.
                          If None, uses DEFAULT_SERVO_LIMITS.
            angle_ranges: List of 5 dicts with 'open_angle' and 'closed_angle'.
                          If None, uses DEFAULT_ANGLE_RANGES.
        """
        self.alpha = smoothing_alpha
        self.servo_limits = servo_limits or [d.copy() for d in DEFAULT_SERVO_LIMITS]
        self.angle_ranges = angle_ranges or [d.copy() for d in DEFAULT_ANGLE_RANGES]

        # Smoothing state — stores the previous smoothed percentage per finger
        self._smooth_pct = [0.0, 0.0, 0.0, 0.0, 0.0]

        # Calibration state
        self._calibrated = False

    # ----------------------------------------------------------------
    # Core Calculation
    # ----------------------------------------------------------------

    def _calculate_joint_angle(self, p1, p2, p3):
        """
        Calculate the angle at p2 formed by the vectors p1→p2 and p3→p2.

        This is the same calculation from the previous hand_tracking.py,
        moved here because angle math belongs with the angle module.
        """
        v1 = np.array([p1.x - p2.x, p1.y - p2.y, p1.z - p2.z])
        v2 = np.array([p3.x - p2.x, p3.y - p2.y, p3.z - p2.z])

        dot_prod = np.dot(v1, v2)
        mag1 = np.linalg.norm(v1)
        mag2 = np.linalg.norm(v2)

        # Avoid division by zero
        if mag1 == 0 or mag2 == 0:
            return 180.0  # Treat as fully open

        cos_theta = dot_prod / (mag1 * mag2)
        cos_theta = max(-1.0, min(1.0, cos_theta))  # Clamp for acos safety

        return math.degrees(math.acos(cos_theta))

    def _angle_to_percentage(self, angle, finger_index):
        """
        Convert a joint angle to a bending percentage (0-100).
        0% = finger open (straight), 100% = finger closed (fist).
        """
        open_angle = self.angle_ranges[finger_index]["open_angle"]
        closed_angle = self.angle_ranges[finger_index]["closed_angle"]

        # np.interp maps:  angle in [closed, open] → output in [100, 0]
        percentage = np.interp(angle, [closed_angle, open_angle], [100, 0])
        return float(np.clip(percentage, 0, 100))

    def _smooth(self, raw_pct, finger_index):
        """
        Apply Exponential Moving Average to reduce jitter.
        EMA formula: smoothed = alpha * new + (1 - alpha) * previous
        """
        self._smooth_pct[finger_index] = (
            self.alpha * raw_pct +
            (1 - self.alpha) * self._smooth_pct[finger_index]
        )
        return self._smooth_pct[finger_index]

    def _percentage_to_servo(self, percentage, finger_index):
        """
        Map a bending percentage (0-100) to a servo angle.
        Each finger has its own servo_min and servo_max.
        """
        s_min = self.servo_limits[finger_index]["servo_min"]
        s_max = self.servo_limits[finger_index]["servo_max"]

        # Linear mapping: 0% → servo_min, 100% → servo_max
        servo_angle = np.interp(percentage, [0, 100], [s_min, s_max])

        # Safety: clamp to the actual servo range (handles inverted ranges too)
        low = min(s_min, s_max)
        high = max(s_min, s_max)
        return int(np.clip(servo_angle, low, high))

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def process_landmarks(self, landmarks):
        """
        Full pipeline: landmarks → bending percentages → servo angles.

        Args:
            landmarks: List of 21 MediaPipe landmark objects.

        Returns:
            (percentages, servo_angles)
            percentages: list of 5 floats (0-100), smoothed bending per finger.
            servo_angles: list of 5 ints, the servo command per finger.
        """
        percentages = []
        servo_angles = []

        for i, finger in enumerate(FINGER_JOINTS):
            p_a, p_b, p_c = finger["points"]

            # Step 1: Calculate raw joint angle
            raw_angle = self._calculate_joint_angle(
                landmarks[p_a], landmarks[p_b], landmarks[p_c]
            )

            # Step 2: Convert to bending percentage
            raw_pct = self._angle_to_percentage(raw_angle, i)

            # Step 3: Smooth the percentage
            smooth_pct = self._smooth(raw_pct, i)

            # Step 4: Map to servo angle
            servo = self._percentage_to_servo(smooth_pct, i)

            percentages.append(round(smooth_pct, 1))
            servo_angles.append(servo)

        return percentages, servo_angles

    # ----------------------------------------------------------------
    # Calibration
    # ----------------------------------------------------------------

    def calibrate_open(self, landmarks):
        """
        Capture the 'fully open' hand position.
        Call this when the user holds their hand flat and open.
        Records the joint angle for each finger as the 'open' reference.
        """
        print("\n--- Calibrating OPEN hand position ---")
        for i, finger in enumerate(FINGER_JOINTS):
            p_a, p_b, p_c = finger["points"]
            angle = self._calculate_joint_angle(
                landmarks[p_a], landmarks[p_b], landmarks[p_c]
            )
            self.angle_ranges[i]["open_angle"] = round(angle, 1)
            print(f"  {finger['name']}: open angle = {angle:.1f}°")

        self._calibrated = True
        print("Open calibration saved!\n")

    def calibrate_closed(self, landmarks):
        """
        Capture the 'fully closed' (fist) position.
        Call this when the user makes a tight fist.
        """
        print("\n--- Calibrating CLOSED hand position ---")
        for i, finger in enumerate(FINGER_JOINTS):
            p_a, p_b, p_c = finger["points"]
            angle = self._calculate_joint_angle(
                landmarks[p_a], landmarks[p_b], landmarks[p_c]
            )
            self.angle_ranges[i]["closed_angle"] = round(angle, 1)
            print(f"  {finger['name']}: closed angle = {angle:.1f}°")

        self._calibrated = True
        print("Closed calibration saved!\n")

    @property
    def is_calibrated(self):
        return self._calibrated

    @property
    def finger_names(self):
        return [f["name"] for f in FINGER_JOINTS]


# --- Standalone test ---
if __name__ == "__main__":
    import cv2
    from webcam import WebcamCapture
    from hand_tracking import HandDetector

    print("Testing finger angles standalone...")
    print("Press 'o' to calibrate OPEN, 'c' to calibrate CLOSED, 'q' to quit.")

    cam = WebcamCapture()
    detector = HandDetector()
    calculator = FingerAngleCalculator()

    while cam.is_open():
        frame = cam.read_frame()
        if frame is None:
            break

        landmarks, label = detector.find_hand(frame)
        frame = detector.draw_landmarks(frame)

        if landmarks is not None:
            percentages, servo_angles = calculator.process_landmarks(landmarks)

            # Display finger data
            names = calculator.finger_names
            for i in range(5):
                text = f"{names[i]}: {percentages[i]:.0f}% -> servo {servo_angles[i]}"
                cv2.putText(frame, text, (10, 60 + i * 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

            cv2.putText(frame, f"Hand: {label}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        else:
            cv2.putText(frame, "No hand detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        cal_text = "CALIBRATED" if calculator.is_calibrated else "Default ranges"
        cv2.putText(frame, cal_text, (10, frame.shape[0] - 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"FPS: {int(cam.fps)}", (10, frame.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow("Finger Angles Test", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('o') and landmarks is not None:
            calculator.calibrate_open(landmarks)
        elif key == ord('c') and landmarks is not None:
            calculator.calibrate_closed(landmarks)

    cam.release()

