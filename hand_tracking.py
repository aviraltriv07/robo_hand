import cv2
import mediapipe as mp
import time
import math
import numpy as np

class HandTracker:
    def __init__(self, max_hands=1, detection_con=0.7, track_con=0.5):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_con,
            min_tracking_confidence=track_con
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Smoothing memory (Exponential Moving Average)
        self.prev_smooth_values = [0, 0, 0, 0, 0] # Thumb, Index, Middle, Ring, Pinky
        self.alpha = 0.3 # Smoothing factor (0-1), lower is smoother but slower

    def calculate_angle(self, p1, p2, p3):
        """Calculates the angle at p2 formed by p1-p2 and p3-p2."""
        # Convert landmarks to numpy arrays
        v1 = np.array([p1.x - p2.x, p1.y - p2.y, p1.z - p2.z])
        v2 = np.array([p3.x - p2.x, p3.y - p2.y, p3.z - p2.z])
        
        # Dot product and magnitudes
        dot_prod = np.dot(v1, v2)
        mag1 = np.linalg.norm(v1)
        mag2 = np.linalg.norm(v2)
        
        # Guard against division by zero or precision errors
        cos_theta = dot_prod / (mag1 * mag2)
        cos_theta = max(-1.0, min(1.0, cos_theta))
        
        angle = math.degrees(math.acos(cos_theta))
        return angle

    def get_bending_percentage(self, angle, min_angle, max_angle):
        """Maps angle to 0-100% bending. 
        Usually 180 deg = 0% (straight), 90 deg = 100% (bent)"""
        percentage = np.interp(angle, [max_angle, min_angle], [100, 0])
        return round(percentage, 1)

    def get_thumb_bend(self, landmarks):
        # Using points 2, 3, 4 (MCP, IP, Tip)
        angle = self.calculate_angle(landmarks[2], landmarks[3], landmarks[4])
        # Thumb has a different range, approx 165 (open) to 110 (closed)
        return self.get_bending_percentage(angle, 165, 110)

    def get_index_bend(self, landmarks):
        # Using points 5, 6, 7 (MCP, PIP, DIP)
        angle = self.calculate_angle(landmarks[5], landmarks[6], landmarks[7])
        return self.get_bending_percentage(angle, 175, 90)

    def get_middle_bend(self, landmarks):
        angle = self.calculate_angle(landmarks[9], landmarks[10], landmarks[11])
        return self.get_bending_percentage(angle, 175, 90)

    def get_ring_bend(self, landmarks):
        angle = self.calculate_angle(landmarks[13], landmarks[14], landmarks[15])
        return self.get_bending_percentage(angle, 175, 90)

    def get_pinky_bend(self, landmarks):
        angle = self.calculate_angle(landmarks[17], landmarks[18], landmarks[19])
        return self.get_bending_percentage(angle, 175, 90)

    def process_frame(self, frame):
        h, w, c = frame.shape
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        
        finger_values = [0, 0, 0, 0, 0]

        if results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                hand_label = results.multi_handedness[hand_idx].classification[0].label
                
                # Draw landmarks
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                # Calculate raw bending
                lms = hand_landmarks.landmark
                raw_values = [
                    self.get_thumb_bend(lms),
                    self.get_index_bend(lms),
                    self.get_middle_bend(lms),
                    self.get_ring_bend(lms),
                    self.get_pinky_bend(lms)
                ]
                
                # Apply Smoothing (EMA)
                for i in range(5):
                    self.prev_smooth_values[i] = (self.alpha * raw_values[i]) + \
                                                ((1 - self.alpha) * self.prev_smooth_values[i])
                    finger_values[i] = int(self.prev_smooth_values[i])

                # Display info
                labels = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
                for i, val in enumerate(finger_values):
                    cv2.putText(frame, f"{labels[i]}: {val}%", (10, 60 + (i * 30)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                cv2.putText(frame, f"Hand: {hand_label}", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        return frame

def main():
    tracker = HandTracker(max_hands=1)
    cap = cv2.VideoCapture(0)
    prev_time = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        frame = tracker.process_frame(frame)

        # FPS calculation
        new_time = time.time()
        fps = 1 / (new_time - prev_time)
        prev_time = new_time
        cv2.putText(frame, f"FPS: {int(fps)}", (10, frame.shape[0] - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        cv2.imshow('Finger Bending Analysis', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
