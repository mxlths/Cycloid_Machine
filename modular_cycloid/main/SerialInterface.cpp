/**
 * SerialInterface.cpp
 * 
 * Implements serial communication for the Cycloid Machine
 */

#include "SerialInterface.h"
#include "MotorControl.h"
#include "Config.h"
#include "MenuSystem.h" // Include for setSystemPaused/getSystemPaused

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

// Initialize serial communication
void setupSerial() {
  Serial.begin(SERIAL_BAUD_RATE);
  Serial.println(F("Cycloid Machine - Motor Control System"));
  Serial.println(F("Type 'HELP' for available commands"));
}

// Process commands received via serial
void processSerialCommands() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.length() == 0) return;
    
    command.toUpperCase();
    
    if (command == "HELP") {
      printHelp();
    } else if (command == "STATUS") {
      printSystemStatus();
    } else if (command == "PAUSE") {
      // Call MenuSystem setter directly
      setSystemPaused(true); 
      // Serial.println(F("Pause requested")); // Feedback is now in setSystemPaused
    } else if (command == "RESUME") {
      // Call MenuSystem setter directly
      setSystemPaused(false);
      // Serial.println(F("Resume requested")); // Feedback is now in setSystemPaused
    } else if (command == "RESET") {
      // Call internal reset function
      resetToDefaultsSerial(); 
    } else if (command.startsWith("MICROSTEP ")) {
      if (command.length() >= 11) {
        int value = command.substring(10).toInt();
        // Use MotorControl API
        if (updateMicrostepMode(value)) { 
          Serial.print(F("Set microstepping mode to "));
          Serial.print(getCurrentMicrostepMode()); // Use getter
          Serial.println(F("x"));
        } else {
          Serial.println(F("Invalid microstepping mode (use 1, 2, 4, 8, 16, 32, 64, or 128)"));
        }
      } else {
        Serial.println(F("Invalid MICROSTEP command format"));
      }
    } else if (command.startsWith("SPEED ")) {
      if (command.length() >= 8) {
        char wheel = command.charAt(6);
        int wheelIndex = -1;
        for (byte i = 0; i < MOTORS_COUNT; i++) {
          if (wheel == wheelLabels[i][0]) { wheelIndex = i; break; }
        }
        if (wheelIndex >= 0) {
          float value = command.substring(8).toFloat();
          // Use MotorControl API setter (handles constraints)
          setWheelSpeed(wheelIndex, value); 
          Serial.print(F("Set "));
          Serial.print(wheelLabels[wheelIndex]);
          Serial.print(F(" speed to "));
          Serial.println(getWheelSpeed(wheelIndex)); // Use getter to confirm
        } else {
          Serial.println(F("Invalid wheel identifier"));
        }
      } else {
        Serial.println(F("Invalid SPEED command format"));
      }
    } else if (command.startsWith("LFO ")) {
      if (command.length() >= 10) {
        char wheel = command.charAt(4);
        int wheelIndex = -1;
        for (byte i = 0; i < MOTORS_COUNT; i++) {
          if (wheel == wheelLabels[i][0]) { wheelIndex = i; break; }
        }
        if (wheelIndex >= 0) {
          int depthIdx = command.indexOf("DEPTH ");
          int rateIdx = command.indexOf("RATE ");
          int polIdx = command.indexOf("POL ");

          if (depthIdx > 0) {
            float value = command.substring(depthIdx + 6).toFloat();
            // Use MotorControl API setter
            setLfoDepth(wheelIndex, value); 
            Serial.print(F("Set ")); Serial.print(wheelLabels[wheelIndex]);
            Serial.print(F(" LFO depth to ")); Serial.println(getLfoDepth(wheelIndex)); // Use getter
          } else if (rateIdx > 0) {
            float value = command.substring(rateIdx + 5).toFloat();
            // Use MotorControl API setter
            setLfoRate(wheelIndex, value);
            Serial.print(F("Set ")); Serial.print(wheelLabels[wheelIndex]);
            Serial.print(F(" LFO rate to ")); Serial.println(getLfoRate(wheelIndex)); // Use getter
          } else if (polIdx > 0) {
            String polStr = command.substring(polIdx + 4);
            polStr.trim(); // Trim whitespace
            bool newPolarity = getLfoPolarity(wheelIndex); // Default to current
            if (polStr == "UNI") {
              newPolarity = false;
            } else if (polStr == "BI") {
              newPolarity = true;
            } else {
               Serial.println(F("Invalid polarity value (use UNI or BI)"));
               continue; // Skip update if value is invalid
            }
            // Use MotorControl API setter
            setLfoPolarity(wheelIndex, newPolarity);
            Serial.print(F("Set ")); Serial.print(wheelLabels[wheelIndex]);
            Serial.print(F(" LFO polarity to ")); Serial.println(getLfoPolarity(wheelIndex) ? "BI" : "UNI"); // Use getter
          } else {
            Serial.println(F("Invalid LFO parameter (DEPTH, RATE, or POL)"));
          }
        } else {
          Serial.println(F("Invalid wheel identifier"));
        }
      } else {
        Serial.println(F("Invalid LFO command format"));
      }
    } else if (command.startsWith("MASTER ")) {
      if (command.length() >= 8) {
        float value = command.substring(7).toFloat();
        // Use MotorControl API setter
        setMasterTime(value); 
        Serial.print(F("Set master time to "));
        Serial.println(getMasterTime()); // Use getter
      } else {
        Serial.println(F("Invalid MASTER command format"));
      }
    } else if (command.startsWith("RATIO ")) {
      if (command.length() >= 7) {
        int value = command.substring(6).toInt();
        if (value >= 1 && value <= NUM_RATIO_PRESETS_SERIAL) {
          // Call internal ratio function
          applyRatioPresetSerial(value - 1); 
        } else {
          Serial.print(F("Invalid ratio preset (use 1-"));
          Serial.print(NUM_RATIO_PRESETS_SERIAL);
          Serial.println(")");
        }
      } else {
        Serial.println(F("Invalid RATIO command format"));
      }
    } else {
      Serial.println(F("Unknown command. Type 'HELP' for available commands."));
    }
  } // end Serial.available()
}

// Print system status using MotorControl getters and MenuSystem pause getter
void printSystemStatus() {
  Serial.println(F("\nCycloid Machine Status:"));
  // Use MenuSystem getter for pause state
  Serial.print(F("System: ")); 
  Serial.println(getSystemPaused() ? F("PAUSED") : F("RUNNING")); 
  
  Serial.print(F("Master Time: "));
  Serial.println(getMasterTime());
  
  Serial.print(F("Microstepping: "));
  Serial.print(getCurrentMicrostepMode());
  Serial.println(F("x"));
  
  Serial.println(F("\nWheel Speeds (Base):"));
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    Serial.print(wheelLabels[i]);
    Serial.print(F(": "));
    Serial.print(getWheelSpeed(i)); // Base speed setting
    Serial.print(F(" (Actual: "));
    Serial.print(getCurrentActualSpeed(i)); // Current calculated steps/sec
    Serial.println(F(" steps/sec)"));
  }
  
  Serial.println(F("\nLFO Settings:"));
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    Serial.print(wheelLabels[i]);
    Serial.print(F(": Depth="));
    Serial.print(getLfoDepth(i));
    Serial.print(F(", Rate="));
    Serial.print(getLfoRate(i));
    Serial.print(F(", Polarity="));
    Serial.println(getLfoPolarity(i) ? F("BI") : F("UNI"));
  }
  
  // Simplify active ratio display - just show current speeds
  // Serial.println(F("\nActive Speeds (Current Base Settings): "));
  // Serial.print(F("X:")); Serial.print(getWheelSpeed(0));
  // Serial.print(F(", Y:")); Serial.print(getWheelSpeed(1));
  // Serial.print(F(", Z:")); Serial.print(getWheelSpeed(2));
  // Serial.print(F(", A:")); Serial.println(getWheelSpeed(3));
}

// Print help information
void printHelp() {
  Serial.println(F("Available commands:"));
  Serial.println(F("HELP          - Show this help"));
  Serial.println(F("STATUS        - Show current system status"));
  Serial.println(F("PAUSE         - Request system pause"));
  Serial.println(F("RESUME        - Request system resume"));
  Serial.println(F("RESET         - Reset all settings to default values"));
  Serial.println(F("MICROSTEP val - Set microstepping (1, 2, 4, 8, 16, 32, 64, 128)"));
  Serial.println(F("SPEED X val   - Set X wheel speed base (0.1-256.0)"));
  Serial.println(F("SPEED Y val   - Set Y wheel speed base"));
  Serial.println(F("SPEED Z val   - Set Z wheel speed base"));
  Serial.println(F("SPEED A val   - Set A wheel speed base"));
  Serial.println(F("LFO X D val   - Set X LFO depth % (0.0-100.0)"));
  Serial.println(F("LFO X R val   - Set X LFO rate (0.0-256.0)"));
  Serial.println(F("LFO X P U/B   - Set X LFO polarity (UNI or BI)"));
  Serial.println(F("... (LFO Y/Z/A similar) ..."));
  Serial.println(F("MASTER val    - Set master time (0.01-999.99)"));
  Serial.print(F("RATIO n       - Apply ratio preset (1-"));
  Serial.print(NUM_RATIO_PRESETS_SERIAL);
  Serial.println(")");
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