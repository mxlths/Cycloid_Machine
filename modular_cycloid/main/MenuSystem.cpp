/**
 * MenuSystem.cpp
 * 
 * Implements LCD display and menu navigation for the Cycloid Machine
 */

#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

#include "MenuSystem.h"
#include "MotorControl.h"
#include "Config.h"

// --- LCD Instance ---
// Defined globally in main.ino, declared extern in Config.h
// extern LiquidCrystal_I2C lcd;

// --- Constants ---
const byte NUM_MAIN_OPTIONS = 7; // SPEED, LFO, RATIO, MASTER, MICROSTEP, RESET, PAUSE
const byte NUM_LFO_PARAMS_PER_WHEEL = 3; // Depth, Rate, Polarity
const byte NUM_LFO_PARAMS_TOTAL = MOTORS_COUNT * NUM_LFO_PARAMS_PER_WHEEL; // Calculate as needed, MOTORS_COUNT is from Config.h

// Remove duplicate definitions clashing with Config.h defines
// const byte NUM_RATIO_PRESETS = 4;
// const byte NUM_VALID_MICROSTEPS = 8;

// --- Menu State Variables ---
static MenuState currentMenu = MENU_MAIN;
static byte selectedMainMenuOption = 0;
static byte selectedSpeedWheel = 0;
static byte selectedLfoParam = 0;
static byte selectedRatioPreset = 0;
static byte selectedMicrostepIndex = 4; // Default to 16x microstepping index
static byte pendingMicrostepMode = DEFAULT_MICROSTEP; // Variable to hold pending selection
static byte selectedPauseOption = 0; // 0=ON, 1=OFF, 2=EXIT

// State flags for editing modes
static bool editingSpeed = false;
static bool editingLfo = false;
static bool editingMaster = false;
static bool editingMicrostep = false;
static bool confirmingRatio = false;
static bool confirmingReset = false;
static bool ratioChoice = false; // false=NO, true=YES for ratio preset confirmation
static bool resetChoice = false; // false=NO, true=YES for reset confirmation

// Pause state
static bool systemPaused = false;

// Variables for microstepping menu
const byte validMicrosteps[] = {1, 2, 4, 8, 16, 32, 64, 128};
const byte microstepCount = 8;
byte currentMicrostepIndex = 0; // Index in validMicrosteps array

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

// --- Forward Declarations for Static Functions ---
// Display Helpers
static void displayPaused(char* line1, char* line2);
static void displayMainMenu(char* line1, char* line2);
static void displaySpeedMenu(char* line1, char* line2);
static void displayLfoMenu(char* line1, char* line2);
static void displayRatioMenu(char* line1, char* line2);
static void displayMasterMenu(char* line1, char* line2);
static void displayMicrostepMenu(char* line1, char* line2);
static void displayResetMenu(char* line1, char* line2);
static void displayPauseMenu(char* line1, char* line2);

// Navigation/Action Helpers
static void handleSpeedMenu(int change);
static void handleLfoMenu(int change);
static void handleRatioMenu(int change);
static void handleMasterMenu(int change);
static void handleMicrostepMenu(int change);
static void handleResetMenu(int change);
static void handlePauseMenu(int change);
static void applyRatioPreset(byte presetIndex);
static void enterSubmenu(MenuState menu);
static void returnToMainMenu();

// Update the LCD display based on current menu and state
void updateDisplay() {
  lcd.clear();
  
  // Format strings for display
  char line1[LCD_COLS + 1];
  char line2[LCD_COLS + 1];
  
  // MODIFY switch to call helper functions - don't show special pause screen
  switch (currentMenu) {
    case MENU_MAIN:
      displayMainMenu(line1, line2);
      break;
      
    case MENU_SPEED:
      displaySpeedMenu(line1, line2);
      break;
      
    case MENU_LFO:
      displayLfoMenu(line1, line2);
      break;
      
    case MENU_RATIO:
      displayRatioMenu(line1, line2);
      break;
      
    case MENU_MASTER:
      displayMasterMenu(line1, line2);
      break;
      
    case MENU_MICROSTEP:
      displayMicrostepMenu(line1, line2);
      break;
      
    case MENU_RESET:
      displayResetMenu(line1, line2);
      break;
      
    case MENU_PAUSE:
      displayPauseMenu(line1, line2);
      break;
      // Default case not strictly needed if MenuState enum is used correctly
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

// --- Forward Declarations for Static Functions ---
// static void enterSubmenu(MenuState menu);
// static void returnToMainMenu();
// static void displayPausedStatic(char* line1, char* line2);
// static void displayMainMenuStatic(char* line1, char* line2);
// static void displaySpeedMenuStatic(char* line1, char* line2);
// static void displayLfoMenuStatic(char* line1, char* line2);
// static void displayRatioMenuStatic(char* line1, char* line2);
// static void displayMasterMenuStatic(char* line1, char* line2);
// static void displayMicrostepMenuStatic(char* line1, char* line2);
// static void displayResetMenuStatic(char* line1, char* line2);
// static void applyRatioPresetInternal(byte presetIndex);
// static void resetToDefaultsInternal();

// Handle menu navigation based on encoder movement
void handleMenuNavigation(int change) {
  // Allow encoder operation in the main menu and pause menu even when paused
  if (systemPaused && currentMenu != MENU_MAIN && currentMenu != MENU_PAUSE) return;
  
  switch (currentMenu) {
    case MENU_MAIN:
      // Cycle through main menu options
      selectedMainMenuOption = (selectedMainMenuOption + NUM_MAIN_OPTIONS + change) % NUM_MAIN_OPTIONS;
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
      
    case MENU_MICROSTEP:
      handleMicrostepMenu(change);
      break;
      
    case MENU_RESET:
      handleResetMenu(change);
      break;
      
    case MENU_PAUSE:
      handlePauseMenu(change);
      break;
  }
  
  updateDisplay();
}

// Handle short button press for menu selection
void handleMenuSelection() {
  if (systemPaused && currentMenu != MENU_MAIN && currentMenu != MENU_PAUSE) return;
  
  switch (currentMenu) {
    case MENU_MAIN:
      // Enter selected submenu
      enterSubmenu(selectedMainMenuOption + 1);  // +1 because MENU_MAIN is 0
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
      
    case MENU_MICROSTEP:
      // Toggle editing mode
      editingMicrostep = !editingMicrostep;
      break;
      
    case MENU_RESET:
      if (confirmingReset) {
        // Process confirmation choice
        if (resetChoice) {  // YES selected
          resetToDefaults(); // Call the main motor reset function
          confirmingReset = false;
          returnToMainMenu();
        } else {  // NO selected
          confirmingReset = false;
          returnToMainMenu();
        }
      }
      break;
      
    case MENU_PAUSE:
      // Process pause menu selection
      if (selectedPauseOption == 0) {  // ON selected
        systemPaused = true;
        stopAllMotors(); // Call MotorControl function
        Serial.println(F("System Paused (Menu)"));
        returnToMainMenu();
      } else if (selectedPauseOption == 1) {  // OFF selected
        systemPaused = false;
        Serial.println(F("System Resumed (Menu)"));
        returnToMainMenu();
      } else {  // EXIT selected
        returnToMainMenu();
      }
      break;
  }
  
  updateDisplay();
}

// Handle long button press for return/pause (called by InputHandling)
void handleMenuReturn() { 
  // We're moving away from using long press for navigation,
  // but keeping basic functionality for backward compatibility
  
  if (currentMenu == MENU_MAIN) {
    // Toggle pause only when in the main menu - consider removing this in the future
    // when the pause menu is fully integrated
    systemPaused = !systemPaused; 
    if (systemPaused) {
      stopAllMotors(); // Call MotorControl function
      Serial.println(F("System Paused (Long Press)")); // Add feedback
    } else {
      Serial.println(F("System Resumed (Long Press)")); // Add feedback
    }
    // Update display immediately after state change
    updateDisplay(); 
  } else {
    // For all other menus, just return to the main menu
    // This will be replaced by explicit EXIT options in the future
    returnToMainMenu();
  }
}

// Handle SPEED menu navigation
static void handleSpeedMenu(int change) {
  if (editingSpeed) {
    // REPLACE direct access with getter/setter
    float currentSpeed = getWheelSpeed(selectedSpeedWheel);
    setWheelSpeed(selectedSpeedWheel, currentSpeed + change * 0.1); 
    // Constraints are handled by the setter
  } else {
    // Cycle through wheels
    selectedSpeedWheel = (selectedSpeedWheel + MOTORS_COUNT + change) % MOTORS_COUNT;
  }
}

// Handle LFO menu navigation
static void handleLfoMenu(int change) {
  if (editingLfo) {
    byte wheelIndex = selectedLfoParam / NUM_LFO_PARAMS_PER_WHEEL;
    byte paramType = selectedLfoParam % NUM_LFO_PARAMS_PER_WHEEL;
    
    if (paramType == 0) {  // Depth (0-100%)
      // REPLACE direct access with getter/setter
      float currentDepth = getLfoDepth(wheelIndex);
      setLfoDepth(wheelIndex, currentDepth + change * 0.1);
      // Constraints are handled by the setter
    }
    else if (paramType == 1) {  // Rate (0-256.0)
      // REPLACE direct access with getter/setter
      float currentRate = getLfoRate(wheelIndex);
      setLfoRate(wheelIndex, currentRate + change * 0.1);
      // Constraints are handled by the setter
    }
    else {  // Polarity (toggle UNI/BI)
      // REPLACE direct access with getter/setter
      if (change != 0) { 
          bool currentPolarity = getLfoPolarity(wheelIndex);
          setLfoPolarity(wheelIndex, !currentPolarity);
      }
    }
  } else {
    // Cycle through LFO parameters 
    selectedLfoParam = (selectedLfoParam + NUM_LFO_PARAMS_TOTAL + change) % NUM_LFO_PARAMS_TOTAL;
  }
}

// Handle RATIO menu navigation
static void handleRatioMenu(int change) {
  if (confirmingRatio) {
    // Toggle YES/NO choice
    if (change != 0) ratioChoice = !ratioChoice;
  } else {
    // Cycle through ratio presets
    selectedRatioPreset = (selectedRatioPreset + NUM_RATIO_PRESETS + change) % NUM_RATIO_PRESETS;
  }
}

// Handle MASTER menu navigation
static void handleMasterMenu(int change) {
  if (editingMaster) {
    // REPLACE direct access with getter/setter
    float currentTime = getMasterTime();
    setMasterTime(currentTime + change * 0.01);
    // Constraints are handled by the setter
  }
  // No cycling needed if not editing
}

// Handle MICROSTEP menu navigation
static void handleMicrostepMenu(int change) {
  if (editingMicrostep) {
    // Adjust the index based on encoder change (this part is fine)
    if (change > 0) {
      currentMicrostepIndex = (currentMicrostepIndex + 1) % NUM_VALID_MICROSTEPS;
    } else if (change < 0) {
      currentMicrostepIndex = (currentMicrostepIndex + NUM_VALID_MICROSTEPS - 1) % NUM_VALID_MICROSTEPS;
    }
    
    // Update the PENDING microstepping mode from the index
    // REMOVE direct write to currentMicrostepMode
    if (change != 0) { // Only update pending mode if index actually changed
       pendingMicrostepMode = validMicrosteps[currentMicrostepIndex];
    }
  }
   // No cycling needed if not editing
}

// Handle RESET menu navigation
static void handleResetMenu(int change) {
  if (confirmingReset) {
    // Toggle YES/NO choice
    if (change != 0) resetChoice = !resetChoice;
  }
}

// Handle PAUSE menu navigation
static void handlePauseMenu(int change) {
  // Cycle through the pause options: ON, OFF, EXIT
  selectedPauseOption = (selectedPauseOption + 3 + change) % 3;
}

/**
 * Display the pause menu screen
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displayPauseMenu(char* line1, char* line2) {
  strcpy(line1, "PAUSE SYSTEM:");
  
  // Show the current selection with a cursor
  if (selectedPauseOption == 0) {
    strcpy(line2, ">ON  OFF  EXIT");
  } else if (selectedPauseOption == 1) {
    strcpy(line2, " ON >OFF  EXIT");
  } else { // selectedPauseOption == 2
    strcpy(line2, " ON  OFF >EXIT");
  }
}

// --- Getter for Pause State ---
bool getSystemPaused() {
    return systemPaused;
}

// --- Setter for Pause State ---
void setSystemPaused(bool pause) {
    if (systemPaused != pause) { // Only act on change
        systemPaused = pause;
        if (systemPaused) {
            stopAllMotors(); // Ensure motors stop if paused externally
            Serial.println(F("System Pause Set Externally"));
        } else {
             Serial.println(F("System Resume Set Externally"));
        }
        updateDisplay(); // Update display to reflect the change
    }
}

// --- Display Helper Functions ---

/**
 * Display the system paused screen
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displayPaused(char* line1, char* line2) {
  strcpy(line1, "** SYSTEM **");
  strcpy(line2, "*** PAUSED ***");
}

/**
 * Display the main menu screen with a sliding window of options
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displayMainMenu(char* line1, char* line2) {
  // Simple sliding window display for main menu
  const char* options[] = {"SPEED", "LFO", "RATIO", "MASTER", "STEP", "RESET", "PAUSE"};
  byte prev = (selectedMainMenuOption + NUM_MAIN_OPTIONS - 1) % NUM_MAIN_OPTIONS;
  byte next = (selectedMainMenuOption + 1) % NUM_MAIN_OPTIONS;
  
  // Add a "P" prefix in line1 to indicate if the system is paused
  if (systemPaused) {
    sprintf(line1, "P>%s", options[selectedMainMenuOption]);
  } else {
    sprintf(line1, ">%s", options[selectedMainMenuOption]);
  }
  
  sprintf(line2, " %s %s", options[prev], options[next]); // Show previous and next options
}

/**
 * Display the speed menu screen for the selected wheel
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displaySpeedMenu(char* line1, char* line2) {
  if (editingSpeed) {
    sprintf(line1, "SPEED: %s#", wheelLabels[selectedSpeedWheel]);
  } else {
    sprintf(line1, "SPEED: %s", wheelLabels[selectedSpeedWheel]);
  }
  // Use getter instead of direct access
  sprintf(line2, "Value: %05.1f", getWheelSpeed(selectedSpeedWheel));
}

/**
 * Display the LFO menu screen for the selected parameter
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displayLfoMenu(char* line1, char* line2) {
  byte wheelIndex = selectedLfoParam / NUM_LFO_PARAMS_PER_WHEEL;
  byte paramType = selectedLfoParam % NUM_LFO_PARAMS_PER_WHEEL;
  const char* paramName = "";
  
  switch(paramType) {
    case 0: // Depth
      paramName = "DPT";
      if (editingLfo) {
        sprintf(line1, "LFO: %s %s#", wheelLabels[wheelIndex], paramName);
      } else {
        sprintf(line1, "LFO: %s %s", wheelLabels[wheelIndex], paramName);
      }
      // Use getter instead of direct access
      sprintf(line2, "Value: %05.1f%%", getLfoDepth(wheelIndex));
      break;
      
    case 1: // Rate
      paramName = "RTE";
      if (editingLfo) {
        sprintf(line1, "LFO: %s %s#", wheelLabels[wheelIndex], paramName);
      } else {
        sprintf(line1, "LFO: %s %s", wheelLabels[wheelIndex], paramName);
      }
      // Use getter instead of direct access
      sprintf(line2, "Value: %05.1f", getLfoRate(wheelIndex));
      break;
      
    case 2: // Polarity
      paramName = "POL";
      if (editingLfo) {
        sprintf(line1, "LFO: %s %s#", wheelLabels[wheelIndex], paramName);
      } else {
        sprintf(line1, "LFO: %s %s", wheelLabels[wheelIndex], paramName);
      }
      // Use getter instead of direct access
      sprintf(line2, "Value: %s", getLfoPolarity(wheelIndex) ? "BI" : "UNI");
      break;
  }
}

/**
 * Display the ratio preset selection screen
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displayRatioMenu(char* line1, char* line2) {
  if (confirmingRatio) {
    strcpy(line1, "Apply Preset?");
    
    char buffer[LCD_COLS + 1];
    // Show the ratios from the preset using Config.h
    // Format for display: "P1: 1.0:1.0:1.0:1.0"
    sprintf(buffer, "P%d:", selectedRatioPreset + 1);
    
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      char ratioStr[6]; // Buffer for ratio display
      dtostrf(RATIO_PRESETS[selectedRatioPreset][i], 3, 1, ratioStr);
      
      if (i < MOTORS_COUNT - 1) {
        strcat(buffer, ratioStr);
        strcat(buffer, ":");
      } else {
        strcat(buffer, ratioStr);
      }
    }
    
    strcpy(line2, buffer);
  } else {
    strcpy(line1, "Select Ratio");
    
    char buffer[LCD_COLS + 1];
    sprintf(buffer, "Preset %d", selectedRatioPreset + 1);
    strcpy(line2, buffer);
  }
}

/**
 * Display the master time adjustment screen
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displayMasterMenu(char* line1, char* line2) {
  if (editingMaster) {
    strcpy(line1, "MASTER TIME:#");
  } else {
    strcpy(line1, "MASTER TIME:");
  }
  // Use getter instead of direct access
  sprintf(line2, "Value: %06.2f S", getMasterTime());
}

/**
 * Display the microstepping mode selection screen
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displayMicrostepMenu(char* line1, char* line2) {
  if (editingMicrostep) {
    strcpy(line1, "MICROSTEP:#");
    // When editing, show the pending value that hasn't been applied yet
    sprintf(line2, "Value: %dx", pendingMicrostepMode);
  } else {
    strcpy(line1, "MICROSTEP:");
    // When not editing, show the current actual value using the getter
    sprintf(line2, "Value: %dx", getCurrentMicrostepMode());
  }
}

/**
 * Display the reset confirmation screen
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displayResetMenu(char* line1, char* line2) {
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
}

/**
 * Apply a ratio preset to all motors
 * @param presetIndex The index of the preset to apply (0-based)
 */
static void applyRatioPreset(byte presetIndex) {
  if (presetIndex < NUM_RATIO_PRESETS) {
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      // Use the centralized ratio presets from Config.h
      setWheelSpeed(i, RATIO_PRESETS[presetIndex][i]);
    }
    Serial.print(F("Applied ratio preset "));
    Serial.println(presetIndex + 1);
  }
}

/**
 * Reset all settings to their default values
 */
static void resetMenuStateToDefaults() {
    Serial.println(F("Menu: Resetting menu state to defaults..."));
    // Reset motor control settings first
    // resetToDefaults(); // REMOVED Recursive Call - Motor reset is handled elsewhere (e.g., Serial command)
    
    // Reset menu state variables
    currentMenu = MENU_MAIN;
    selectedMainMenuOption = 0;
    selectedSpeedWheel = 0;
    selectedLfoParam = 0;
    selectedRatioPreset = 0;
    selectedMicrostepIndex = 4; // Default index for 16x
    pendingMicrostepMode = DEFAULT_MICROSTEP;
    editingSpeed = false;
    editingLfo = false;
    editingMaster = false;
    editingMicrostep = false;
    confirmingRatio = false;
    confirmingReset = false;
    systemPaused = false; // Ensure system is not paused after reset
}

/**
 * Enter a submenu and initialize its state
 * @param menu The menu to enter
 */
static void enterSubmenu(MenuState menu) {
  currentMenu = menu;
  
  // Initialize submenu state (Example - adjust based on actual needs)
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
    case MENU_MICROSTEP:
      editingMicrostep = false;
      break;
    case MENU_RESET:
      confirmingReset = true;  // Start with confirmation dialog
      resetChoice = false;     // Default to NO
      break;
    case MENU_PAUSE:
      // Initialize pause menu state - default to current state
      selectedPauseOption = systemPaused ? 0 : 1; // Select ON if paused, OFF if not
      break;
    default: // Handle MENU_MAIN or unexpected cases
        break; 
  }
  
  updateDisplay();
}

// Return to main menu (helper function)
static void returnToMainMenu() {
  currentMenu = MENU_MAIN;
  // Reset all editing states
  editingSpeed = false;
  editingLfo = false;
  editingMaster = false;
  editingMicrostep = false;
  confirmingRatio = false;
  confirmingReset = false;
  resetChoice = false;
  ratioChoice = false;
  // Do NOT toggle pause state when returning to main menu
  updateDisplay();
} 