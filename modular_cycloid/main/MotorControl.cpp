/**
 * MotorControl.cpp
 * 
 * Implements stepper motor control and LFO functions for the Cycloid Machine
 */

#include "MotorControl.h"
#include <math.h>

// --- Internal State Variables ---

struct MotorSettings {
    float wheelSpeed = 10.0; // Default base speed
    float lfoDepth = 0.0;    // LFO Depth percentage (0-100)
    float lfoRate = 0.0;     // LFO Rate (cycles per masterTime)
    bool lfoPolarity = false; // false = UNI, true = BI
    float currentActualSpeed = 0.0; // Calculated steps/sec
    unsigned long lfoPhase = 0;     // LFO phase (0 to LFO_RESOLUTION-1)
};

static MotorSettings motorSettings[MOTORS_COUNT];
static byte currentMicrostepMode = MICROSTEP_FULL;  // Default to full step mode
static float masterTime = 1.00; // Master time in seconds for 1 rotation at speed 1.0
static unsigned long lastMotorUpdateTime = 0;

// --- Internal Helper Functions (moved declarations here) ---
static void updateMotorSpeeds();
static float calculateLfoModulation(byte motorIndex);

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
    // Serial printing can be removed or handled by the caller (Menu/Serial)
    // Serial.println(F("Invalid microstepping mode")); 
    return false;
  }
  
  currentMicrostepMode = newMode;
  
  // Reconfigure motor parameters
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    float maxSpeed = 10000.0 * currentMicrostepMode;
    steppers[i]->setMaxSpeed(maxSpeed);
    steppers[i]->setAcceleration(500 * currentMicrostepMode);
  }
  
  // Serial printing can be removed or handled by the caller
  // Serial.print(F("Microstepping mode set to "));
  // Serial.print(currentMicrostepMode);
  // Serial.println(F("x"));
  
  return true;
}

// Stop all motors
void stopAllMotors() {
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    steppers[i]->setSpeed(0);
  }
}

// Update motors - main control function called from loop
void updateMotors(unsigned long currentMillis, bool paused) {
  // Skip if paused
  if (paused) return;
  
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

// Update motor speeds based on current internal settings
static void updateMotorSpeeds() {
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    // Use internal motorSettings structure
    float baseSpeed = motorSettings[i].wheelSpeed;
    
    // Apply LFO modulation if enabled
    if (motorSettings[i].lfoRate > 0.0 && motorSettings[i].lfoDepth > 0.0) {
      float lfoMod = calculateLfoModulation(i);
      
      if (motorSettings[i].lfoPolarity) { // Bipolar
        baseSpeed += lfoMod;
      } else { // Unipolar
        baseSpeed = max(0.1, baseSpeed + lfoMod);
      }
    }
    
    // Use internal masterTime
    float stepsPerSecond = getStepsPerWheelRev() / (masterTime * baseSpeed);
    
    // Store calculated speed and set motor speed
    motorSettings[i].currentActualSpeed = stepsPerSecond;
    steppers[i]->setSpeed(stepsPerSecond);
    
    // Update LFO phases using internal settings
    if (motorSettings[i].lfoRate > 0.0) {
      float cycleRate = 1.0 / (masterTime * motorSettings[i].lfoRate);
      float phaseIncrement = (float)MOTOR_UPDATE_INTERVAL / 1000.0 * cycleRate * LFO_RESOLUTION;
      motorSettings[i].lfoPhase = (motorSettings[i].lfoPhase + (unsigned long)phaseIncrement) % LFO_RESOLUTION;
    }
  }
}

// Calculate LFO modulation for a motor using internal state
static float calculateLfoModulation(byte motorIndex) {
  // Use internal motorSettings
  float phase = (float)motorSettings[motorIndex].lfoPhase / LFO_RESOLUTION * 2.0 * PI;
  float sinValue = sin(phase);
  
  float baseSpeed = motorSettings[motorIndex].wheelSpeed;
  float depth = motorSettings[motorIndex].lfoDepth / 100.0;
  
  if (motorSettings[motorIndex].lfoPolarity) { // Bipolar
    return baseSpeed * depth * sinValue;
  } else { // Unipolar
    return baseSpeed * depth * (sinValue + 1.0) / 2.0;
  }
}

// --- Getter Implementations ---

float getWheelSpeed(byte motorIndex) {
  return (motorIndex < MOTORS_COUNT) ? motorSettings[motorIndex].wheelSpeed : 0.0;
}

float getLfoDepth(byte motorIndex) {
  return (motorIndex < MOTORS_COUNT) ? motorSettings[motorIndex].lfoDepth : 0.0;
}

float getLfoRate(byte motorIndex) {
  return (motorIndex < MOTORS_COUNT) ? motorSettings[motorIndex].lfoRate : 0.0;
}

bool getLfoPolarity(byte motorIndex) {
  return (motorIndex < MOTORS_COUNT) ? motorSettings[motorIndex].lfoPolarity : false;
}

float getMasterTime() {
  return masterTime;
}

byte getCurrentMicrostepMode() {
  return currentMicrostepMode;
}

float getCurrentActualSpeed(byte motorIndex) {
  return (motorIndex < MOTORS_COUNT) ? motorSettings[motorIndex].currentActualSpeed : 0.0;
}

// --- Setter Implementations ---

void setWheelSpeed(byte motorIndex, float speed) {
  if (motorIndex < MOTORS_COUNT) {
    motorSettings[motorIndex].wheelSpeed = constrain(speed, 0.1, 256.0); // Add constraints here
  }
}

void setLfoDepth(byte motorIndex, float depth) {
  if (motorIndex < MOTORS_COUNT) {
    motorSettings[motorIndex].lfoDepth = constrain(depth, 0.0, 100.0);
  }
}

void setLfoRate(byte motorIndex, float rate) {
  if (motorIndex < MOTORS_COUNT) {
    motorSettings[motorIndex].lfoRate = constrain(rate, 0.0, 256.0);
  }
}

void setLfoPolarity(byte motorIndex, bool isBipolar) {
  if (motorIndex < MOTORS_COUNT) {
    motorSettings[motorIndex].lfoPolarity = isBipolar;
  }
}

void setMasterTime(float time) {
  masterTime = constrain(time, 0.01, 999.99);
} 