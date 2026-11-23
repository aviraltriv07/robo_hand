import cv2
import time

def main():
    # 1. Access the laptop's webcam
    # '0' is the default camera. If you have an external one, it might be 1.
    cap = cv2.VideoCapture(0)

    # 6. Handle webcam errors properly
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Variables for FPS calculation
    prev_time = 0
    new_time = 0

    print("Webcam started. Press 'q' to exit.")

    # 2. Capture live video continuously
    while True:
        # Capture frame-by-frame
        # 'ret' is a boolean (True if frame is captured), 'frame' is the image data
        ret, frame = cap.read()

        if not ret:
            print("Error: Failed to grab frame.")
            break

        # 4. Calculate FPS
        new_time = time.time()
        # FPS = 1 / (time taken for this frame)
        fps = 1 / (new_time - prev_time)
        prev_time = new_time

        # Get resolution
        height, width, channels = frame.shape
        resolution_text = f"Res: {width}x{height}"
        fps_text = f"FPS: {int(fps)}"

        # Display resolution and FPS on the frame
        # cv2.putText(image, text, position, font, scale, color, thickness)
        cv2.putText(frame, resolution_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        cv2.putText(frame, fps_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        # 3. Display the video in a window
        cv2.imshow('Robotic Hand - Vision Stage 1', frame)

        # 5. Allow exit by pressing 'q'
        # waitKey(1) waits for 1ms for a key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 5. Proper Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Program exited successfully.")

if __name__ == "__main__":
    main()
