/**
 * SerialInterface.cpp
 * 
 * Implements serial communication for the Cycloid Machine
 */

#include "SerialInterface.h"
#include "MotorControl.h"

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
    
    // Convert to uppercase for case-insensitive comparison
    command.toUpperCase();
    
    // Handle commands
    if (command == "HELP") {
      printHelp();
    }
    else if (command == "STATUS") {
      printSystemStatus();
    }
    else if (command == "PAUSE") {
      systemPaused = true;
      stopAllMotors();
      Serial.println(F("System paused"));
    }
    else if (command == "RESUME") {
      systemPaused = false;
      Serial.println(F("System resumed"));
    }
    else if (command == "RESET") {
      resetToDefaults();
    }
    else if (command.startsWith("MICROSTEP ")) {
      // Parse "MICROSTEP value" format
      if (command.length() >= 11) {
        int value = command.substring(10).toInt();
        if (updateMicrostepMode(value)) {
          Serial.print(F("Set microstepping mode to "));
          Serial.print(currentMicrostepMode);
          Serial.println(F("x"));
        } else {
          Serial.println(F("Invalid microstepping mode (use 1, 2, 4, 8, 16, 32, 64, or 128)"));
        }
      } else {
        Serial.println(F("Invalid MICROSTEP command format"));
      }
    }
    else if (command.startsWith("SPEED ")) {
      // Parse "SPEED X value" format
      if (command.length() >= 8) {
        char wheel = command.charAt(6);
        int wheelIndex = -1;
        
        // Determine wheel index
        for (byte i = 0; i < MOTORS_COUNT; i++) {
          if (wheel == wheelLabels[i][0]) {
            wheelIndex = i;
            break;
          }
        }
        
        // If valid wheel identified, set its speed
        if (wheelIndex >= 0) {
          float value = command.substring(8).toFloat();
          // Constrain to valid range
          wheelSpeeds[wheelIndex] = constrain(value, 0.1, 256.0);
          Serial.print(F("Set "));
          Serial.print(wheelLabels[wheelIndex]);
          Serial.print(F(" speed to "));
          Serial.println(wheelSpeeds[wheelIndex]);
        } else {
          Serial.println(F("Invalid wheel identifier"));
        }
      } else {
        Serial.println(F("Invalid SPEED command format"));
      }
    }
    else if (command.startsWith("LFO ")) {
      // Parse "LFO X DEPTH/RATE/POL value" format
      if (command.length() >= 10) {
        char wheel = command.charAt(4);
        int wheelIndex = -1;
        
        // Determine wheel index
        for (byte i = 0; i < MOTORS_COUNT; i++) {
          if (wheel == wheelLabels[i][0]) {
            wheelIndex = i;
            break;
          }
        }
        
        // If valid wheel identified, set its LFO parameter
        if (wheelIndex >= 0) {
          if (command.indexOf("DEPTH ") > 0) {
            float value = command.substring(command.indexOf("DEPTH ") + 6).toFloat();
            lfoDepths[wheelIndex] = constrain(value, 0.0, 100.0);
            Serial.print(F("Set "));
            Serial.print(wheelLabels[wheelIndex]);
            Serial.print(F(" LFO depth to "));
            Serial.println(lfoDepths[wheelIndex]);
          }
          else if (command.indexOf("RATE ") > 0) {
            float value = command.substring(command.indexOf("RATE ") + 5).toFloat();
            lfoRates[wheelIndex] = constrain(value, 0.0, 256.0);
            Serial.print(F("Set "));
            Serial.print(wheelLabels[wheelIndex]);
            Serial.print(F(" LFO rate to "));
            Serial.println(lfoRates[wheelIndex]);
          }
          else if (command.indexOf("POL ") > 0) {
            String polStr = command.substring(command.indexOf("POL ") + 4);
            if (polStr.indexOf("UNI") == 0) {
              lfoPolarities[wheelIndex] = false;
              Serial.print(F("Set "));
              Serial.print(wheelLabels[wheelIndex]);
              Serial.println(F(" LFO polarity to UNI"));
            }
            else if (polStr.indexOf("BI") == 0) {
              lfoPolarities[wheelIndex] = true;
              Serial.print(F("Set "));
              Serial.print(wheelLabels[wheelIndex]);
              Serial.println(F(" LFO polarity to BI"));
            }
            else {
              Serial.println(F("Invalid polarity value (use UNI or BI)"));
            }
          }
          else {
            Serial.println(F("Invalid LFO parameter"));
          }
        } else {
          Serial.println(F("Invalid wheel identifier"));
        }
      } else {
        Serial.println(F("Invalid LFO command format"));
      }
    }
    else if (command.startsWith("MASTER ")) {
      // Parse "MASTER value" format
      if (command.length() >= 8) {
        float value = command.substring(7).toFloat();
        masterTime = constrain(value, 0.01, 999.99);
        Serial.print(F("Set master time to "));
        Serial.println(masterTime);
      } else {
        Serial.println(F("Invalid MASTER command format"));
      }
    }
    else if (command.startsWith("RATIO ")) {
      // Parse "RATIO n" format
      if (command.length() >= 7) {
        int value = command.substring(6).toInt();
        if (value >= 1 && value <= 4) {
          applyRatioPreset(value - 1);
        } else {
          Serial.println(F("Invalid ratio preset (use 1-4)"));
        }
      } else {
        Serial.println(F("Invalid RATIO command format"));
      }
    }
    else {
      Serial.println(F("Unknown command. Type 'HELP' for available commands."));
    }
  }
}

// Print system status
void printSystemStatus() {
  Serial.println(F("\nCycloid Machine Status:"));
  Serial.print(F("System: "));
  Serial.println(systemPaused ? F("PAUSED") : F("RUNNING"));
  
  Serial.print(F("Master Time: "));
  Serial.println(masterTime);
  
  Serial.print(F("Microstepping: "));
  Serial.print(currentMicrostepMode);
  Serial.println(F("x"));
  
  Serial.println(F("\nWheel Speeds:"));
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    Serial.print(wheelLabels[i]);
    Serial.print(F(": "));
    Serial.print(wheelSpeeds[i]);
    Serial.print(F(" ("));
    Serial.print(currentSpeeds[i]);
    Serial.println(F(" steps/sec)"));
  }
  
  Serial.println(F("\nLFO Settings:"));
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    Serial.print(wheelLabels[i]);
    Serial.print(F(": Depth="));
    Serial.print(lfoDepths[i]);
    Serial.print(F(", Rate="));
    Serial.print(lfoRates[i]);
    Serial.print(F(", Polarity="));
    Serial.println(lfoPolarities[i] ? F("BI") : F("UNI"));
  }
  
  Serial.println(F("\nActive Ratio Preset: "));
  Serial.print(F("X:"));
  Serial.print(wheelSpeeds[0]);
  Serial.print(F(", Y:"));
  Serial.print(wheelSpeeds[1]);
  Serial.print(F(", Z:"));
  Serial.print(wheelSpeeds[2]);
  Serial.print(F(", A:"));
  Serial.println(wheelSpeeds[3]);
}

// Print help information
void printHelp() {
  Serial.println(F("Available commands:"));
  Serial.println(F("HELP - Show this help"));
  Serial.println(F("STATUS - Show current system status"));
  Serial.println(F("PAUSE - Pause the system"));
  Serial.println(F("RESUME - Resume the system"));
  Serial.println(F("RESET - Reset to default values"));
  Serial.println(F("MICROSTEP value - Set microstepping mode (1, 2, 4, 8, 16, 32, 64, 128)"));
  Serial.println(F("SPEED X value - Set X wheel speed (0.1-256.0)"));
  Serial.println(F("SPEED Y value - Set Y wheel speed"));
  Serial.println(F("SPEED Z value - Set Z wheel speed"));
  Serial.println(F("SPEED A value - Set A wheel speed"));
  Serial.println(F("LFO X DEPTH value - Set X LFO depth (0.0-100.0)"));
  Serial.println(F("LFO X RATE value - Set X LFO rate (0.0-256.0)"));
  Serial.println(F("LFO X POL UNI/BI - Set X LFO polarity"));
  Serial.println(F("MASTER value - Set master time (0.01-999.99)"));
  Serial.println(F("RATIO n - Apply ratio preset (1-4)"));
} 