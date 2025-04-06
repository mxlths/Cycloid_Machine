/**
 * MenuSystem.cpp
 * 
 * Implements LCD display and menu navigation for the Cycloid Machine
 */

#include "MenuSystem.h"
#include "MotorControl.h"

// Initialize the LCD
void setupLCD() {
  Wire.begin();
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(F("Cycloid Machine"));
  lcd.setCursor(0, 1);
  lcd.print(F("Starting..."));
  
  delay(1000);  // Show startup message
}

// Update the LCD display based on current menu and state
void updateDisplay() {
  lcd.clear();
  
  // Format strings for display
  char line1[LCD_COLS + 1];
  char line2[LCD_COLS + 1];
  
  if (systemPaused) {
    strcpy(line1, "** SYSTEM **");
    strcpy(line2, "*** PAUSED ***");
  } else {
    switch (currentMenu) {
      case MENU_MAIN:
        // Show main menu with selected option
        switch (selectedOption) {
          case 0:
            strcpy(line1, ">SPEED");
            strcpy(line2, " LFO RATIO MSTR");
            break;
          case 1:
            strcpy(line1, ">LFO");
            strcpy(line2, " RATIO MSTR RST");
            break;
          case 2:
            strcpy(line1, ">RATIO");
            strcpy(line2, " MSTR RST SPEED");
            break;
          case 3:
            strcpy(line1, ">MASTER");
            strcpy(line2, " RST SPEED LFO");
            break;
          case 4:
            strcpy(line1, ">RESET");
            strcpy(line2, " SPEED LFO RATIO");
            break;
        }
        break;
        
      case MENU_SPEED:
        // Show wheel selection and speed
        if (editingSpeed) {
          sprintf(line1, "SPEED: %s#", wheelLabels[selectedSpeedWheel]);
        } else {
          sprintf(line1, "SPEED: %s", wheelLabels[selectedSpeedWheel]);
        }
        sprintf(line2, "Value: %05.1f", wheelSpeeds[selectedSpeedWheel]);
        break;
        
      case MENU_LFO:
        // Show LFO parameter selection and value
        byte wheelIndex = selectedLfoParam / 3;
        byte paramType = selectedLfoParam % 3;
        
        if (paramType == 0) {  // Depth
          if (editingLfo) {
            sprintf(line1, "LFO: %s DPT#", wheelLabels[wheelIndex]);
          } else {
            sprintf(line1, "LFO: %s DPT", wheelLabels[wheelIndex]);
          }
          sprintf(line2, "Value: %05.1f%%", lfoDepths[wheelIndex]);
        }
        else if (paramType == 1) {  // Rate
          if (editingLfo) {
            sprintf(line1, "LFO: %s RTE#", wheelLabels[wheelIndex]);
          } else {
            sprintf(line1, "LFO: %s RTE", wheelLabels[wheelIndex]);
          }
          sprintf(line2, "Value: %05.1f", lfoRates[wheelIndex]);
        }
        else {  // Polarity
          if (editingLfo) {
            sprintf(line1, "LFO: %s POL#", wheelLabels[wheelIndex]);
          } else {
            sprintf(line1, "LFO: %s POL", wheelLabels[wheelIndex]);
          }
          sprintf(line2, "Value: %s", lfoPolarities[wheelIndex] ? "BI" : "UNI");
        }
        break;
        
      case MENU_RATIO:
        if (confirmingRatio) {
          strcpy(line1, "APPLY RATIO?");
          if (ratioChoice) {
            strcpy(line2, " NO   >YES");
          } else {
            strcpy(line2, ">NO    YES");
          }
        } else {
          sprintf(line1, "RATIO PRESET: %d", selectedRatioPreset + 1);
          
          // Format the ratio values in a compact way
          char ratio[17];
          sprintf(ratio, "%g:%g:%g:%g", 
                  ratioPresets[selectedRatioPreset][0],
                  ratioPresets[selectedRatioPreset][1],
                  ratioPresets[selectedRatioPreset][2],
                  ratioPresets[selectedRatioPreset][3]);
          strcpy(line2, ratio);
        }
        break;
        
      case MENU_MASTER:
        if (editingMaster) {
          strcpy(line1, "MASTER TIME:#");
        } else {
          strcpy(line1, "MASTER TIME:");
        }
        sprintf(line2, "Value: %06.2f S", masterTime);
        break;
        
      case MENU_RESET:
        if (confirmingReset) {
          strcpy(line1, "RESET TO DEFLT?");
          if (resetChoice) {
            strcpy(line2, " NO   >YES");
          } else {
            strcpy(line2, ">NO    YES");
          }
        } else {
          strcpy(line1, "RESET");
          strcpy(line2, "Press to confirm");
        }
        break;
    }
  }
  
  // Ensure strings fit in LCD columns
  line1[LCD_COLS] = '\0';
  line2[LCD_COLS] = '\0';
  
  // Update LCD
  lcd.setCursor(0, 0);
  lcd.print(line1);
  lcd.setCursor(0, 1);
  lcd.print(line2);
}

// Enter a submenu and initialize its state
void enterSubmenu(byte menu) {
  currentMenu = menu;
  
  // Initialize submenu state
  switch (currentMenu) {
    case MENU_SPEED:
      selectedSpeedWheel = 0;
      editingSpeed = false;
      break;
      
    case MENU_LFO:
      selectedLfoParam = 0;
      editingLfo = false;
      break;
      
    case MENU_RATIO:
      selectedRatioPreset = 0;
      confirmingRatio = false;
      break;
      
    case MENU_MASTER:
      editingMaster = false;
      break;
      
    case MENU_RESET:
      confirmingReset = true;  // Start with confirmation dialog
      resetChoice = false;     // Default to NO
      break;
  }
  
  updateDisplay();
}

// Return to the main menu, resetting submenu states
void returnToMainMenu() {
  currentMenu = MENU_MAIN;
  editingSpeed = false;
  editingLfo = false;
  editingMaster = false;
  confirmingRatio = false;
  confirmingReset = false;
  
  updateDisplay();
}

// Handle menu navigation based on encoder movement
void handleMenuNavigation(int change) {
  if (systemPaused && currentMenu != MENU_MAIN) return;
  
  switch (currentMenu) {
    case MENU_MAIN:
      // Cycle through main menu options
      selectedOption = (selectedOption + 5 + change) % 5;  // +5 to avoid negative values
      break;
      
    case MENU_SPEED:
      handleSpeedMenu(change);
      break;
      
    case MENU_LFO:
      handleLfoMenu(change);
      break;
      
    case MENU_RATIO:
      handleRatioMenu(change);
      break;
      
    case MENU_MASTER:
      handleMasterMenu(change);
      break;
      
    case MENU_RESET:
      handleResetMenu(change);
      break;
  }
  
  updateDisplay();
}

// Handle short button press for menu selection
void handleMenuSelection() {
  if (systemPaused && currentMenu != MENU_MAIN) return;
  
  switch (currentMenu) {
    case MENU_MAIN:
      // Enter selected submenu
      enterSubmenu(selectedOption + 1);  // +1 because MENU_MAIN is 0
      break;
      
    case MENU_SPEED:
      // Toggle editing mode
      editingSpeed = !editingSpeed;
      break;
      
    case MENU_LFO:
      // Toggle editing mode
      editingLfo = !editingLfo;
      break;
      
    case MENU_RATIO:
      if (!confirmingRatio) {
        // Enter confirmation mode
        confirmingRatio = true;
        ratioChoice = false;  // Default to NO
      } else {
        // Process confirmation choice
        if (ratioChoice) {  // YES selected
          applyRatioPreset(selectedRatioPreset);
          confirmingRatio = false;
          returnToMainMenu();
        } else {  // NO selected
          confirmingRatio = false;  // Return to ratio selection
        }
      }
      break;
      
    case MENU_MASTER:
      // Toggle editing mode
      editingMaster = !editingMaster;
      break;
      
    case MENU_RESET:
      if (confirmingReset) {
        // Process confirmation choice
        if (resetChoice) {  // YES selected
          resetToDefaults();
          confirmingReset = false;
          returnToMainMenu();
        } else {  // NO selected
          confirmingReset = false;
          returnToMainMenu();
        }
      }
      break;
  }
  
  updateDisplay();
}

// Handle menu return or system pause
void handleMenuReturn() {
  if (currentMenu == MENU_MAIN) {
    // Toggle pause
    systemPaused = !systemPaused;
    
    if (systemPaused) {
      // Stop all motors when paused
      stopAllMotors();
    }
  } else {
    // Return to main menu from any submenu
    returnToMainMenu();
  }
  
  updateDisplay();
}

// Handle SPEED menu navigation
void handleSpeedMenu(int change) {
  if (editingSpeed) {
    // Adjust selected wheel speed (0.1 increments)
    wheelSpeeds[selectedSpeedWheel] += change * 0.1;
    // Constrain to valid range
    if (wheelSpeeds[selectedSpeedWheel] < 0.1) wheelSpeeds[selectedSpeedWheel] = 0.1;
    if (wheelSpeeds[selectedSpeedWheel] > 256.0) wheelSpeeds[selectedSpeedWheel] = 256.0;
  } else {
    // Cycle through wheels
    selectedSpeedWheel = (selectedSpeedWheel + MOTORS_COUNT + change) % MOTORS_COUNT;
  }
}

// Handle LFO menu navigation
void handleLfoMenu(int change) {
  if (editingLfo) {
    byte wheelIndex = selectedLfoParam / 3;
    byte paramType = selectedLfoParam % 3;
    
    if (paramType == 0) {  // Depth (0-100%)
      lfoDepths[wheelIndex] += change * 0.1;
      if (lfoDepths[wheelIndex] < 0.0) lfoDepths[wheelIndex] = 0.0;
      if (lfoDepths[wheelIndex] > 100.0) lfoDepths[wheelIndex] = 100.0;
    }
    else if (paramType == 1) {  // Rate (0-256.0)
      lfoRates[wheelIndex] += change * 0.1;
      if (lfoRates[wheelIndex] < 0.0) lfoRates[wheelIndex] = 0.0;
      if (lfoRates[wheelIndex] > 256.0) lfoRates[wheelIndex] = 256.0;
    }
    else {  // Polarity (toggle UNI/BI)
      if (change != 0) lfoPolarities[wheelIndex] = !lfoPolarities[wheelIndex];
    }
  } else {
    // Cycle through LFO parameters (12 total: 4 wheels x 3 params)
    selectedLfoParam = (selectedLfoParam + 12 + change) % 12;
  }
}

// Handle RATIO menu navigation
void handleRatioMenu(int change) {
  if (confirmingRatio) {
    // Toggle YES/NO choice
    if (change != 0) ratioChoice = !ratioChoice;
  } else {
    // Cycle through ratio presets
    selectedRatioPreset = (selectedRatioPreset + 4 + change) % 4;
  }
}

// Handle MASTER menu navigation
void handleMasterMenu(int change) {
  if (editingMaster) {
    // Adjust master time (0.01 increments)
    masterTime += change * 0.01;
    // Constrain to valid range
    if (masterTime < 0.01) masterTime = 0.01;
    if (masterTime > 999.99) masterTime = 999.99;
  }
}

// Handle RESET menu navigation
void handleResetMenu(int change) {
  if (confirmingReset) {
    // Toggle YES/NO choice
    if (change != 0) resetChoice = !resetChoice;
  }
} 