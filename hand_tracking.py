"""
hand_tracking.py - MediaPipe Hand Detection Module
====================================================
Detects a hand in a camera frame using MediaPipe and returns the
21 hand landmarks. This module ONLY does detection — it does not
calculate finger angles (that's finger_angles.py's job).

What changed from the previous hand_tracking.py:
  - Removed angle calculation (moved to finger_angles.py)
  - Removed smoothing (moved to finger_angles.py)
  - Removed frame flipping (webcam.py handles that now)
  - Returns raw landmarks so other modules can use them
  - Cleaner separation: this module = "find the hand"

Usage:
    from hand_tracking import HandDetector

    detector = HandDetector()
    landmarks, hand_label = detector.find_hand(frame)
    if landmarks is not None:
        # landmarks is a list of 21 MediaPipe landmark objects
        frame = detector.draw_landmarks(frame)
"""

import mediapipe as mp


class HandDetector:
    """Detects a single hand and provides its 21 landmarks."""

    def __init__(self, max_hands=1, detection_con=0.7, track_con=0.5):
        """
        Initialize MediaPipe hand detection.

        Args:
            max_hands: Maximum number of hands to detect.
            detection_con: Minimum confidence for initial detection (0-1).
            track_con: Minimum confidence for frame-to-frame tracking (0-1).
        """
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_con,
            min_tracking_confidence=track_con
        )
        self.mp_draw = mp.solutions.drawing_utils

        # Store latest results for drawing
        self._latest_results = None
        self._latest_hand_landmarks = None

    def find_hand(self, frame, target_hand="Left"):
        """
        Process a frame and find the target hand.

        Args:
            frame: BGR image (already flipped by webcam.py).
            target_hand: Which hand to track — "Left" or "Right".
                         Note: MediaPipe labels are from the camera's
                         perspective, but since we flip the image in
                         webcam.py, "Left" in MediaPipe = your left hand.

        Returns:
            (landmarks, hand_label) if hand found, (None, None) otherwise.
            landmarks is a list of 21 MediaPipe NormalizedLandmark objects.
        """
        import cv2

        # MediaPipe needs RGB, OpenCV gives BGR
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._latest_results = self.hands.process(rgb_frame)
        self._latest_hand_landmarks = None

        if not self._latest_results.multi_hand_landmarks:
            return None, None

        # Find the target hand
        for hand_idx, hand_landmarks in enumerate(self._latest_results.multi_hand_landmarks):
            label = self._latest_results.multi_handedness[hand_idx].classification[0].label

            if label == target_hand:
                self._latest_hand_landmarks = hand_landmarks
                return hand_landmarks.landmark, label

        return None, None

    def draw_landmarks(self, frame):
        """
        Draw the detected hand skeleton on the frame.
        Call this AFTER find_hand().
        """
        if self._latest_hand_landmarks is not None:
            self.mp_draw.draw_landmarks(
                frame,
                self._latest_hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS
            )
        return frame


# --- Standalone test ---
if __name__ == "__main__":
    import cv2
    from webcam import WebcamCapture

    print("Testing hand detection standalone...")
    cam = WebcamCapture()
    detector = HandDetector()

    while cam.is_open():
        frame = cam.read_frame()
        if frame is None:
            break

        landmarks, label = detector.find_hand(frame)
        frame = detector.draw_landmarks(frame)

        status = f"Hand: {label}" if label else "No hand detected"
        cv2.putText(frame, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.putText(frame, f"FPS: {int(cam.fps)}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow("Hand Detection Test", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
