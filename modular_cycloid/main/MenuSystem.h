/**
 * MenuSystem.h
 * 
 * Manages LCD display and menu navigation for the Cycloid Machine
 */

#ifndef MENU_SYSTEM_H
#define MENU_SYSTEM_H

#include "Config.h"

// Menu system functions
void setupLCD();
void updateDisplay();
void enterSubmenu(byte menu);
void returnToMainMenu();

// Menu navigation handlers
void handleMenuNavigation(int change);
void handleMenuSelection();
void handleMenuReturn();

// Menu specific handlers
void handleSpeedMenu(int change);
void handleLfoMenu(int change);
void handleRatioMenu(int change);
void handleMasterMenu(int change);
void handleResetMenu(int change);

#endif // MENU_SYSTEM_H 