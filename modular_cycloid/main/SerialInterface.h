/**
 * SerialInterface.h
 * 
 * Manages serial communication for the Cycloid Machine
 */

#ifndef SERIAL_INTERFACE_H
#define SERIAL_INTERFACE_H

#include "Config.h"

// Initialize serial communication
void setupSerialCommands();

// Process any available serial commands
void processSerialCommands();

// Execute a specific command
void executeCommand(char* command);

// Print system status
void printSystemStatus();

// Print help information
void printHelp();

#endif // SERIAL_INTERFACE_H 