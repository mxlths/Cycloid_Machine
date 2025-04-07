/**
 * SerialInterface.cpp
 * 
 * Implements serial communication for the Cycloid Machine
 */

#include <Arduino.h>
#include "SerialInterface.h"
#include "MotorControl.h"
#include "MenuSystem.h"
#include "Config.h"

// Buffer for incoming serial commands
char serialBuffer[MAX_BUFFER_SIZE];
int bufferIndex = 0;

// Initialize serial communication
void setupSerialCommands() {
  Serial.begin(SERIAL_BAUD);
  Serial.println(F("Cycloid Machine Controller"));
  Serial.println(F("Type 'help' for available commands"));
}

// Process any available serial commands
void processSerialCommands() {
  if (Serial.available() > 0) {
    char incomingChar = Serial.read();
    
    if (incomingChar == '\b' || incomingChar == 127) { // Handle backspace
      if (bufferIndex > 0) {
        bufferIndex--;
        Serial.print(F("\b \b"));
      }
      return;
    }
    
    Serial.print(incomingChar); // Echo
    
    if (incomingChar != '\n' && incomingChar != '\r') { // Add to buffer
      if (bufferIndex < MAX_BUFFER_SIZE - 1) {
        serialBuffer[bufferIndex++] = incomingChar;
      }
    } else { // Process command on line ending
      serialBuffer[bufferIndex] = '\0';
      Serial.println(); 
      executeCommand(serialBuffer);
      bufferIndex = 0; // Reset buffer
    }
  }
}

// Execute serial command
void executeCommand(char* command) {
  // Convert to lowercase for case-insensitive comparison
  char* p = command;
  while (*p) { *p = tolower(*p); p++; }
  
  // Help command
  if (strcmp(command, "help") == 0) {
    printHelp(); return;
  }
  // Status command
  if (strcmp(command, "status") == 0) {
    printSystemStatus(); return;
  }
  // Pause command
  if (strcmp(command, "pause") == 0) {
    setSystemPaused(true); return; // Feedback is in setSystemPaused
  }
  // Resume command
  if (strcmp(command, "resume") == 0) {
    setSystemPaused(false); return; // Feedback is in setSystemPaused
  }
  // Reset command
  if (strcmp(command, "reset") == 0) {
    MotorControl::resetToDefaults(); // Call MotorControl public reset
    // Menu state is reset internally if needed via MotorControl calls
    Serial.println(F("All motor settings reset to defaults via Serial"));
    return;
  }
  // Enable motors command
  if (strcmp(command, "enable") == 0) {
    enableAllMotors(); return;
  }
  // Disable motors command
  if (strcmp(command, "disable") == 0) {
    disableAllMotors(); return;
  }
  // Master time command: master=<value>
  if (strncmp(command, "master=", 7) == 0) {
    float time = atof(command + 7);
    setMasterTime(time); // Setter handles validation
    Serial.print(F("Master time set to: ")); Serial.println(getMasterTime());
    return;
  }
  // Wheel speed command format: wheel<n>=<value> (n=1-4)
  if (strncmp(command, "wheel", 5) == 0 && command[5] >= '1' && command[5] <= '0' + MOTORS_COUNT && command[6] == '=') {
    int motorIndex = command[5] - '1'; 
    float speed = atof(command + 7);
    setWheelSpeed(motorIndex, speed); // Setter handles validation
    Serial.print(F("Wheel ")); Serial.print(motorIndex + 1);
    Serial.print(F(" speed set to: ")); Serial.println(getWheelSpeed(motorIndex));
    return;
  }
  // LFO depth command format: depth<n>=<value> (n=1-4)
  if (strncmp(command, "depth", 5) == 0 && command[5] >= '1' && command[5] <= '0' + MOTORS_COUNT && command[6] == '=') {
    int motorIndex = command[5] - '1';
    float depth = atof(command + 7);
    setLfoDepth(motorIndex, depth); // Setter handles validation
    Serial.print(F("Wheel ")); Serial.print(motorIndex + 1);
    Serial.print(F(" LFO depth set to: ")); Serial.println(getLfoDepth(motorIndex));
    return;
  }
  // LFO rate command format: rate<n>=<value> (n=1-4)
  if (strncmp(command, "rate", 4) == 0 && command[4] >= '1' && command[4] <= '0' + MOTORS_COUNT && command[5] == '=') {
    int motorIndex = command[4] - '1';
    float rate = atof(command + 6);
    setLfoRate(motorIndex, rate); // Setter handles validation
    Serial.print(F("Wheel ")); Serial.print(motorIndex + 1);
    Serial.print(F(" LFO rate set to: ")); Serial.println(getLfoRate(motorIndex));
    return;
  }
  // LFO polarity command format: polarity<n>=<0/1> (n=1-4)
  if (strncmp(command, "polarity", 8) == 0 && command[8] >= '1' && command[8] <= '0' + MOTORS_COUNT && command[9] == '=') {
    int motorIndex = command[8] - '1';
    int polarity = atoi(command + 10);
    setLfoPolarity(motorIndex, (polarity == 1)); // Setter handles validation
    Serial.print(F("Wheel ")); Serial.print(motorIndex + 1);
    Serial.print(F(" LFO polarity set to: ")); Serial.println(getLfoPolarity(motorIndex) ? F("Bipolar") : F("Unipolar"));
    return;
  }
  // Microstep command format: microstep=<value>
  if (strncmp(command, "microstep=", 10) == 0) {
    int microstep = atoi(command + 10);
    if (updateMicrostepMode(microstep)) { // Function handles validation & feedback
      Serial.print(F("Microstep mode set to: ")); Serial.println(getCurrentMicrostepMode());
    } else {
      Serial.println(F("Error: Invalid microstep value. Use 1, 2, 4, 8, 16, 32, 64, or 128"));
    }
    return;
  }
  // Apply preset command format: preset=<value> (n=1-NUM_RATIO_PRESETS)
  if (strncmp(command, "preset=", 7) == 0) {
    int presetIndex = atoi(command + 7) - 1; // Convert to 0-based index
    if (presetIndex >= 0 && presetIndex < NUM_RATIO_PRESETS) {
      // Apply preset by calling individual setters
      Serial.print(F("Applying ratio preset: ")); Serial.println(presetIndex + 1);
      for (byte i = 0; i < MOTORS_COUNT; i++) {
          setWheelSpeed(i, RATIO_PRESETS[presetIndex][i]);
      }
    } else {
      Serial.println(F("Error: Invalid preset number (1-") + String(NUM_RATIO_PRESETS) + F(")"));
    }
    return;
  }
  
  // Unknown command
  Serial.print(F("Unknown command: ")); Serial.println(command);
  Serial.println(F("Type 'help' for available commands"));
}

// Print help information
void printHelp() {
  Serial.println(F("\n--- Cycloid Machine Commands ---"));
  Serial.println(F("status                   - Display system status"));
  Serial.println(F("help                     - Show this help message"));
  Serial.println(F("pause                    - Pause the system"));
  Serial.println(F("resume                   - Resume the system"));
  Serial.println(F("reset                    - Reset all motor settings to defaults"));
  Serial.println(F("enable                   - Enable motor drivers"));
  Serial.println(F("disable                  - Disable motor drivers"));
  Serial.println(F("master=<value>           - Set master time in milliseconds (e.g., 1000)"));
  Serial.println(F("wheel<n>=<value>         - Set wheel speed ratio (n=1-4, e.g., wheel1=1.5)"));
  Serial.println(F("depth<n>=<value>         - Set LFO depth 0-100% (n=1-4, e.g., depth2=50)"));
  Serial.println(F("rate<n>=<value>          - Set LFO rate 0-10Hz (n=1-4, e.g., rate3=2.5)"));
  Serial.println(F("polarity<n>=<0/1>        - Set LFO polarity: 0=uni, 1=bi (n=1-4, e.g., polarity4=1)"));
  Serial.println(F("microstep=<value>        - Set microstepping (1,2,4,8,16,32,64,128)"));
  Serial.println(F("preset=<value>           - Apply ratio preset (1-") + String(NUM_RATIO_PRESETS) + F(")"));
}

// Print system status
void printSystemStatus() {
  Serial.println(F("\n--- System Status ---"));
  Serial.print(F("System state: ")); Serial.println(getSystemPaused() ? F("PAUSED") : F("RUNNING"));
  Serial.print(F("Master time: ")); Serial.println(getMasterTime());
  Serial.print(F("Microstepping: ")); Serial.println(getCurrentMicrostepMode());
  
  Serial.println(F("\n--- Wheel Settings ---"));
  Serial.println(F("Wheel | Ratio | LFO Dep | LFO Rate | LFO Pol | Actual Speed (Steps/s)"));
  Serial.println(F("------|-------|---------|----------|---------|------------------------"));
  
  char buffer[100];
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    sprintf(buffer, " %-4d | %-5.2f | %-7.1f | %-8.2f | %-7s | %.2f",
            i + 1,
            getWheelSpeed(i),
            getLfoDepth(i),
            getLfoRate(i),
            getLfoPolarity(i) ? "Bipolar" : "Unipolar",
            getCurrentActualSpeed(i)); // Get speed in steps/sec
    Serial.println(buffer);
  }
} 