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
void enterSubmenu(byte menu);
void returnToMainMenu();
void handleMenuNavigation(int change);
void handleMenuSelection();
void handleMenuReturn();

// Submenu handler functions
void handleSpeedMenu(int change);
void handleLfoMenu(int change);
void handleRatioMenu(int change);
void handleMasterMenu(int change);
void handleMicrostepMenu(int change);
void handleResetMenu(int change);

// External variable declarations
extern bool editingMicrostep;
extern const byte validMicrosteps[];
extern const byte microstepCount;
extern byte currentMicrostepIndex;

#endif // MENU_SYSTEM_H 