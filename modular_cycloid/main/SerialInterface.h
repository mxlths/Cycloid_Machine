/**
 * SerialInterface.h
 * 
 * Manages serial communication for the Cycloid Machine
 */

#ifndef SERIAL_INTERFACE_H
#define SERIAL_INTERFACE_H

#include "Config.h"

// Serial interface functions
void setupSerial();
void processSerialCommands();
void printSystemStatus();
void printHelp();

#endif // SERIAL_INTERFACE_H 