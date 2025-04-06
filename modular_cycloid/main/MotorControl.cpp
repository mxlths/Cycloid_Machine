/**
 * MotorControl.cpp
 * 
 * Implements stepper motor control and LFO functions for the Cycloid Machine
 */

#include "MotorControl.h"
#include <math.h>

// Initialize the stepper motors
void setupMotors() {
  // Configure stepper motor drivers
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    steppers[i]->setMaxSpeed(10000);  // Set a high maximum (will be limited by setSpeed)
    steppers[i]->setAcceleration(500);
  }
  
  // Enable motor drivers
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW);  // LOW = enabled
}

// Stop all motors
void stopAllMotors() {
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    steppers[i]->setSpeed(0);
  }
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
    
    // Convert speed parameter to actual steps per second
    // Speed 1.0 = 1 rotation in masterTime seconds
    // Speed 10.0 = 1/10 rotation in masterTime seconds
    float stepsPerSecond = STEPS_PER_WHEEL_REV / (masterTime * baseSpeed);
    
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