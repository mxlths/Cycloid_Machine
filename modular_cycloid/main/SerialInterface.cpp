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

// Need access to wheel labels (still extern in Config.h)
// REMOVE duplicate include
// #include "Config.h" 

// For access to ratio presets - consider defining them centrally or passing needed data
// For simplicity, let's copy the definition here as static const
// Or ideally, MotorControl could provide a function to apply preset by index?
// Let's keep it simple and have SerialInterface call setters directly.
static const byte NUM_RATIO_PRESETS_SERIAL = 4; // Match MenuSystem
static const float ratioPresetsSerial[NUM_RATIO_PRESETS_SERIAL][MOTORS_COUNT] = {
  {1.0, 1.0, 1.0, 1.0},    // Preset 1: 1:1:1:1
  {1.0, 2.0, 3.0, 4.0},    // Preset 2: 1:2:3:4
  {1.0, -1.0, 1.0, -1.0},  // Preset 3: 1:-1:1:-1 (Alternating)
  {1.0, 1.5, 2.25, 3.375}  // Preset 4: Geometric progression (approx)
};

// --- Internal Helper Functions --- 
static void applyRatioPresetSerial(byte presetIndex);
static void resetToDefaultsSerial();

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
    
    // Handle backspace
    if (incomingChar == '\b' || incomingChar == 127) {
      if (bufferIndex > 0) {
        bufferIndex--;
        Serial.print(F("\b \b")); // Erase character on terminal
      }
      return;
    }
    
    // Echo character
    Serial.print(incomingChar);
    
    // Add to buffer if not a line ending
    if (incomingChar != '\n' && incomingChar != '\r') {
      if (bufferIndex < MAX_BUFFER_SIZE - 1) {
        serialBuffer[bufferIndex++] = incomingChar;
      }
    } else {
      // Process command when line ending is received
      serialBuffer[bufferIndex] = '\0'; // Null-terminate
      
      Serial.println(); // New line after command
      executeCommand(serialBuffer);
      
      // Reset buffer
      bufferIndex = 0;
    }
  }
}

// Execute serial command
void executeCommand(char* command) {
  // Convert to lowercase for case-insensitive comparison
  for (int i = 0; command[i]; i++) {
    command[i] = tolower(command[i]);
  }
  
  // Help command
  if (strcmp(command, "help") == 0) {
    printHelp();
    return;
  }
  
  // Status command
  if (strcmp(command, "status") == 0) {
    printSystemStatus();
    return;
  }
  
  // Pause command
  if (strcmp(command, "pause") == 0) {
    setSystemPaused(true);
    Serial.println(F("System paused"));
    return;
  }
  
  // Resume command
  if (strcmp(command, "resume") == 0) {
    setSystemPaused(false);
    Serial.println(F("System resumed"));
    return;
  }
  
  // Reset command
  if (strcmp(command, "reset") == 0) {
    resetToDefaults();
    Serial.println(F("All settings reset to defaults"));
    return;
  }
  
  // Enable motors command
  if (strcmp(command, "enable") == 0) {
    enableAllMotors();
    Serial.println(F("Motors enabled"));
    return;
  }
  
  // Disable motors command
  if (strcmp(command, "disable") == 0) {
    disableAllMotors();
    Serial.println(F("Motors disabled"));
    return;
  }
  
  // Master time command
  if (strncmp(command, "master=", 7) == 0) {
    float time = atof(command + 7);
    if (time > 0) {
      setMasterTime(time);
      Serial.print(F("Master time set to: "));
      Serial.println(time);
    } else {
      Serial.println(F("Error: Invalid master time value"));
    }
    return;
  }
  
  // Wheel speed command format: "wheel1=value"
  if (strncmp(command, "wheel", 5) == 0 && command[5] >= '1' && command[5] <= '4' && command[6] == '=') {
    int motorIndex = command[5] - '1'; // Convert to 0-based index
    float speed = atof(command + 7);
    
    if (speed != 0.0 || command[7] == '0') { // Valid numeric input
      setWheelSpeed(motorIndex, speed);
      Serial.print(F("Wheel "));
      Serial.print(motorIndex + 1);
      Serial.print(F(" speed set to: "));
      Serial.println(speed);
    } else {
      Serial.println(F("Error: Invalid wheel speed value"));
    }
    return;
  }
  
  // LFO depth command format: "depth1=value"
  if (strncmp(command, "depth", 5) == 0 && command[5] >= '1' && command[5] <= '4' && command[6] == '=') {
    int motorIndex = command[5] - '1'; // Convert to 0-based index
    float depth = atof(command + 7);
    
    if (depth >= 0 && depth <= LFO_DEPTH_MAX) {
      setLfoDepth(motorIndex, depth);
      Serial.print(F("LFO depth for wheel "));
      Serial.print(motorIndex + 1);
      Serial.print(F(" set to: "));
      Serial.println(depth);
    } else {
      Serial.println(F("Error: Invalid LFO depth value (0-100)"));
    }
    return;
  }
  
  // LFO rate command format: "rate1=value"
  if (strncmp(command, "rate", 4) == 0 && command[4] >= '1' && command[4] <= '4' && command[5] == '=') {
    int motorIndex = command[4] - '1'; // Convert to 0-based index
    float rate = atof(command + 6);
    
    if (rate >= 0 && rate <= LFO_RATE_MAX) {
      setLfoRate(motorIndex, rate);
      Serial.print(F("LFO rate for wheel "));
      Serial.print(motorIndex + 1);
      Serial.print(F(" set to: "));
      Serial.println(rate);
    } else {
      Serial.println(F("Error: Invalid LFO rate value (0-10)"));
    }
    return;
  }
  
  // LFO polarity command format: "polarity1=1" (1 for bipolar, 0 for unipolar)
  if (strncmp(command, "polarity", 8) == 0 && command[8] >= '1' && command[8] <= '4' && command[9] == '=') {
    int motorIndex = command[8] - '1'; // Convert to 0-based index
    int polarity = atoi(command + 10);
    
    bool isBipolar = (polarity == 1);
    setLfoPolarity(motorIndex, isBipolar);
    Serial.print(F("LFO polarity for wheel "));
    Serial.print(motorIndex + 1);
    Serial.print(F(" set to: "));
    Serial.println(isBipolar ? F("Bipolar") : F("Unipolar"));
    return;
  }
  
  // Microstep command format: "microstep=value"
  if (strncmp(command, "microstep=", 10) == 0) {
    int microstep = atoi(command + 10);
    
    if (updateMicrostepMode(microstep)) {
      Serial.print(F("Microstep mode set to: "));
      Serial.println(microstep);
    } else {
      Serial.println(F("Error: Invalid microstep value. Use 1, 2, 4, 8, 16, 32, 64, or 128"));
    }
    return;
  }
  
  // Apply preset command format: "preset=value"
  if (strncmp(command, "preset=", 7) == 0) {
    int preset = atoi(command + 7);
    
    if (preset >= 1 && preset <= NUM_RATIO_PRESETS) {
      applyRatioPreset(preset - 1); // Convert to 0-based index
      Serial.print(F("Applied ratio preset: "));
      Serial.println(preset);
    } else {
      Serial.println(F("Error: Invalid preset number"));
    }
    return;
  }
  
  // If we get here, the command was not recognized
  Serial.print(F("Unknown command: "));
  Serial.println(command);
  Serial.println(F("Type 'help' for available commands"));
}

// Print help information
void printHelp() {
  Serial.println(F("\n--- Cycloid Machine Commands ---"));
  Serial.println(F("status                   - Display system status"));
  Serial.println(F("help                     - Show this help message"));
  Serial.println(F("pause                    - Pause the system"));
  Serial.println(F("resume                   - Resume the system"));
  Serial.println(F("reset                    - Reset all settings to defaults"));
  Serial.println(F("enable                   - Enable motor drivers"));
  Serial.println(F("disable                  - Disable motor drivers"));
  Serial.println(F("master=<value>           - Set master time in milliseconds"));
  Serial.println(F("wheel<n>=<value>         - Set wheel speed ratio (n=1-4)"));
  Serial.println(F("depth<n>=<value>         - Set LFO depth 0-100% (n=1-4)"));
  Serial.println(F("rate<n>=<value>          - Set LFO rate 0-10Hz (n=1-4)"));
  Serial.println(F("polarity<n>=<0/1>        - Set LFO polarity: 0=uni, 1=bi (n=1-4)"));
  Serial.println(F("microstep=<value>        - Set microstepping (1,2,4,8,16,32,64,128)"));
  Serial.println(F("preset=<value>           - Apply ratio preset (1-4)"));
}

// Print system status
void printSystemStatus() {
  Serial.println(F("\n--- System Status ---"));
  
  // System state
  Serial.print(F("System state: "));
  Serial.println(getSystemPaused() ? F("PAUSED") : F("RUNNING"));
  
  // Master time
  Serial.print(F("Master time: "));
  Serial.println(getMasterTime());
  
  // Microstepping mode
  Serial.print(F("Microstepping: "));
  Serial.println(getCurrentMicrostepMode());
  
  // Print wheel information
  Serial.println(F("\n--- Wheel Settings ---"));
  Serial.println(F("Wheel\tSpeed\tActual\tLFO Depth\tLFO Rate\tLFO Polarity"));
  
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    Serial.print(i + 1);
    Serial.print(F("\t"));
    
    // Wheel speed ratio
    Serial.print(getWheelSpeed(i));
    Serial.print(F("\t"));
    
    // Actual speed in RPM
    Serial.print(getCurrentActualSpeed(i));
    Serial.print(F("\t"));
    
    // LFO depth
    Serial.print(getLfoDepth(i));
    Serial.print(F("%\t\t"));
    
    // LFO rate
    Serial.print(getLfoRate(i));
    Serial.print(F("Hz\t\t"));
    
    // LFO polarity
    Serial.println(getLfoPolarity(i) ? F("Bipolar") : F("Unipolar"));
  }
}

// --- Internal Helper Function Implementations ---

// Apply a ratio preset using MotorControl setters
static void applyRatioPresetSerial(byte presetIndex) {
  if (presetIndex < NUM_RATIO_PRESETS_SERIAL) {
    Serial.print(F("Applying ratio preset "));
    Serial.println(presetIndex + 1);
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      setWheelSpeed(i, ratioPresetsSerial[presetIndex][i]);
    }
  } else {
      Serial.println(F("Invalid preset index in applyRatioPresetSerial"));
  }
}

// Reset all values to defaults using MotorControl setters
static void resetToDefaultsSerial() {
  Serial.println(F("Resetting all settings to defaults via Serial..."));
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    setWheelSpeed(i, 10.0); // Default speed
    setLfoDepth(i, 0.0);
    setLfoRate(i, 0.0);
    setLfoPolarity(i, false); // UNI
  }
  setMasterTime(1.00); // Default master time
  
  // Also reset microstepping via Serial command
  if (updateMicrostepMode(MICROSTEP_FULL)) { 
     Serial.println(F("Microstepping reset to 1x"));
  } else {
     Serial.println(F("Microstepping reset failed!"));
  }
} 