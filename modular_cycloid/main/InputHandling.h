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
// void updateEncoderPosition(); // This is often an ISR, keep it internal/static
void checkButtonPress(); // Called from loop, keep public

// The following are primarily internal logic or forwarders, can be removed from public header
// void processEncoderChange(int change); // Becomes static internal
// Button press handlers
// void handleShortPress(); // Becomes static internal
// void handleLongPress(); // Becomes static internal

#endif // INPUT_HANDLING_H 