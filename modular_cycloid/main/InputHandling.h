/**
 * InputHandling.h
 * 
 * Manages rotary encoder and button input for the Cycloid Machine
 */

#ifndef INPUT_HANDLING_H
#define INPUT_HANDLING_H

#include "Config.h"

// Encoder setup and input detection
void setupEncoder();
void updateEncoderPosition();
void checkButtonPress();
void processEncoderChange(int change);

// Button press handlers
void handleShortPress();
void handleLongPress();

#endif // INPUT_HANDLING_H 