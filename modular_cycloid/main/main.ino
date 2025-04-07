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

// Global Definitions (Hardware Objects)
// These were previously extern in Config.h, need definition here or in a dedicated globals.cpp
LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS); 
AccelStepper stepperX(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepperY(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);
AccelStepper stepperZ(AccelStepper::DRIVER, Z_STEP_PIN, Z_DIR_PIN);
AccelStepper stepperA(AccelStepper::DRIVER, A_STEP_PIN, A_DIR_PIN);
AccelStepper* steppers[MOTORS_COUNT] = {&stepperX, &stepperY, &stepperZ, &stepperA};
const char* wheelLabels[MOTORS_COUNT] = {"X", "Y", "Z", "A"};

// Timing for serial check (can remain global or move)
unsigned long serialCheckInterval = 250; // Check serial every 250ms
unsigned long lastSerialCheck = 0;

void setup() {
  setupSerial();
  setupMotors();
  setupEncoder();
  setupLCD(); // Added LCD setup call
  initializeMenu();
  
  // REMOVE global reset call - Modules initialize their own defaults
  // resetToDefaults(); 
  
  delay(100); // Short delay for stability
  Serial.println(F("System Initialized."));
}

void loop() {
  unsigned long currentMillis = millis();
  
  // --- Input and Command Processing ---
  checkButtonPress(); // Handles button, potentially changes MenuSystem's pause state
  
  // Process serial commands periodically
  if (currentMillis - lastSerialCheck >= serialCheckInterval) {
    processSerialCommands(); // Reads serial, potentially calls MenuSystem::setSystemPaused
    lastSerialCheck = currentMillis;
  }

  // --- Motor Update ---
  // Get the current pause state from MenuSystem
  bool isPaused = getSystemPaused(); 
  updateMotors(currentMillis, isPaused); 
  
  // --- Display Update ---
  // MenuSystem's updateDisplay already checks its internal pause state
  updateDisplay(); 
  
  // Small delay
  delay(1); 
} 