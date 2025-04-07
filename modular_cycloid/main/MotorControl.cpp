/**
 * MotorControl.cpp
 * 
 * Implements stepper motor control and LFO functions for the Cycloid Machine
 */

#include <Arduino.h>
#include <AccelStepper.h>
#include "MotorControl.h"
#include "Config.h"
#include <math.h>

// --- Motor Instance Definitions ---
AccelStepper stepper1(AccelStepper::DRIVER, STEP_PIN_1, DIR_PIN_1);
AccelStepper stepper2(AccelStepper::DRIVER, STEP_PIN_2, DIR_PIN_2);
AccelStepper stepper3(AccelStepper::DRIVER, STEP_PIN_3, DIR_PIN_3);
AccelStepper stepper4(AccelStepper::DRIVER, STEP_PIN_4, DIR_PIN_4);

// Array of stepper pointers for easier iteration
AccelStepper* steppers[MOTORS_COUNT] = {&stepper1, &stepper2, &stepper3, &stepper4};

// --- Motor Settings ---
// Variables to store the state of each motor
struct MotorSetting {
  float wheelSpeed;  // Base wheel speed (ratio) before LFO
  float lfoDepth;    // LFO depth (0-100%)
  float lfoRate;     // LFO rate in Hz
  bool lfoPolarity;  // false = unipolar, true = bipolar
  unsigned int lfoPhase; // Current phase of the LFO (0-999)
};

static MotorSetting motorSettings[MOTORS_COUNT];

// Master time (period) in milliseconds
static float masterTime = DEFAULT_MASTER_SPEED;

// Microstepping mode
static byte currentMicrostepMode = DEFAULT_MICROSTEP;

// LFO update timing
static unsigned long lastMotorUpdateTime = 0;
static const int MOTOR_UPDATE_INTERVAL = 5; // ms

// Steps per full wheel revolution
static unsigned long stepsPerRev = 200 * DEFAULT_MICROSTEP; // Standard stepper = 200 steps, multiplied by microstep setting

// --- Motor Setup ---
void setupMotors() {
  // Set up each stepper motor with initial values
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    steppers[i]->setMaxSpeed(10000); // Set a high max speed initially
    steppers[i]->setAcceleration(2000); // Moderate acceleration
    steppers[i]->setSpeed(0); // Start with motor stopped
    
    // Initialize motor settings
    motorSettings[i].wheelSpeed = DEFAULT_SPEED_RATIO;
    motorSettings[i].lfoDepth = DEFAULT_LFO_DEPTH;
    motorSettings[i].lfoRate = DEFAULT_LFO_RATE;
    motorSettings[i].lfoPolarity = (DEFAULT_LFO_POLARITY == 1);
    motorSettings[i].lfoPhase = 0;
  }
  
  // Set up enable pins
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW); // Motors enabled at startup (LOW = enabled)
  
  // Setup microstepping pins
  pinMode(MS1_PIN, OUTPUT);
  pinMode(MS2_PIN, OUTPUT);
  pinMode(MS3_PIN, OUTPUT);
  
  // Set default microstepping mode
  updateMicrostepMode(DEFAULT_MICROSTEP);
  
  Serial.println(F("Motors initialized"));
}

// --- Motor Speed Control ---
void updateMotors(unsigned long currentMillis, bool paused) {
  // Skip motor updates if system is paused
  if (paused) return;
  
  // Update LFO phases and motor speeds if it's time
  unsigned long deltaMillis = currentMillis - lastMotorUpdateTime;
  if (deltaMillis >= MOTOR_UPDATE_INTERVAL) {
    // For each motor, update LFO phase and speed
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      // Update LFO phase if LFO is active
      if (motorSettings[i].lfoRate > 0 && motorSettings[i].lfoDepth > 0) {
        // Calculate phase increment based on rate and time delta
        unsigned int phaseIncrement = (unsigned int)((motorSettings[i].lfoRate * deltaMillis * LFO_RESOLUTION) / 1000);
        motorSettings[i].lfoPhase = (motorSettings[i].lfoPhase + phaseIncrement) % LFO_RESOLUTION;
      }
      
      // Calculate final motor speed including LFO
      float stepsPerSecond = calculateMotorStepRate(i);
      
      // Set the motor speed
      steppers[i]->setSpeed(stepsPerSecond);
      
      // Run the motor at the calculated speed
      steppers[i]->runSpeed();
    }
    
    lastMotorUpdateTime = currentMillis;
  }
}

// Helper function to calculate motor step rate including LFO
float calculateMotorStepRate(byte motorIndex) {
  // Base steps per second from master time and wheel speed ratio
  float baseStepsPerSecond = (60000.0 / masterTime) * motorSettings[motorIndex].wheelSpeed * (stepsPerRev / 360.0);
  
  // Apply LFO if enabled
  if (motorSettings[motorIndex].lfoDepth > 0) {
    // Generate sine wave from current phase
    float sinVal = sin(2 * PI * motorSettings[motorIndex].lfoPhase / LFO_RESOLUTION);
    
    // Apply depth scaling and polarity
    float lfoFactor;
    if (motorSettings[motorIndex].lfoPolarity) {
      // Bipolar: Vary above and below base speed
      lfoFactor = 1.0 + sinVal * (motorSettings[motorIndex].lfoDepth / 100.0);
    } else {
      // Unipolar: Vary only above base speed
      lfoFactor = 1.0 + (sinVal + 1.0) * 0.5 * (motorSettings[motorIndex].lfoDepth / 100.0);
    }
    
    return baseStepsPerSecond * lfoFactor;
  }
  
  return baseStepsPerSecond;
}

void stopAllMotors() {
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    steppers[i]->setSpeed(0);
    steppers[i]->runSpeed();
  }
  Serial.println(F("Motors stopped"));
}

// --- Microstepping Control ---
bool updateMicrostepMode(byte newMode) {
  // Verify that the microstep value is valid
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
  
  currentMicrostepMode = newMode;
  
  // Update steps per revolution
  stepsPerRev = 200 * currentMicrostepMode;
  
  // Set the physical pins for microstepping
  // Note: This implementation is for A4988 drivers. Adjust for your specific driver
  bool ms1, ms2, ms3;
  
  switch (currentMicrostepMode) {
    case 1: // Full step
      ms1 = LOW; ms2 = LOW; ms3 = LOW;
      break;
    case 2: // Half step
      ms1 = HIGH; ms2 = LOW; ms3 = LOW;
      break;
    case 4: // Quarter step
      ms1 = LOW; ms2 = HIGH; ms3 = LOW;
      break;
    case 8: // Eighth step
      ms1 = HIGH; ms2 = HIGH; ms3 = LOW;
      break;
    case 16: // Sixteenth step
      ms1 = HIGH; ms2 = HIGH; ms3 = HIGH;
      break;
    case 32: // Thirty-second step (if available)
    case 64: // Sixty-fourth step (if available)
    case 128: // 128th step (if available)
      // These might require different driver or additional logic
      ms1 = HIGH; ms2 = HIGH; ms3 = HIGH;
      break;
    default:
      // Default to full step if invalid
      ms1 = LOW; ms2 = LOW; ms3 = LOW;
      break;
  }
  
  // Set microstepping pins for all motors
  digitalWrite(MS1_PIN, ms1);
  digitalWrite(MS2_PIN, ms2);
  digitalWrite(MS3_PIN, ms3);
  
  Serial.print(F("Microstep mode set to: "));
  Serial.println(currentMicrostepMode);
  
  // Update max speed for all steppers based on new microstepping
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    float maxSpeed = 10000.0 * currentMicrostepMode;
    steppers[i]->setMaxSpeed(maxSpeed);
  }
  
  return true;
}

unsigned long getStepsPerWheelRev() {
  return stepsPerRev;
}

// --- Getter Functions ---
float getWheelSpeed(byte motorIndex) {
  // Bounds check
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return 0.0;
  }
  return motorSettings[motorIndex].wheelSpeed;
}

float getLfoDepth(byte motorIndex) {
  // Bounds check
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return 0.0;
  }
  return motorSettings[motorIndex].lfoDepth;
}

float getLfoRate(byte motorIndex) {
  // Bounds check
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return 0.0;
  }
  return motorSettings[motorIndex].lfoRate;
}

bool getLfoPolarity(byte motorIndex) {
  // Bounds check
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return false;
  }
  return motorSettings[motorIndex].lfoPolarity;
}

float getMasterTime() {
  return masterTime;
}

byte getCurrentMicrostepMode() {
  return currentMicrostepMode;
}

float getCurrentActualSpeed(byte motorIndex) {
  // Return the actual calculated speed in RPM for display purposes
  if (motorIndex >= MOTORS_COUNT) return 0.0;
  
  // Base RPM from master time and wheel speed ratio
  float baseRpm = 60000.0 / masterTime * motorSettings[motorIndex].wheelSpeed;
  
  // TODO: Include current LFO effect if needed
  
  return baseRpm;
}

// --- Setter Functions ---
void setWheelSpeed(byte motorIndex, float speed) {
  // Bounds check: Ensure the motor index is valid
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return;
  }
  
  // Bounds check: Reasonable speed limits to prevent excessive speeds
  if (speed < -10.0) {
    speed = -10.0;
    Serial.println(F("Warning: Wheel speed limited to min value (-10.0)"));
  } else if (speed > 10.0) {
    speed = 10.0;
    Serial.println(F("Warning: Wheel speed limited to max value (10.0)"));
  }
  
  motorSettings[motorIndex].wheelSpeed = speed;
  Serial.print(F("Motor "));
  Serial.print(motorIndex + 1);
  Serial.print(F(" wheel speed set to: "));
  Serial.println(speed);
}

void setLfoDepth(byte motorIndex, float depth) {
  // Bounds check: Ensure the motor index is valid
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return;
  }
  
  // Bounds check: Ensure LFO depth is within valid range
  if (depth < 0) {
    depth = 0;
    Serial.println(F("Warning: LFO depth limited to min value (0)"));
  } else if (depth > LFO_DEPTH_MAX) {
    depth = LFO_DEPTH_MAX;
    Serial.println(F("Warning: LFO depth limited to max value"));
  }
  
  motorSettings[motorIndex].lfoDepth = depth;
  Serial.print(F("Motor "));
  Serial.print(motorIndex + 1);
  Serial.print(F(" LFO depth set to: "));
  Serial.println(depth);
}

void setLfoRate(byte motorIndex, float rate) {
  // Bounds check: Ensure the motor index is valid
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return;
  }
  
  // Bounds check: Ensure LFO rate is within valid range
  if (rate < 0) {
    rate = 0;
    Serial.println(F("Warning: LFO rate limited to min value (0)"));
  } else if (rate > LFO_RATE_MAX) {
    rate = LFO_RATE_MAX;
    Serial.println(F("Warning: LFO rate limited to max value"));
  }
  
  motorSettings[motorIndex].lfoRate = rate;
  Serial.print(F("Motor "));
  Serial.print(motorIndex + 1);
  Serial.print(F(" LFO rate set to: "));
  Serial.println(rate);
}

void setLfoPolarity(byte motorIndex, bool isBipolar) {
  // Bounds check: Ensure the motor index is valid
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return;
  }
  
  motorSettings[motorIndex].lfoPolarity = isBipolar;
  Serial.print(F("Motor "));
  Serial.print(motorIndex + 1);
  Serial.print(F(" LFO polarity set to: "));
  Serial.println(isBipolar ? "Bipolar" : "Unipolar");
}

void setMasterTime(float time) {
  // Bounds check: Ensure the time is within reasonable limits
  if (time < 10) {
    time = 10; // Lower limit for safety
    Serial.println(F("Warning: Master time limited to min value (10ms)"));
  } else if (time > 10000) {
    time = 10000; // Upper limit
    Serial.println(F("Warning: Master time limited to max value (10000ms)"));
  }
  
  masterTime = time;
  Serial.print(F("Master time set to: "));
  Serial.println(masterTime);
}

void enableAllMotors() {
  digitalWrite(ENABLE_PIN_ALL, LOW); // LOW = enabled for most drivers
  Serial.println(F("Motors enabled"));
}

void disableAllMotors() {
  digitalWrite(ENABLE_PIN_ALL, HIGH); // HIGH = disabled for most drivers
  Serial.println(F("Motors disabled"));
}

void resetAllMotorsToDefaults() {
  // Set master speed to default
  setMasterTime(DEFAULT_MASTER_TIME);
  
  // Reset all motor ratios to default
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    setWheelSpeed(i, DEFAULT_WHEEL_SPEED);
    setLfoDepth(i, DEFAULT_LFO_DEPTH);
    setLfoRate(i, DEFAULT_LFO_RATE);
    setLfoPolarity(i, DEFAULT_LFO_POLARITY);
  }
  
  // Reset microstep mode to default
  updateMicrostepMode(DEFAULT_MICROSTEP);
  
  Serial.println(F("All motor parameters reset to defaults"));
}

// --- Motor Configuration ---
void setMasterSpeed(float speed) {
  // Bounds check: Ensure the speed is within reasonable limits
  if (speed < 0) {
    speed = 0; // Cannot have negative master speed
    Serial.println(F("Warning: Master speed limited to min value (0)"));
  } else if (speed > 1000) {
    speed = 1000; // Upper limit for motor safety
    Serial.println(F("Warning: Master speed limited to max value (1000)"));
  }
  
  masterTime = constrain(speed, 0.01, 999.99);
  Serial.print(F("Master speed set to: "));
  Serial.println(masterTime);
}

float getMasterSpeed() {
  return masterTime;
}

void setMotorRatio(byte motorIndex, float ratio) {
  // Bounds check: Ensure the motor index is valid
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return;
  }
  
  // Bounds check: Reasonable ratio limits to prevent excessive speeds
  if (ratio < -10.0) {
    ratio = -10.0;
    Serial.println(F("Warning: Ratio limited to min value (-10.0)"));
  } else if (ratio > 10.0) {
    ratio = 10.0;
    Serial.println(F("Warning: Ratio limited to max value (10.0)"));
  }
  
  motorSettings[motorIndex].wheelSpeed = constrain(ratio, 0.1, 256.0);
  Serial.print(F("Motor "));
  Serial.print(motorIndex + 1);
  Serial.print(F(" ratio set to: "));
  Serial.println(ratio);
}

float getMotorRatio(byte motorIndex) {
  // Bounds check
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return 0.0;
  }
  return motorSettings[motorIndex].wheelSpeed;
}

void setMotorLfoDepth(byte motorIndex, byte depth) {
  // Bounds check: Ensure the motor index is valid
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return;
  }
  
  // Bounds check: Ensure LFO depth is within valid range
  if (depth > LFO_DEPTH_MAX) {
    depth = LFO_DEPTH_MAX;
    Serial.println(F("Warning: LFO depth limited to max value"));
  }
  
  motorSettings[motorIndex].lfoDepth = constrain(depth, 0.0, 100.0);
  Serial.print(F("Motor "));
  Serial.print(motorIndex + 1);
  Serial.print(F(" LFO depth set to: "));
  Serial.println(depth);
}

byte getMotorLfoDepth(byte motorIndex) {
  // Bounds check
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return 0;
  }
  return (byte)motorSettings[motorIndex].lfoDepth;
}

void setMotorLfoRate(byte motorIndex, float rate) {
  // Bounds check: Ensure the motor index is valid
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return;
  }
  
  // Bounds check: Ensure LFO rate is within valid range
  if (rate < 0) {
    rate = 0;
    Serial.println(F("Warning: LFO rate limited to min value (0)"));
  } else if (rate > LFO_RATE_MAX) {
    rate = LFO_RATE_MAX;
    Serial.println(F("Warning: LFO rate limited to max value"));
  }
  
  motorSettings[motorIndex].lfoRate = constrain(rate, 0.0, 256.0);
  Serial.print(F("Motor "));
  Serial.print(motorIndex + 1);
  Serial.print(F(" LFO rate set to: "));
  Serial.println(rate);
}

float getMotorLfoRate(byte motorIndex) {
  // Bounds check
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return 0.0;
  }
  return motorSettings[motorIndex].lfoRate;
}

void setMotorLfoPolarity(byte motorIndex, int polarity) {
  // Bounds check: Ensure the motor index is valid
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return;
  }
  
  // Bounds check: Ensure polarity is either -1, 0, or 1
  if (polarity < -1) polarity = -1;
  else if (polarity > 1) polarity = 1;
  
  motorSettings[motorIndex].lfoPolarity = (polarity == 1);
  Serial.print(F("Motor "));
  Serial.print(motorIndex + 1);
  Serial.print(F(" LFO polarity set to: "));
  Serial.println(polarity);
}

int getMotorLfoPolarity(byte motorIndex) {
  // Bounds check
  if (motorIndex >= MOTORS_COUNT) {
    Serial.print(F("Error: Invalid motor index: "));
    Serial.println(motorIndex);
    return 0;
  }
  return (motorSettings[motorIndex].lfoPolarity ? 1 : 0);
}

void setMicrostepMode(int microsteps) {
  // Verify that the microstep value is valid
  bool validMicrostep = false;
  for (byte i = 0; i < NUM_VALID_MICROSTEPS; i++) {
    if (microsteps == VALID_MICROSTEPS[i]) {
      validMicrostep = true;
      break;
    }
  }
  
  if (!validMicrostep) {
    Serial.print(F("Error: Invalid microstep value: "));
    Serial.println(microsteps);
    return;
  }
  
  updateMicrostepMode(microsteps);
}

int getMicrostepMode() {
  return currentMicrostepMode;
} 