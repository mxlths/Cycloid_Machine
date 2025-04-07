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

// Debug flags - uncomment to enable debug output
// #define DEBUG_TIMING
// #define DEBUG_INPUT
// #define DEBUG_MOTORS

// Global Definitions (Hardware Objects)
// These were previously extern in Config.h, need definition here or in a dedicated globals.cpp
LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS); 
AccelStepper stepperX(AccelStepper::DRIVER, X_STEP_PIN, X_DIR_PIN);
AccelStepper stepperY(AccelStepper::DRIVER, Y_STEP_PIN, Y_DIR_PIN);
AccelStepper stepperZ(AccelStepper::DRIVER, Z_STEP_PIN, Z_DIR_PIN);
AccelStepper stepperA(AccelStepper::DRIVER, A_STEP_PIN, A_DIR_PIN);
AccelStepper* steppers[MOTORS_COUNT] = {&stepperX, &stepperY, &stepperZ, &stepperA};
const char* wheelLabels[MOTORS_COUNT] = {"X", "Y", "Z", "A"};

// Timing variables
unsigned long currentMillis = 0;
unsigned long lastSerialStatusTime = 0;

// Setup function - called once at startup
void setup() {
  // Initialize serial communication
  Serial.begin(SERIAL_BAUD);
  Serial.println(F("\nCycloid Machine Controller v1.1"));
  Serial.println(F("Initializing..."));
  
  // Initialize systems in order
  setupMotors();
  setupLCD();
  setupEncoders();
  setupSerialCommands();
  
  // Show initial display
  updateDisplay();
  
  Serial.println(F("Initialization complete"));
  Serial.println(F("Type 'help' for available commands"));
}

// Loop function - called repeatedly after setup
void loop() {
  // Get current time
  currentMillis = millis();
  
  // Process serial commands
  processSerialCommands();
  
  // Get system paused state from MenuSystem
  bool paused = getSystemPaused();
  
  // Update motor speeds if not paused
  updateMotors(currentMillis, paused);
  
  // Check and handle encoder/button inputs
  checkEncoders();
  
  // Print status at regular intervals
  if (currentMillis - lastSerialStatusTime >= 2000) {
    #ifdef DEBUG_TIMING
    Serial.print(F("Loop time (ms): "));
    Serial.println(millis() - currentMillis);
    #endif
    
    #ifdef DEBUG_MOTORS
    printSystemStatus();
    #endif
    
    lastSerialStatusTime = currentMillis;
  }
}

// Function to update motor speed display and actual motor speeds
void updateMotorSpeeds() {
  // Update LCD with current speeds
  updateDisplay();
  
  #ifdef DEBUG_MOTORS
  Serial.println(F("Motor speeds updated"));
  // Print individual motor speeds
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    Serial.print(F("Motor "));
    Serial.print(i + 1);
    Serial.print(F(": "));
    Serial.print(getWheelSpeed(i));
    Serial.print(F(" ratio, actual RPM: "));
    Serial.println(getCurrentActualSpeed(i));
  }
  #endif
} 