/**
 * MotorControl.cpp
 * 
 * Implements stepper motor control and LFO functions for the Cycloid Machine
 */

#include <Arduino.h>
#include <AccelStepper.h>
#include <math.h>
#include "MotorControl.h"
#include "Config.h"

// NOTE: Stepper instances (stepperX, stepperY, etc.) and the 
// 'steppers' array are defined in main.ino and declared extern in Config.h.
// Do NOT redefine them here.

// --- Motor Settings ---
// Variables to store the state of each motor
struct MotorSetting {
  float wheelSpeed;  // Base wheel speed (ratio) before LFO
  float lfoDepth;    // LFO depth (0-100%)
  float lfoRate;     // LFO rate in Hz
  bool lfoPolarity;  // false = unipolar, true = bipolar
  unsigned int lfoPhase; // Current phase of the LFO (0-LFO_RESOLUTION-1)
};

static MotorSetting motorSettings[MOTORS_COUNT];

// Master time (period) in milliseconds for one rotation at speed 1.0
static float masterTime = DEFAULT_MASTER_TIME;

// Microstepping mode (software value, must match hardware jumpers)
static byte currentMicrostepMode = DEFAULT_MICROSTEP;

// LFO update timing
static unsigned long lastMotorUpdateTime = 0;

// Steps per full wheel revolution (calculated based on microstepping)
static unsigned long stepsPerRev = 200 * DEFAULT_MICROSTEP;

// Forward declaration for internal reset helper
static void resetMotorSettings();

// --- Motor Setup ---
void setupMotors() {
  // Initialize motor settings to defaults
  resetMotorSettings();
  
  // Apply initial settings to AccelStepper objects
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    // Use the externally defined steppers array
    steppers[i]->setMaxSpeed(10000.0 * currentMicrostepMode); // Max speed depends on microsteps
    steppers[i]->setAcceleration(2000.0 * currentMicrostepMode); // Acceleration also scales
    steppers[i]->setSpeed(0); // Start stopped
  }
  
  // Set up enable pin
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW); // Motors enabled at startup (LOW = enabled)
  
  // NOTE: Microstepping pins (MS1, MS2, MS3) are NOT controlled here.
  // They must be set via hardware jumpers to match DEFAULT_MICROSTEP.
  
  Serial.println(F("Motors initialized"));
}

// --- Motor Control ---
void updateMotors(unsigned long currentMillis, bool paused) {
  // Stop motors immediately if paused
  if (paused) {
    // Ensure motors are stopped if they were moving
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      if (steppers[i]->speed() != 0) {
        steppers[i]->setSpeed(0);
      }
    }
    // We still need to call runSpeed() to potentially decelerate
    for (byte i = 0; i < MOTORS_COUNT; i++) {
        steppers[i]->runSpeed();
    }
    return; 
  }
  
  // Update LFO phases and motor speeds if it's time
  unsigned long deltaMillis = currentMillis - lastMotorUpdateTime;
  if (deltaMillis >= LFO_UPDATE_INTERVAL) {
    bool speedNeedsUpdate = false; // Flag if any LFO caused a change
    
    // Update LFO phases first
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      if (motorSettings[i].lfoRate > 0 && motorSettings[i].lfoDepth > 0) {
        unsigned int phaseIncrement = (unsigned int)((motorSettings[i].lfoRate * deltaMillis * LFO_RESOLUTION) / 1000);
        motorSettings[i].lfoPhase = (motorSettings[i].lfoPhase + phaseIncrement) % LFO_RESOLUTION;
        speedNeedsUpdate = true; // LFO is active, speed calculation needed
      }
    }
    
    // Update motor speeds if LFO is active or if base speed potentially changed
    // For simplicity, we recalculate speeds every interval if not paused.
    // Optimization: could track if settings changed, but interval is small.
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      float stepsPerSecond = calculateMotorStepRate(i);
      steppers[i]->setSpeed(stepsPerSecond);
    }
    
    lastMotorUpdateTime = currentMillis;
  }
  
  // Run the motors (this needs to be called frequently)
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    steppers[i]->runSpeed();
  }
}

// Helper function to calculate motor step rate including LFO
float calculateMotorStepRate(byte motorIndex) {
  // Base steps per second calculation:
  // Speed (Revolutions per Second) = (1 / masterTime_seconds) * wheelSpeed_ratio
  // Steps per Second = Speed (RPS) * stepsPerRev
  // masterTime is in ms, so masterTime_seconds = masterTime / 1000.0
  // RPS = (1000.0 / masterTime) * motorSettings[motorIndex].wheelSpeed
  float baseStepsPerSecond = (1000.0 / masterTime) * motorSettings[motorIndex].wheelSpeed * stepsPerRev;
  
  // Apply LFO if enabled
  if (motorSettings[motorIndex].lfoDepth > 0) {
    float sinVal = sin(2.0 * PI * motorSettings[motorIndex].lfoPhase / LFO_RESOLUTION);
    float lfoFactor;
    if (motorSettings[motorIndex].lfoPolarity) { // Bipolar
      lfoFactor = 1.0 + sinVal * (motorSettings[motorIndex].lfoDepth / 100.0);
    } else { // Unipolar
      lfoFactor = 1.0 + (sinVal + 1.0) * 0.5 * (motorSettings[motorIndex].lfoDepth / 100.0);
    }
    return baseStepsPerSecond * lfoFactor;
  }
  
  return baseStepsPerSecond;
}

void stopAllMotors() {
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    steppers[i]->stop(); // Use stop() for abrupt stop with deceleration if configured
    // or steppers[i]->setSpeed(0); for immediate speed change
  }
  Serial.println(F("Motors stopped"));
}

void enableAllMotors() {
  digitalWrite(ENABLE_PIN, LOW); // LOW = enabled for most drivers
  Serial.println(F("Motors enabled"));
}

void disableAllMotors() {
  digitalWrite(ENABLE_PIN, HIGH); // HIGH = disabled for most drivers
  Serial.println(F("Motors disabled"));
}

// --- Microstepping Control ---
bool updateMicrostepMode(byte newMode) {
  // Verify that the microstep value is valid (power of 2 up to 128)
  bool validMicrostep = false;
  for (byte i = 0; i < NUM_VALID_MICROSTEPS; i++) {
    if (newMode == VALID_MICROSTEPS[i]) {
      validMicrostep = true;
      break;
    }
  }
  
  if (!validMicrostep) {
    Serial.print(F("Error: Invalid microstep value: "));
    Serial.println(newMode);
    return false;
  }
  
  // Only update if the mode has changed
  if (newMode != currentMicrostepMode) {
      currentMicrostepMode = newMode;
      
      // Update steps per revolution based on the new mode
      stepsPerRev = 200 * currentMicrostepMode;
      
      // Update AccelStepper parameters (MaxSpeed/Acceleration scale with microsteps)
      for (byte i = 0; i < MOTORS_COUNT; i++) {
        steppers[i]->setMaxSpeed(10000.0 * currentMicrostepMode);
        steppers[i]->setAcceleration(2000.0 * currentMicrostepMode);
      }
      
      Serial.print(F("Microstep mode set to: "));
      Serial.println(currentMicrostepMode);
  } 
  return true;
  // NOTE: No digitalWrite calls for MS1/MS2/MS3 - jumpers handle this.
}

unsigned long getStepsPerWheelRev() {
  return stepsPerRev;
}

// --- Getter Functions ---
float getWheelSpeed(byte motorIndex) {
  if (motorIndex >= MOTORS_COUNT) return 0.0;
  return motorSettings[motorIndex].wheelSpeed;
}

float getLfoDepth(byte motorIndex) {
  if (motorIndex >= MOTORS_COUNT) return 0.0;
  return motorSettings[motorIndex].lfoDepth;
}

float getLfoRate(byte motorIndex) {
  if (motorIndex >= MOTORS_COUNT) return 0.0;
  return motorSettings[motorIndex].lfoRate;
}

bool getLfoPolarity(byte motorIndex) {
  if (motorIndex >= MOTORS_COUNT) return false;
  return motorSettings[motorIndex].lfoPolarity;
}

float getMasterTime() {
  return masterTime;
}

byte getCurrentMicrostepMode() {
  return currentMicrostepMode;
}

float getCurrentActualSpeed(byte motorIndex) {
  // Return the actual calculated speed in steps/sec for diagnostics
  if (motorIndex >= MOTORS_COUNT) return 0.0;
  return calculateMotorStepRate(motorIndex); // Includes LFO effect
  
  // To return RPM: (calculateMotorStepRate(motorIndex) / stepsPerRev) * 60.0
}

// --- Setter Functions ---
void setWheelSpeed(byte motorIndex, float speed) {
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return;
  }
  
  // Apply constraints - adjust as needed
  if (speed < -10.0) speed = -10.0;
  else if (speed > 10.0) speed = 10.0;
  
  motorSettings[motorIndex].wheelSpeed = speed;
  // Serial feedback can be added here if desired
}

void setLfoDepth(byte motorIndex, float depth) {
  if (motorIndex >= MOTORS_COUNT) return;
  
  // Apply constraints
  if (depth < 0) depth = 0;
  else if (depth > LFO_DEPTH_MAX) depth = LFO_DEPTH_MAX;
  
  motorSettings[motorIndex].lfoDepth = depth;
}

void setLfoRate(byte motorIndex, float rate) {
  if (motorIndex >= MOTORS_COUNT) return;
  
  // Apply constraints
  if (rate < 0) rate = 0;
  else if (rate > LFO_RATE_MAX) rate = LFO_RATE_MAX;
  
  motorSettings[motorIndex].lfoRate = rate;
}

void setLfoPolarity(byte motorIndex, bool isBipolar) {
  if (motorIndex >= MOTORS_COUNT) return;
  motorSettings[motorIndex].lfoPolarity = isBipolar;
}

void setMasterTime(float time) {
  // Apply constraints (e.g., minimum time to prevent excessive speed)
  if (time < 10.0) time = 10.0; // Min 10 ms period
  else if (time > 60000.0) time = 60000.0; // Max 1 min period
  
  masterTime = time;
}

// --- Reset Function ---

// Public function to reset all settings
void resetToDefaults() {
    resetMotorSettings();
    // Apply the reset settings to the running motors
    // updateMicrostepMode handles AccelStepper updates
    updateMicrostepMode(DEFAULT_MICROSTEP);
    // Speeds will update on the next updateMotors call
    Serial.println(F("All motor parameters reset to defaults"));
}

// Internal helper to reset static variables
static void resetMotorSettings() {
  masterTime = DEFAULT_MASTER_TIME;
  currentMicrostepMode = DEFAULT_MICROSTEP; // Keep track of the intended mode
  stepsPerRev = 200 * currentMicrostepMode;
  
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    motorSettings[i].wheelSpeed = DEFAULT_SPEED_RATIO;
    motorSettings[i].lfoDepth = DEFAULT_LFO_DEPTH;
    motorSettings[i].lfoRate = DEFAULT_LFO_RATE;
    motorSettings[i].lfoPolarity = DEFAULT_LFO_POLARITY;
    motorSettings[i].lfoPhase = 0;
  }
}

// // --- Motor Configuration ---
// void setMasterSpeed(float speed) {
//   // Bounds check: Ensure the speed is within reasonable limits
//   // ... (Implementation removed)
// }

// float getMasterSpeed() {
//   // ... (Implementation removed)
// }

// void setMotorRatio(byte motorIndex, float ratio) {
//   // ... (Implementation removed)
// }

// float getMotorRatio(byte motorIndex) {
//   // ... (Implementation removed)
// }

// void setMotorLfoDepth(byte motorIndex, byte depth) {
//   // ... (Implementation removed)
// }

// byte getMotorLfoDepth(byte motorIndex) {
//   // ... (Implementation removed)
// }

// void setMotorLfoRate(byte motorIndex, float rate) {
//   // ... (Implementation removed)
// }

// float getMotorLfoRate(byte motorIndex) {
//   // ... (Implementation removed)
// }

// void setMotorLfoPolarity(byte motorIndex, int polarity) {
//   // ... (Implementation removed)
// }

// int getMotorLfoPolarity(byte motorIndex) {
//   // ... (Implementation removed)
// }

// void setMicrostepMode(int microsteps) {
//   // ... (Implementation removed)
// }

// int getMicrostepMode() {
//   // ... (Implementation removed)
// }

// void resetAllMotorsToDefaults() {
//   // ... (Implementation removed)
// } 