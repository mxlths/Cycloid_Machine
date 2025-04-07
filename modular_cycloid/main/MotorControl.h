/**
 * MotorControl.h
 * 
 * Manages stepper motor control and LFO functions for the Cycloid Machine
 */

#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H

#include "Config.h"

// Motor setup functions
void setupMotors();
void stopAllMotors();
bool updateMicrostepMode(byte newMode);
unsigned long getStepsPerWheelRev();

// Motor control functions
void updateMotors(unsigned long currentMillis);
void updateMotorSpeeds();
float calculateLfoModulation(byte motorIndex);
void calculateStepsPerSecond(byte motorIndex);

// Menu action functions
void applyRatioPreset(byte presetIndex);
void resetToDefaults();

#endif // MOTOR_CONTROL_H 