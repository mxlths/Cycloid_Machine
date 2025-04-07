/**
 * MenuSystem.h
 * 
 * Manages LCD display and menu navigation for the Cycloid Machine
 */

#ifndef MENU_SYSTEM_H
#define MENU_SYSTEM_H

#include "Config.h"

// LCD display functions
void setupLCD();
void updateDisplay();

// Menu navigation functions
void initializeMenu();
void handleMenuNavigation(int change);
void handleMenuSelection();
void handleMenuReturn();

// Function to get the current pause state
bool getSystemPaused();

// Function to set the pause state externally (e.g., from Serial)
void setSystemPaused(bool pause);

// Submenu handler functions
// void handleSpeedMenu(int change);
// void handleLfoMenu(int change);
// void handleRatioMenu(int change);
// void handleMasterMenu(int change);
// void handleMicrostepMenu(int change);
// void handleResetMenu(int change);

#endif // MENU_SYSTEM_H 