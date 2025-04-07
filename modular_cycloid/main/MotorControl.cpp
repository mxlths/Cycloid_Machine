/**
 * MotorControl.cpp
 * 
 * Implements stepper motor control and LFO functions for the Cycloid Machine
 */

#include "MotorControl.h"
#include <math.h>

// Define variables for motor control
unsigned long lastMotorUpdateTime = 0;
byte currentMicrostepMode = MICROSTEP_FULL;  // Default to full step mode

// Initialize the stepper motors
void setupMotors() {
  // Configure stepper motor drivers
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    // Higher max speed is needed with microstepping
    float maxSpeed = 10000.0 * currentMicrostepMode;
    steppers[i]->setMaxSpeed(maxSpeed);
    steppers[i]->setAcceleration(500 * currentMicrostepMode);
  }
  
  // Enable motor drivers
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW);  // LOW = enabled
}

// Update microstepping mode
bool updateMicrostepMode(byte newMode) {
  // Check if the mode is valid (must be a power of 2 up to 128)
  if (newMode != 1 && newMode != 2 && newMode != 4 && newMode != 8 && 
      newMode != 16 && newMode != 32 && newMode != 64 && newMode != 128) {
    Serial.println(F("Invalid microstepping mode"));
    return false;
  }
  
  // Store the new microstepping mode
  currentMicrostepMode = newMode;
  
  // Reconfigure motor parameters for new step resolution
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    float maxSpeed = 10000.0 * currentMicrostepMode;
    steppers[i]->setMaxSpeed(maxSpeed);
    steppers[i]->setAcceleration(500 * currentMicrostepMode);
  }
  
  Serial.print(F("Microstepping mode set to "));
  Serial.print(currentMicrostepMode);
  Serial.println(F("x"));
  
  return true;
}

// Stop all motors
void stopAllMotors() {
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    steppers[i]->setSpeed(0);
  }
}

// Update motors - main control function called from loop
void updateMotors(unsigned long currentMillis) {
  // Skip if paused
  if (systemPaused) return;
  
  // Update speeds periodically
  if (currentMillis - lastMotorUpdateTime >= MOTOR_UPDATE_INTERVAL) {
    updateMotorSpeeds();
    lastMotorUpdateTime = currentMillis;
  }
  
  // Run each motor
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    steppers[i]->runSpeed();
  }
}

// Calculate steps per revolution with microstepping
unsigned long getStepsPerWheelRev() {
  return STEPS_PER_MOTOR_REV * GEAR_RATIO * currentMicrostepMode;
}

// Update motor speeds based on current settings
void updateMotorSpeeds() {
  // Skip updating if paused
  if (systemPaused) return;
  
  // Update all motor speeds
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    // Start with base speed
    float baseSpeed = wheelSpeeds[i];
    
    // Apply LFO modulation if enabled
    if (lfoRates[i] > 0.0 && lfoDepths[i] > 0.0) {
      float lfoMod = calculateLfoModulation(i);
      
      // Apply modulation to base speed
      if (lfoPolarities[i]) {  // Bipolar modulation
        baseSpeed += lfoMod;
      } else {  // Unipolar modulation (never reverse direction)
        baseSpeed = max(0.1, baseSpeed + lfoMod);
      }
    }
    
    // Convert speed parameter to actual steps per second, accounting for microstepping
    // Speed 1.0 = 1 rotation in masterTime seconds
    // Speed 10.0 = 1/10 rotation in masterTime seconds
    float stepsPerSecond = getStepsPerWheelRev() / (masterTime * baseSpeed);
    
    // Set motor speed
    currentSpeeds[i] = stepsPerSecond;
    steppers[i]->setSpeed(stepsPerSecond);
    
    // Update LFO phases
    if (lfoRates[i] > 0.0) {
      // Increment phase based on rate and elapsed time
      // Rate 1.0 = 1 full cycle in masterTime seconds
      float cycleRate = 1.0 / (masterTime * lfoRates[i]);
      float phaseIncrement = (float)MOTOR_UPDATE_INTERVAL / 1000.0 * cycleRate * LFO_RESOLUTION;
      lfoPhases[i] = (lfoPhases[i] + (unsigned long)phaseIncrement) % LFO_RESOLUTION;
    }
  }
}

// Calculate LFO modulation for a motor
float calculateLfoModulation(byte motorIndex) {
  // Calculate sine wave based on current phase (0-999)
  float phase = (float)lfoPhases[motorIndex] / LFO_RESOLUTION * 2.0 * PI;
  float sinValue = sin(phase);
  
  // Convert to modulation amount
  float baseSpeed = wheelSpeeds[motorIndex];
  float depth = lfoDepths[motorIndex] / 100.0;  // Convert percentage to decimal
  
  if (lfoPolarities[motorIndex]) {
    // Bipolar: -depth% to +depth%
    return baseSpeed * depth * sinValue;
  } else {
    // Unipolar: 0 to +depth%
    return baseSpeed * depth * (sinValue + 1.0) / 2.0;
  }
}

// Apply a ratio preset to wheel speeds
void applyRatioPreset(byte presetIndex) {
  if (presetIndex < 4) {
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      wheelSpeeds[i] = ratioPresets[presetIndex][i];
    }
    Serial.print(F("Applied ratio preset "));
    Serial.println(presetIndex + 1);
  }
}

// Reset all values to defaults
void resetToDefaults() {
  // Reset wheel speeds
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    wheelSpeeds[i] = 10.0;
    lfoDepths[i] = 0.0;
    lfoRates[i] = 0.0;
    lfoPolarities[i] = false;  // UNI
  }
  
  // Reset master time
  masterTime = 1.00;
  
  Serial.println(F("All settings reset to defaults"));
} 