"""
webcam.py - Webcam Capture Module
==================================
Handles opening the camera, reading frames, flipping, and cleanup.
Extracted from webcam_test.py so other modules can reuse it cleanly.

Usage:
    from webcam import WebcamCapture

    cam = WebcamCapture(camera_index=0)
    while True:
        frame = cam.read_frame()
        if frame is None:
            break
        # ... do something with frame ...
    cam.release()
"""

import cv2
import time


class WebcamCapture:
    """Manages the laptop webcam with FPS tracking."""

    def __init__(self, camera_index=0, flip_horizontal=True):
        """
        Open the webcam.

        Args:
            camera_index: Which camera to use (0 = default laptop webcam).
            flip_horizontal: Mirror the image so it feels natural
                             (your right hand appears on the right side).
        """
        self.camera_index = camera_index
        self.flip = flip_horizontal

        # Open the camera
        self.cap = cv2.VideoCapture(camera_index)

        if not self.cap.isOpened():
            raise RuntimeError(
                f"Could not open webcam (index {camera_index}). "
                "Is another program using it?"
            )

        # FPS tracking
        self._prev_time = time.time()
        self.fps = 0

        # Read one frame to get resolution
        ret, test_frame = self.cap.read()
        if ret:
            self.height, self.width = test_frame.shape[:2]
        else:
            self.width, self.height = 640, 480  # Fallback

        print(f"Webcam opened: {self.width}x{self.height} (camera {camera_index})")

    def read_frame(self):
        """
        Read one frame from the webcam.

        Returns:
            The frame (numpy array), or None if the read failed.
            Frame is already flipped if flip_horizontal was True.
        """
        ret, frame = self.cap.read()

        if not ret:
            return None

        # Mirror the image so left/right feels natural
        if self.flip:
            frame = cv2.flip(frame, 1)

        # Update FPS calculation
        current_time = time.time()
        time_diff = current_time - self._prev_time
        if time_diff > 0:
            self.fps = 1.0 / time_diff
        self._prev_time = current_time

        return frame

    def is_open(self):
        """Check if the webcam is still available."""
        return self.cap.isOpened()

    def release(self):
        """Release the webcam and close all OpenCV windows."""
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        print("Webcam released.")


# --- Standalone test ---
if __name__ == "__main__":
    print("Testing webcam module standalone...")
    cam = WebcamCapture(camera_index=0)

    while cam.is_open():
        frame = cam.read_frame()
        if frame is None:
            break

        cv2.putText(frame, f"FPS: {int(cam.fps)}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Webcam Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()

