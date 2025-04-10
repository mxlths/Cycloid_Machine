/**
 * Modular Cycloid Machine Control
 * 
 * Main program for the Arduino-based Cycloid Machine controller
 * Controls 4 stepper motors with individual speed control and LFO modulation
 */

#include <Arduino.h>
#include <Wire.h>
#include <AccelStepper.h>
#include <LiquidCrystal_I2C.h>

#include "Config.h"
#include "MotorControl.h"
#include "MenuSystem.h"
#include "InputHandling.h"
#include "SerialInterface.h"

// Debug flags - uncomment to enable specific debug output
// #define DEBUG_TIMING
// #define DEBUG_INPUT
// #define DEBUG_MOTORS

// --- Global Hardware Objects ---
// LCD Display
LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS);

// Stepper Motors (using definitions from Config.h)
AccelStepper stepperX(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepperY(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);
AccelStepper stepperZ(AccelStepper::DRIVER, Z_STEP_PIN, Z_DIR_PIN);
AccelStepper stepperA(AccelStepper::DRIVER, A_STEP_PIN, A_DIR_PIN);

// Array of stepper pointers (used by MotorControl)
AccelStepper* steppers[MOTORS_COUNT] = {&stepperX, &stepperY, &stepperZ, &stepperA};

// Wheel Labels (used by MenuSystem)
const char* wheelLabels[MOTORS_COUNT] = {"X", "Y", "Z", "A"};

// Timing variables
unsigned long currentMillis = 0;
unsigned long lastSerialStatusTime = 0;
const unsigned long SERIAL_STATUS_INTERVAL = 2000; // ms

// Setup function - called once at startup
void setup() {
  // Initialize serial communication FIRST for debugging output
  Serial.begin(SERIAL_BAUD);
  Serial.println(F("\nCycloid Machine Controller v1.2")); // Updated version
  Serial.println(F("Initializing..."));
  
  // Initialize systems in order
  setupMotors();        // Initialize motor parameters and enable pin
  setupLCD();           // Initialize LCD display
  setupEncoder();       // Initialize rotary encoder pins and state
  setupSerialCommands();// Initialize serial command buffer
  
  // Show initial display after all setup
  updateDisplay();
  
  // Explicitly set system to paused state at the end of setup
  setSystemPaused(true); 

  Serial.println(F("Initialization complete - System is PAUSED"));
  Serial.println(F("Type 'help' for available commands"));
}

// Loop function - called repeatedly after setup
void loop() {
  // Get current time
  currentMillis = millis();
  
  // Process any incoming serial commands
  processSerialCommands();
  
  // Check and handle encoder/button inputs (updates menu state)
  processEncoderChanges();
  checkButtonPress();
  
  // Get current system paused state from MenuSystem
  bool paused = getSystemPaused();
  
  // Update motor positions/speeds based on current settings and pause state
  updateMotors(currentMillis, paused);
  
  // Update the LCD display (reflects changes from input/motors)
  // updateDisplay(); // Called within handleMenuNavigation/Selection/Return now

  // Print status periodically if DEBUG_MOTORS is enabled
  #ifdef DEBUG_MOTORS
  if (currentMillis - lastSerialStatusTime >= SERIAL_STATUS_INTERVAL) {
    printSystemStatus();
    lastSerialStatusTime = currentMillis;
  }
  #endif

  // Optional: Small delay to prevent overwhelming the processor, 
  // but AccelStepper generally benefits from frequent .runSpeed() calls in updateMotors
  // delay(1);
}

// REMOVE unused function
// void updateMotorSpeeds() {
//   // Update LCD with current speeds
//   updateDisplay();
//   
//   #ifdef DEBUG_MOTORS
//   // ... (debug printing removed)
//   #endif
// } 