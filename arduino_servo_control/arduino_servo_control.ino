// ============================================================
// Arduino Servo Control - Robotic Hand (Updated)
// ============================================================
// Receives five servo angle values over Serial from Python.
// Data format expected: "30,45,60,90,20\n"
// Each value maps to one finger: Thumb, Index, Middle, Ring, Pinky
//
// UPDATED for integration:
//   - Per-finger safety limits (each servo can have different range)
//   - Reduced serial timeout for faster real-time response
//   - Smoother servo movement with optional step limiting
//   - Cleaner error handling
// ============================================================

#include <Servo.h>

// --- Configuration ---
const int NUM_SERVOS = 5;

// Which digital pins the servos are connected to
const int SERVO_PINS[NUM_SERVOS] = {3, 5, 6, 9, 10};

// Friendly names for debug printing
const char* FINGER_NAMES[NUM_SERVOS] = {
  "Thumb", "Index", "Middle", "Ring", "Pinky"
};

// Per-finger safety angle limits (degrees).
// Adjust these to match YOUR specific servo/hand design!
// If a finger can only move from 10° to 160°, set those limits here.
const int MIN_ANGLES[NUM_SERVOS] = {0, 0, 0, 0, 0};
const int MAX_ANGLES[NUM_SERVOS] = {180, 180, 180, 180, 180};

// Maximum degrees a servo can move in one update.
// This prevents sudden jumps that could damage the mechanism.
// Set to 180 to disable (allow any jump). Try 15-30 for smooth motion.
const int MAX_STEP = 180;

// --- Global Variables ---
Servo servos[NUM_SERVOS];
int currentAngles[NUM_SERVOS] = {90, 90, 90, 90, 90};  // Start at mid-position

// Buffer for incoming serial data
String inputBuffer = "";

void setup() {
  // Start serial communication at 9600 baud
  // IMPORTANT: Python must use the SAME baud rate!
  Serial.begin(9600);

  // Reduce default serial timeout from 1000ms to 100ms.
  // This makes Serial.readStringUntil() return faster if
  // it doesn't find a newline, keeping the loop responsive.
  Serial.setTimeout(100);

  // Attach each servo to its pin
  for (int i = 0; i < NUM_SERVOS; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(currentAngles[i]);  // Move to starting position
  }

  // Let Python know the Arduino is ready
  Serial.println("READY");

  // Brief delay to let servos reach starting position
  delay(500);
}

void loop() {
  // Check if any serial data has arrived
  if (Serial.available() > 0) {

    // Read everything up to the newline character '\n'
    inputBuffer = Serial.readStringUntil('\n');

    // Remove any trailing whitespace or carriage return '\r'
    inputBuffer.trim();

    // Ignore empty strings
    if (inputBuffer.length() > 0) {
      parseAndApply(inputBuffer);
    }
  }
}

void parseAndApply(String data) {
  // We expect exactly 5 comma-separated integers, e.g. "30,45,60,90,20"
  int angles[NUM_SERVOS];
  int parseIndex = 0;

  // Walk through the string, extracting numbers between commas
  int startPos = 0;
  for (unsigned int i = 0; i < data.length(); i++) {
    if (data.charAt(i) == ',' || i == data.length() - 1) {
      // Extract the substring for this number
      String token;
      if (data.charAt(i) == ',') {
        token = data.substring(startPos, i);
      } else {
        // Last value (no trailing comma)
        token = data.substring(startPos, i + 1);
      }

      // Convert string to integer
      int value = token.toInt();

      // Store if we haven't exceeded our servo count
      if (parseIndex < NUM_SERVOS) {
        angles[parseIndex] = value;
        parseIndex++;
      }

      startPos = i + 1;  // Move past the comma
    }
  }

  // Did we get exactly 5 values?
  if (parseIndex != NUM_SERVOS) {
    Serial.println("ERROR: Expected 5 values");
    return;
  }

  // Apply each angle with per-finger safety limits and step limiting
  for (int i = 0; i < NUM_SERVOS; i++) {
    // Constrain the angle to this finger's safe limits
    int targetAngle = constrain(angles[i], MIN_ANGLES[i], MAX_ANGLES[i]);

    // Step limiting: don't jump too far in one update
    int diff = targetAngle - currentAngles[i];
    if (diff > MAX_STEP) {
      targetAngle = currentAngles[i] + MAX_STEP;
    } else if (diff < -MAX_STEP) {
      targetAngle = currentAngles[i] - MAX_STEP;
    }

    // Only move the servo if the angle actually changed
    if (targetAngle != currentAngles[i]) {
      currentAngles[i] = targetAngle;
      servos[i].write(targetAngle);
    }
  }

  // Send confirmation back to Python (useful for debugging)
  Serial.print("OK:");
  for (int i = 0; i < NUM_SERVOS; i++) {
    Serial.print(currentAngles[i]);
    if (i < NUM_SERVOS - 1) Serial.print(",");
  }
  Serial.println();
}
