# 🤖 Vision-Based Robotic Hand Control

A computer vision-based robotic hand that mimics the movements of a human hand in real time using webcam-based hand tracking, finger joint angle calculation, and Arduino-controlled servo motors.

## 📌 Overview

This project connects a human hand to a robotic hand using computer vision and embedded systems.

A webcam captures the movement of the human hand. MediaPipe detects and tracks hand landmarks, which are then used to calculate the angles between finger joints.

These joint angles are converted into **finger bending percentages**, which are mapped to corresponding **servo motor angles**. The calculated servo angles are transmitted through serial communication to an Arduino, which controls the servo motors of the robotic hand.

The objective is to create a robotic hand that replicates human finger movements in real time.

## ⚙️ How It Works

The complete workflow follows this pipeline:

**Webcam → MediaPipe → Finger Joint Angles → Bending Percentage → Servo Angles → Serial Communication → Arduino → Servo Motors**

### 1. Hand Detection and Tracking
- Captures live video using OpenCV.
- Uses MediaPipe Hands to detect and track 21 hand landmarks.
- Identifies the positions of individual finger joints.

### 2. Finger Joint Angle Calculation
- Calculates angles between the joints of individual fingers using their landmark coordinates.
- Uses these angles to determine how much each finger is bent.

### 3. Bending Percentage Calculation
- Converts the calculated joint angles into a normalized bending percentage.
- Uses calibration values corresponding to an open hand and a closed hand.
- Produces a bending value for each of the five fingers.

### 4. Servo Angle Mapping
- Converts the bending percentages into corresponding servo motor angles.
- Maps the movement of each human finger to its corresponding robotic finger.

### 5. Arduino Communication
- Sends the calculated servo angles from Python to Arduino using serial communication.
- Uses PySerial for communication between the computer and Arduino.
- Arduino receives the values and controls the connected servo motors.

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| OpenCV | Webcam access and image processing |
| MediaPipe | Hand landmark detection and tracking |
| NumPy | Mathematical calculations |
| PySerial | Serial communication with Arduino |
| Arduino IDE | Programming the microcontroller |
| Servo Motors | Physical movement of robotic fingers |

## 📁 Project Structure

```text
robo_hand/
│
├── arduino_servo_control/
│   └── servo_control.ino
│
├── main.py
├── hand_tracking.py
├── finger_angles.py
├── serial_communication.py
├── webcam.py
│
└── README.md
```

### Python Files

- **main.py** – Main integration program that connects all the modules.
- **hand_tracking.py** – Detects and tracks the human hand using MediaPipe.
- **finger_angles.py** – Calculates finger joint angles and converts them into bending percentages and servo angles.
- **serial_communication.py** – Handles serial communication between Python and Arduino.
- **webcam.py** – Manages webcam capture and video frames.

## 💻 Requirements

### Software
- Python 3.x
- Arduino IDE
- VS Code (recommended)

### Python Libraries

Install the required libraries:

```bash
pip install opencv-python
pip install mediapipe
pip install numpy
pip install pyserial
```

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone YOUR_REPOSITORY_URL
```

```bash
cd robo_hand
```

### 2. Install Dependencies

```bash
pip install opencv-python mediapipe numpy pyserial
```

### 3. Upload Arduino Code

- Open `servo_control.ino` in Arduino IDE.
- Connect your Arduino board.
- Select the appropriate board and COM port.
- Upload the code.

### 4. Configure Serial Communication

Open `main.py` and configure:

```python
ARDUINO_PORT = "COM7"
BAUD_RATE = 9600
CAMERA_INDEX = 0
```

Change the COM port according to your Arduino connection.

### 5. Run the Project

```bash
python main.py
```

## 🎮 Controls

| Key | Function |
|---|---|
| `q` | Quit the program |
| `o` | Calibrate open hand |
| `c` | Calibrate closed hand |
| `p` | Pause/resume serial communication |
| `d` | Toggle debug information |
| `SPACE` | Send a single test command |

## 🔬 Key Concepts Explored

- Computer Vision
- Hand Landmark Detection
- Geometric Angle Calculation
- Coordinate-Based Motion Tracking
- Data Normalization and Mapping
- Serial Communication (UART)
- Microcontroller Programming
- Embedded Systems
- Human-Machine Interaction

## 🎯 Objective

The project explores how computer vision and embedded systems can work together to translate human movements into physical actions.

It provides practical experience in integrating software-based perception and mathematical calculations with hardware-based actuation.

---

**Built with Python, OpenCV, MediaPipe and Arduino.**
