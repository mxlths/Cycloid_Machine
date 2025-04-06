/**
 * Cycloid Machine - Main Program
 * 
 * An Arduino-based control system for a modular Cycloid Machine
 * that controls four stepper motors with adjustable speed ratios,
 * LFO modulation, and a user interface with encoder navigation.
 */

#include "Config.h"
#include "MenuSystem.h"
#include "MotorControl.h"
#include "InputHandling.h"
#include "SerialInterface.h"

unsigned long lastMillis = 0;
unsigned long serialCheckInterval = 250; // Check serial every 250ms
unsigned long lastSerialCheck = 0;

void setup() {
  // Initialize serial communication
  setupSerial();
  
  // Setup stepper motors
  setupMotors();
  
  // Initialize encoder and button
  setupEncoder();
  
  // Initialize menu system
  initializeMenu();
  
  // Load default settings
  resetToDefaults();
  
  delay(100); // Short delay for stability
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Update motor control
  updateMotors(currentMillis);
  
  // Check for button press
  checkButtonPress();
  
  // Handle encoder position updates
  updateEncoderPosition();
  
  // Process serial commands periodically
  if (currentMillis - lastSerialCheck >= serialCheckInterval) {
    processSerialCommands();
    lastSerialCheck = currentMillis;
  }
  
  // Refresh screen if needed
  updateDisplay();
  
  // Small delay to prevent CPU hogging
  delay(1);
} 