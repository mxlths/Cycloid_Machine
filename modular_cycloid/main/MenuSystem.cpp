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

// Add a throttling variable for LCD updates
static unsigned long lastDisplayUpdateTime = 0;
const unsigned long MIN_DISPLAY_UPDATE_INTERVAL = 100; // Minimum 100ms between display updates

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

// Update the LCD display based on current menu and state - now with throttling
void updateDisplay() {
  // Check if enough time has passed since the last update
  unsigned long currentMillis = millis();
  if (currentMillis - lastDisplayUpdateTime < MIN_DISPLAY_UPDATE_INTERVAL) {
    return; // Skip this update to avoid too frequent refreshes
  }
  lastDisplayUpdateTime = currentMillis;
  
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
  // We'll allow encoder input in all menus, regardless of pause state
  // This makes the menu system more responsive and intuitive
  
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
  // Allow button operations in all menus, regardless of pause state
  // This makes the menu system more responsive and intuitive
  
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
        // Go to confirmation screen
        confirmingRatio = true;
        ratioChoice = false;  // Default to NO
      } else {
        if (ratioChoice) {  // YES selected
          applyRatioPreset(selectedRatioPreset);
          confirmingRatio = false;
        } else {
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
      if (editingMicrostep) {
        // If we're exiting edit mode, apply the pending change
        if (updateMicrostepMode(pendingMicrostepMode)) {
          // Keep this message as it's important user feedback
          Serial.print(F("Microstepping updated to "));
          Serial.print(pendingMicrostepMode);
          Serial.println(F("x"));
        } else {
          // Keep error message
          Serial.println(F("Microstepping update failed!"));
          // Revert the pending value to the current value
          pendingMicrostepMode = getCurrentMicrostepMode();
          // Update index to match
          for (byte i = 0; i < NUM_VALID_MICROSTEPS; i++) {
            if (validMicrosteps[i] == pendingMicrostepMode) {
              currentMicrostepIndex = i;
              break;
            }
          }
        }
        editingMicrostep = false;
      } else {
        // Entering edit mode - ensure the pending value matches the current value
        pendingMicrostepMode = getCurrentMicrostepMode();
        // Find the corresponding index
        for (byte i = 0; i < NUM_VALID_MICROSTEPS; i++) {
          if (validMicrosteps[i] == pendingMicrostepMode) {
            currentMicrostepIndex = i;
            break;
          }
        }
        editingMicrostep = true;
      }
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
        Serial.println(F("System Paused (Menu)")); // Keep this as it's user feedback
        returnToMainMenu();
      } else if (selectedPauseOption == 1) {  // OFF selected
        systemPaused = false;
        Serial.println(F("System Resumed (Menu)")); // Keep this as it's user feedback
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
  // We're completely removing the pause toggling functionality from long press
  // since we now have a dedicated PAUSE menu
  
  if (currentMenu == MENU_MAIN) {
    // No longer toggle pause on long press in main menu
    // Just provide feedback that this behavior is deprecated
    Serial.println(F("Long press in main menu: Use PAUSE menu instead"));
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
    // Get current value, modify it, and set it back
    float currentSpeed = getWheelSpeed(selectedSpeedWheel);
    
    // Calculate step size based on change magnitude
    float stepSize = 0.1;
    if (abs(change) > 1) {
      // Use a more aggressive non-linear scaling for larger changes
      stepSize = 0.1 * pow(abs(change), 0.7); // More aggressive than sqrt (which is pow(x, 0.5))
    }
    
    // Apply the change with appropriate step size
    float newSpeed = currentSpeed + (change > 0 ? stepSize : -stepSize);
    setWheelSpeed(selectedSpeedWheel, newSpeed);
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
    
    // Make sure we're in valid range
    if (wheelIndex >= MOTORS_COUNT) {
      wheelIndex = 0;
      selectedLfoParam = 0;
      paramType = 0;
    }
    
    if (paramType == 0) {  // Depth (0-100%)
      float currentDepth = getLfoDepth(wheelIndex);
      
      // Calculate step size based on change magnitude
      float stepSize = 0.1;
      if (abs(change) > 1) {
        // Use a more aggressive scaling for larger changes
        stepSize = 0.1 * pow(abs(change), 0.7);
        
        // For larger values, make bigger steps
        if (currentDepth > 50) {
          stepSize *= 1.5; // Faster adjustment for higher values
        }
      }
      
      // Apply the change with appropriate step size
      float newDepth = currentDepth + (change > 0 ? stepSize : -stepSize);
      setLfoDepth(wheelIndex, newDepth);
    }
    else if (paramType == 1) {  // Rate (0-10.0)
      float currentRate = getLfoRate(wheelIndex);
      
      // Calculate step size based on change magnitude
      float stepSize = 0.1;
      if (abs(change) > 1) {
        // Use a more aggressive scaling for larger changes
        stepSize = 0.1 * pow(abs(change), 0.7);
        
        // For larger values, make bigger steps
        if (currentRate > 5) {
          stepSize *= 1.5; // Faster adjustment for higher values
        }
      }
      
      // Apply the change with appropriate step size
      float newRate = currentRate + (change > 0 ? stepSize : -stepSize);
      setLfoRate(wheelIndex, newRate);
    }
    else if (paramType == 2) {  // Polarity (toggle UNI/BI)
      if (change != 0) { 
        bool currentPolarity = getLfoPolarity(wheelIndex);
        bool newPolarity = !currentPolarity;
        setLfoPolarity(wheelIndex, newPolarity);
      }
    }
  } else {
    // Cycle through LFO parameters, ensuring we stay within valid range
    int maxParams = MOTORS_COUNT * NUM_LFO_PARAMS_PER_WHEEL;
    
    // Calculate new parameter value with wrapping
    int newParam = selectedLfoParam + change;
    
    // Apply modulp operation with correct handling of negative numbers
    newParam = ((newParam % maxParams) + maxParams) % maxParams;
    selectedLfoParam = (byte)newParam;
    
    // Verify we're in valid range
    byte wheelIndex = selectedLfoParam / NUM_LFO_PARAMS_PER_WHEEL;
    byte paramType = selectedLfoParam % NUM_LFO_PARAMS_PER_WHEEL;
    
    if (wheelIndex >= MOTORS_COUNT) {
      selectedLfoParam = 0;
      wheelIndex = 0;
      paramType = 0;
    }
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
    float currentTime = getMasterTime();
    
    // Calculate step size based on change magnitude and current value
    float stepSize = 10.0; // Base step size in ms
    if (abs(change) > 1) {
      // More aggressive scaling for larger changes
      stepSize = 10.0 * pow(abs(change), 0.8);
      
      // For larger values, make even bigger steps
      if (currentTime > 1000) {
        stepSize *= 3.0; // Increased from 2.0 for faster adjustment
      }
    }
    
    // Apply the change with appropriate step size
    float newTime = currentTime + (change > 0 ? stepSize : -stepSize);
    setMasterTime(newTime);
  }
  // No cycling needed if not editing
}

// Handle MICROSTEP menu navigation
static void handleMicrostepMenu(int change) {
  if (editingMicrostep) {
    // Only process change if it's non-zero
    if (change != 0) {
      // Adjust the index based on encoder change
      if (change > 0) {
        currentMicrostepIndex = (currentMicrostepIndex + 1) % NUM_VALID_MICROSTEPS;
      } else if (change < 0) {
        currentMicrostepIndex = (currentMicrostepIndex + NUM_VALID_MICROSTEPS - 1) % NUM_VALID_MICROSTEPS;
      }
      
      // Update the PENDING microstepping mode from the index
      pendingMicrostepMode = validMicrosteps[currentMicrostepIndex];
      
      // Remove debug output
      // Serial.print(F("Selected microstep mode: "));
      // Serial.println(pendingMicrostepMode);
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
  float speed = getWheelSpeed(selectedSpeedWheel);
  char speedStr[7]; // Buffer for speed display
  dtostrf(speed, 5, 1, speedStr); // Convert float to string with 1 decimal place
  sprintf(line2, "Value: %s", speedStr);
}

/**
 * Display the LFO menu screen for the selected parameter
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displayLfoMenu(char* line1, char* line2) {
  // Calculate wheel index and parameter type
  byte wheelIndex = selectedLfoParam / NUM_LFO_PARAMS_PER_WHEEL;
  byte paramType = selectedLfoParam % NUM_LFO_PARAMS_PER_WHEEL;
  
  // Bounds check to prevent display issues
  if (wheelIndex >= MOTORS_COUNT) {
    wheelIndex = 0;
    selectedLfoParam = 0;
  }
  
  // Make sure we have valid parameter values
  const char* paramNames[] = {"DPT", "RTE", "POL"};
  const char* paramName = (paramType < 3) ? paramNames[paramType] : "ERR";
  
  // Clear buffers first to prevent garbage
  memset(line1, 0, LCD_COLS + 1);
  memset(line2, 0, LCD_COLS + 1);
  
  // Format the first line
  if (editingLfo) {
    snprintf(line1, LCD_COLS + 1, "LFO: %s %s#", wheelLabels[wheelIndex], paramName);
  } else {
    snprintf(line1, LCD_COLS + 1, "LFO: %s %s", wheelLabels[wheelIndex], paramName);
  }
  
  // Format the second line based on parameter type
  switch(paramType) {
    case 0: // Depth
      {
        float depth = getLfoDepth(wheelIndex);
        char depthStr[7]; // Buffer for depth display
        dtostrf(depth, 5, 1, depthStr); // Convert float to string with 1 decimal place
        snprintf(line2, LCD_COLS + 1, "Value: %s%%", depthStr);
      }
      break;
      
    case 1: // Rate
      {
        float rate = getLfoRate(wheelIndex);
        char rateStr[7]; // Buffer for rate display
        dtostrf(rate, 5, 1, rateStr); // Convert float to string with 1 decimal place
        snprintf(line2, LCD_COLS + 1, "Value: %s", rateStr);
      }
      break;
      
    case 2: // Polarity
      snprintf(line2, LCD_COLS + 1, "Value: %s", getLfoPolarity(wheelIndex) ? "BI" : "UNI");
      break;
      
    default:
      strcpy(line2, "Value: ERROR");
      break;
  }
  
  // Ensure null termination
  line1[LCD_COLS] = '\0';
  line2[LCD_COLS] = '\0';
}

/**
 * Display the ratio preset selection screen
 * @param line1 Buffer for the first line of display
 * @param line2 Buffer for the second line of display
 */
static void displayRatioMenu(char* line1, char* line2) {
  if (confirmingRatio) {
    strcpy(line1, "Apply Preset?");
    
    // Show YES/NO options with cursor
    if (ratioChoice) {
      strcpy(line2, " NO   >YES");
    } else {
      strcpy(line2, ">NO    YES");
    }
  } else {
    // Show the preset number in first line
    char buffer[LCD_COLS + 1];
    sprintf(buffer, "Preset %d", selectedRatioPreset + 1);
    strcpy(line1, buffer);
    
    // Show a preview of the ratios in the second line
    char ratioBuffer[LCD_COLS + 1] = "";
    
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      char ratioStr[5]; // Buffer for ratio display (smaller to fit)
      dtostrf(RATIO_PRESETS[selectedRatioPreset][i], 3, 1, ratioStr);
      
      // Add to buffer (with separator if not last)
      strcat(ratioBuffer, ratioStr);
      if (i < MOTORS_COUNT - 1) {
        strcat(ratioBuffer, ":");
      }
    }
    
    strcpy(line2, ratioBuffer);
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
  float time = getMasterTime();
  char timeStr[7]; // Buffer for time display
  dtostrf(time/1000.0, 5, 2, timeStr); // Convert ms to seconds with 2 decimal places
  sprintf(line2, "Value: %s S", timeStr);
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
    // Keep this message as it's important user feedback
    Serial.print(F("Applied ratio preset "));
    Serial.println(presetIndex + 1);
  }
}

/**
 * Reset all settings to their default values
 */
static void resetMenuStateToDefaults() {
    // Keep this as it's important for diagnostics
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