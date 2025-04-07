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
void enableAllMotors();
void disableAllMotors();
void resetToDefaults();

// Motor control functions
void updateMotors(unsigned long currentMillis, bool paused);

// --- Getter Functions ---
float getWheelSpeed(byte motorIndex);
float getLfoDepth(byte motorIndex);
float getLfoRate(byte motorIndex);
bool getLfoPolarity(byte motorIndex);
float getMasterTime();
byte getCurrentMicrostepMode();
float getCurrentActualSpeed(byte motorIndex); // For status display

// --- Setter Functions ---
void setWheelSpeed(byte motorIndex, float speed);
void setLfoDepth(byte motorIndex, float depth);
void setLfoRate(byte motorIndex, float rate);
void setLfoPolarity(byte motorIndex, bool isBipolar);
void setMasterTime(float time);

#endif // MOTOR_CONTROL_H 