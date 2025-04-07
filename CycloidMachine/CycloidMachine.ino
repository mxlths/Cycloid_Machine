/**
 * Cycloid Machine - Arduino Program
 * Based on design document specifications
 * 
 * A 4-wheel stepper motor system designed to generate cycloidal patterns
 * using mechanical linkages controlled through an LCD interface.
 */

// Required Libraries
#include <Wire.h>              // Core I2C communication
#include <LiquidCrystal_I2C.h> // I2C LCD interface
#include <AccelStepper.h>      // Advanced stepper control

// ===== PIN DEFINITIONS =====
// Arduino Pin Definitions for CNC Shield
#define X_STEP_PIN 2   // X axis step signal
#define X_DIR_PIN 5    // X axis direction
#define Y_STEP_PIN 3   // Y axis step signal
#define Y_DIR_PIN 6    // Y axis direction
#define Z_STEP_PIN 4   // Z axis step signal
#define Z_DIR_PIN 7    // Z axis direction
#define A_STEP_PIN 12  // A axis step signal
#define A_DIR_PIN 13   // A axis direction
#define ENABLE_PIN 8   // Motor drivers enable (active LOW)

// Rotary Encoder Pin Definitions (via CNC Shield limit switch pins)
#define ENC_A_PIN 9    // CLK signal (connect to X-LIMIT on CNC Shield)
#define ENC_B_PIN 10   // DT signal (connect to Y-LIMIT on CNC Shield)
#define ENC_BTN_PIN 11 // SW push button (connect to Z-LIMIT on CNC Shield)

// I2C LCD Address
#define LCD_I2C_ADDR 0x27 // Default address, may need to change to 0x3F

// ===== SYSTEM CONSTANTS =====
#define MOTORS_COUNT 4
#define LCD_COLS 16
#define LCD_ROWS 2

// Microstepping configuration
#define MICROSTEP_FULL 1       // Full step mode (default)
#define MICROSTEP_HALF 2       // Half step mode
#define MICROSTEP_QUARTER 4    // Quarter step mode
#define MICROSTEP_EIGHTH 8     // Eighth step mode
#define MICROSTEP_SIXTEENTH 16 // Sixteenth step mode
#define MICROSTEP_32 32        // 32 microsteps (TMC2208 only)
#define MICROSTEP_64 64        // 64 microsteps (TMC2208 only)
#define MICROSTEP_128 128      // 128 microsteps (TMC2208 only)

// Motor Configuration
#define STEPS_PER_MOTOR_REV 200 // 1.8° stepper motors
#define GEAR_RATIO 3            // 1:3 gear reduction
#define STEPS_PER_WHEEL_REV (STEPS_PER_MOTOR_REV * GEAR_RATIO) // 600 steps

// Communication Settings
#define SERIAL_BAUD_RATE 9600

// Menu Navigation Constants
#define MENU_MAIN 0
#define MENU_SPEED 1
#define MENU_LFO 2
#define MENU_RATIO 3
#define MENU_MASTER 4
#define MENU_MICROSTEP 5
#define MENU_RESET 6

// Button Timing Constants
#define DEBOUNCE_TIME 50    // ms
#define LONG_PRESS_TIME 1000 // ms

// Motor Control Constants
#define MOTOR_UPDATE_INTERVAL 5 // ms

// LFO Control Constants
#define LFO_RESOLUTION 1000 // Phase resolution for smoother LFO

// ===== OBJECT INITIALIZATION =====
// LCD Display
LiquidCrystal_I2C lcd(LCD_I2C_ADDR, LCD_COLS, LCD_ROWS);

// Stepper Motors (AccelStepper driver interface type = 1)
AccelStepper motorX(1, X_STEP_PIN, X_DIR_PIN);
AccelStepper motorY(1, Y_STEP_PIN, Y_DIR_PIN);
AccelStepper motorZ(1, Z_STEP_PIN, Z_DIR_PIN);
AccelStepper motorA(1, A_STEP_PIN, A_DIR_PIN);
AccelStepper motors[MOTORS_COUNT] = {motorX, motorY, motorZ, motorA};

// ===== SYSTEM VARIABLES =====
// Microstepping Variables
byte currentMicrostepMode = MICROSTEP_FULL; // Default to full step mode
bool editingMicrostep = false;              // Flag for editing mode
const byte validMicrosteps[] = {1, 2, 4, 8, 16, 32, 64, 128};
const byte microstepCount = 8;
byte currentMicrostepIndex = 0; // Index in validMicrosteps array

// Menu State Variables
byte currentMenu = MENU_MAIN; // Current active menu
byte selectedOption = 0;      // Selected option in current menu
bool systemPaused = false;    // System pause state

// Speed Control Variables
float wheelSpeeds[MOTORS_COUNT] = {10.0, 10.0, 10.0, 10.0}; // Default 10.0
byte selectedSpeedWheel = 0;  // Currently selected wheel
bool editingSpeed = false;    // Flag for editing mode

// LFO Control Variables
float lfoDepths[MOTORS_COUNT] = {0.0, 0.0, 0.0, 0.0};       // Default 0.0%
float lfoRates[MOTORS_COUNT] = {0.0, 0.0, 0.0, 0.0};        // Default 0.0
bool lfoPolarities[MOTORS_COUNT] = {false, false, false, false}; // false=UNI, true=BI
byte selectedLfoParam = 0;    // 0-11: 4 wheels × 3 params
bool editingLfo = false;      // Flag for editing mode

// LFO State Variables
unsigned long lfoPhases[MOTORS_COUNT] = {0, 0, 0, 0}; // Current phase of each LFO

// Ratio Preset Values
const float ratioPresets[4][MOTORS_COUNT] = {
  {100.0, 100.0, 100.0, 100.0}, // Equal (Preset 1)
  {50.0, 100.0, 150.0, 200.0},  // Increasing (Preset 2)
  {200.0, 150.0, 100.0, 50.0},  // Decreasing (Preset 3)
  {75.0, 125.0, 175.0, 225.0}   // Custom (Preset 4)
};

// Ratio Control Variables
byte selectedRatioPreset = 0;  // Currently selected preset (0-3)
bool confirmingRatio = false;  // Flag for confirmation dialog
bool ratioChoice = false;      // false=NO, true=YES

// Master Time Variables
float masterTime = 1.00;       // Default 1.00 second
bool editingMaster = false;    // Flag for edit mode

// Reset Control Variables
bool confirmingReset = false;  // Flag for confirmation dialog
bool resetChoice = false;      // false=NO, true=YES

// Timing Variables
unsigned long currentMillis = 0;
unsigned long previousMotorMillis = 0;
unsigned long previousLfoMillis = 0;
unsigned long buttonPressTime = 0;
unsigned long buttonReleaseTime = 0;
bool buttonPressed = false;
bool buttonLongPressed = false;

// Encoder Variables
volatile int encoderPos = 0;
volatile int lastEncoded = 0;
int lastEncoderPos = 0;

// Function prototypes
void updateEncoderPosition();
void handleEncoderChange(int change);
void checkButtonPress();
void handleShortPress();
void handleLongPress();
void updateDisplay();
void updateMotorSpeeds();
float calculateLfoModulation(byte motorIndex);
void applyRatioPreset(byte presetIndex);
void resetToDefaults();
void processSerialCommands();
void parseAndExecuteCommand(char* cmd);
void showHelp();
void showStatus();
bool updateMicrostepMode(byte newMode);
unsigned long getStepsPerWheelRev();

// ===== SETUP FUNCTION =====
void setup() {
  // Initialize serial communication
  Serial.begin(SERIAL_BAUD_RATE);
  Serial.println(F("Cycloid Machine - Starting up..."));
  
  // Initialize I2C LCD
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(F("Cycloid Machine"));
  lcd.setCursor(0, 1);
  lcd.print(F("Initializing..."));
  delay(1000);
  
  // Configure encoder pins with pull-up resistors
  pinMode(ENC_A_PIN, INPUT_PULLUP);
  pinMode(ENC_B_PIN, INPUT_PULLUP);
  pinMode(ENC_BTN_PIN, INPUT_PULLUP);
  
  // Attach encoder interrupts for smooth operation
  attachInterrupt(digitalPinToInterrupt(ENC_A_PIN), updateEncoderPosition, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_B_PIN), updateEncoderPosition, CHANGE);
  
  // Initialize stepper motors and set parameters
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    motors[i].setMaxSpeed(2000);    // Max steps per second
    motors[i].setAcceleration(500); // Steps per second per second
  }
  
  // Enable motor drivers (active LOW)
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW);
  
  // Display initial menu
  updateDisplay();
  
  Serial.println(F("Initialization complete"));
}

// ===== MAIN LOOP =====
void loop() {
  currentMillis = millis();
  
  // Check for encoder button presses
  checkButtonPress();
  
  // Process any changes to encoder position
  if (encoderPos != lastEncoderPos) {
    int change = encoderPos - lastEncoderPos;
    handleEncoderChange(change);
    lastEncoderPos = encoderPos;
  }
  
  // Update motor speeds if not paused (every MOTOR_UPDATE_INTERVAL ms)
  if (!systemPaused && (currentMillis - previousMotorMillis >= MOTOR_UPDATE_INTERVAL)) {
    previousMotorMillis = currentMillis;
    updateMotorSpeeds();
  }
  
  // Update LFO phases (every ms for smoother modulation)
  if (currentMillis - previousLfoMillis >= 1) {
    previousLfoMillis = currentMillis;
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      if (lfoRates[i] > 0) {
        // Update phase based on LFO rate
        float phaseIncrement = (1.0 / 1000.0) * (1.0 / (masterTime * lfoRates[i])) * LFO_RESOLUTION;
        lfoPhases[i] = (lfoPhases[i] + (unsigned long)phaseIncrement) % LFO_RESOLUTION;
      }
    }
  }
  
  // Check for and process serial commands
  if (Serial.available() > 0) {
    processSerialCommands();
  }
  
  // Run the motors
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    motors[i].run();
  }
}

// ===== ENCODER AND BUTTON HANDLING =====
void updateEncoderPosition() {
  int MSB = digitalRead(ENC_A_PIN);
  int LSB = digitalRead(ENC_B_PIN);
  
  int encoded = (MSB << 1) | LSB;
  int sum = (lastEncoded << 2) | encoded;
  
  if (sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011) {
    encoderPos++;
  } else if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000) {
    encoderPos--;
  }
  
  lastEncoded = encoded;
}

void handleEncoderChange(int change) {
  switch (currentMenu) {
    case MENU_MAIN:
      // In main menu, cycle through options (0-5)
      selectedOption = (selectedOption + change + 6) % 6;
      break;
      
    case MENU_SPEED:
      if (editingSpeed) {
        // Editing speed value
        wheelSpeeds[selectedSpeedWheel] += change * 0.1;
        // Constrain speed values
        if (wheelSpeeds[selectedSpeedWheel] < 0.1) wheelSpeeds[selectedSpeedWheel] = 0.1;
        if (wheelSpeeds[selectedSpeedWheel] > 256.0) wheelSpeeds[selectedSpeedWheel] = 256.0;
      } else {
        // Selecting wheel (0-3: X, Y, Z, A)
        selectedSpeedWheel = (selectedSpeedWheel + change + 4) % 4;
      }
      break;
      
    case MENU_LFO:
      if (editingLfo) {
        // Editing LFO value
        byte wheelIndex = selectedLfoParam / 3;
        byte paramType = selectedLfoParam % 3;
        
        if (paramType == 0) {
          // Depth adjustment (0.0 - 100.0%)
          lfoDepths[wheelIndex] += change * 1.0;
          if (lfoDepths[wheelIndex] < 0.0) lfoDepths[wheelIndex] = 0.0;
          if (lfoDepths[wheelIndex] > 100.0) lfoDepths[wheelIndex] = 100.0;
        } else if (paramType == 1) {
          // Rate adjustment (0.0 - 256.0)
          lfoRates[wheelIndex] += change * 0.1;
          if (lfoRates[wheelIndex] < 0.0) lfoRates[wheelIndex] = 0.0;
          if (lfoRates[wheelIndex] > 256.0) lfoRates[wheelIndex] = 256.0;
        } else if (paramType == 2) {
          // Polarity toggle (UNI/BI)
          if (change != 0) {
            lfoPolarities[wheelIndex] = !lfoPolarities[wheelIndex];
          }
        }
      } else {
        // Selecting LFO parameter (0-11)
        selectedLfoParam = (selectedLfoParam + change + 12) % 12;
      }
      break;
      
    case MENU_RATIO:
      if (confirmingRatio) {
        // Toggle between NO/YES
        if (change != 0) {
          ratioChoice = !ratioChoice;
        }
      } else {
        // Cycle through presets (0-3)
        selectedRatioPreset = (selectedRatioPreset + change + 4) % 4;
      }
      break;
      
    case MENU_MASTER:
      if (editingMaster) {
        // Adjust master time (0.01 - 999.99)
        masterTime += change * 0.01;
        if (masterTime < 0.01) masterTime = 0.01;
        if (masterTime > 999.99) masterTime = 999.99;
      }
      break;
      
    case MENU_MICROSTEP:
      if (editingMicrostep) {
        // Find current index in the validMicrosteps array
        for (byte i = 0; i < microstepCount; i++) {
          if (validMicrosteps[i] == currentMicrostepMode) {
            currentMicrostepIndex = i;
            break;
          }
        }
        
        // Adjust the index based on encoder change
        if (change > 0) {
          currentMicrostepIndex = (currentMicrostepIndex + 1) % microstepCount;
        } else if (change < 0) {
          currentMicrostepIndex = (currentMicrostepIndex + microstepCount - 1) % microstepCount;
        }
        
        // Update the microstepping mode from the index
        currentMicrostepMode = validMicrosteps[currentMicrostepIndex];
      }
      break;
      
    case MENU_RESET:
      // Toggle between NO/YES
      if (change != 0) {
        resetChoice = !resetChoice;
      }
      break;
  }
  
  updateDisplay();
}

void checkButtonPress() {
  // Read the button state
  bool btnState = digitalRead(ENC_BTN_PIN);
  
  // Button state change detection with debounce
  if (!btnState && !buttonPressed) {  // Button pressed (active LOW)
    if (millis() - buttonReleaseTime > DEBOUNCE_TIME) {
      buttonPressed = true;
      buttonPressTime = millis();
    }
  } else if (btnState && buttonPressed) {  // Button released
    buttonPressed = false;
    buttonReleaseTime = millis();
    
    if (buttonLongPressed) {
      buttonLongPressed = false;
    } else if (millis() - buttonPressTime >= DEBOUNCE_TIME) {
      // Short press detected
      handleShortPress();
    }
  }
  
  // Check for long press while button is held
  if (buttonPressed && !buttonLongPressed && millis() - buttonPressTime >= LONG_PRESS_TIME) {
    buttonLongPressed = true;
    handleLongPress();
  }
}

void handleShortPress() {
  switch (currentMenu) {
    case MENU_MAIN:
      // Enter selected submenu
      currentMenu = selectedOption + 1;  // +1 because MENU_MAIN is 0, options start at 1
      selectedOption = 0;
      break;
      
    case MENU_SPEED:
      // Toggle between wheel selection and speed editing
      editingSpeed = !editingSpeed;
      break;
      
    case MENU_LFO:
      // Toggle between parameter selection and value editing
      editingLfo = !editingLfo;
      break;
      
    case MENU_RATIO:
      if (confirmingRatio) {
        // Apply ratio if YES is selected
        if (ratioChoice) {
          applyRatioPreset(selectedRatioPreset);
        }
        confirmingRatio = false;
      } else {
        // Enter confirmation screen
        confirmingRatio = true;
        ratioChoice = false;  // Default to NO
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
      // Apply reset if YES is selected
      if (resetChoice) {
        resetToDefaults();
      }
      // Return to main menu
      currentMenu = MENU_MAIN;
      break;
  }
  
  updateDisplay();
}

void handleLongPress() {
  if (currentMenu == MENU_MAIN) {
    // Toggle system pause state
    systemPaused = !systemPaused;
    if (systemPaused) {
      // Stop all motors when paused
      for (byte i = 0; i < MOTORS_COUNT; i++) {
        motors[i].stop();
      }
    }
  } else if (currentMenu == MENU_MICROSTEP) {
    // Apply microstepping change on long press
    updateMicrostepMode(currentMicrostepMode);
    
    // Return to main menu
    currentMenu = MENU_MAIN;
    selectedOption = 0;
    editingMicrostep = false;
  } else {
    // Return to main menu from any submenu
    currentMenu = MENU_MAIN;
    selectedOption = 0;
    editingSpeed = false;
    editingLfo = false;
    confirmingRatio = false;
    editingMaster = false;
  }
  
  updateDisplay();
}

void updateDisplay() {
  lcd.clear();
  
  switch (currentMenu) {
    case MENU_MAIN:
      if (systemPaused) {
        // Display pause screen
        lcd.setCursor(0, 0);
        lcd.print(F("SYSTEM"));
        lcd.setCursor(0, 1);
        lcd.print(F("* PAUSED *"));
      } else {
        // Display main menu options
        const char* menuOptions[] = {"SPEED", "LFO", "RATIO", "MSTR", "MICROSTEP", "RESET"};
        lcd.setCursor(0, 0);
        lcd.print('>');
        lcd.print(menuOptions[selectedOption]);
        
        // Show other options on second line
        lcd.setCursor(0, 1);
        for (byte i = 0; i < 3; i++) {
          byte optIndex = (selectedOption + i + 1) % 6;
          lcd.print(menuOptions[optIndex]);
          lcd.print(' ');
        }
      }
      break;
      
    case MENU_SPEED:
      // Display speed menu
      const char wheelNames[] = {'X', 'Y', 'Z', 'A'};
      lcd.setCursor(0, 0);
      lcd.print(F("SPEED: "));
      lcd.print(wheelNames[selectedSpeedWheel]);
      
      // Show edit indicator if editing
      if (editingSpeed) {
        lcd.print('#');
      }
      
      // Show speed value
      lcd.setCursor(0, 1);
      lcd.print(F("Value: "));
      
      // Format with leading zeros and fixed decimal places
      if (wheelSpeeds[selectedSpeedWheel] < 10) lcd.print('0');
      if (wheelSpeeds[selectedSpeedWheel] < 100) lcd.print('0');
      lcd.print(wheelSpeeds[selectedSpeedWheel], 1);
      break;
      
    case MENU_LFO:
      // Display LFO parameters
      const char* paramNames[] = {"DPT", "RAT", "POL"};
      byte wheelIndex = selectedLfoParam / 3;
      byte paramType = selectedLfoParam % 3;
      
      // Show selected wheel and parameter
      lcd.setCursor(0, 0);
      lcd.print(F("LFO: "));
      lcd.print(wheelNames[wheelIndex]);
      lcd.print(' ');
      lcd.print(paramNames[paramType]);
      
      // Show edit indicator if editing
      if (editingLfo) {
        lcd.print('#');
      }
      
      // Show parameter value based on type
      lcd.setCursor(0, 1);
      lcd.print(F("Value: "));
      
      if (paramType == 0) {
        // Depth (0.0-100.0%)
        if (lfoDepths[wheelIndex] < 10) lcd.print('0');
        if (lfoDepths[wheelIndex] < 100) lcd.print('0');
        lcd.print(lfoDepths[wheelIndex], 1);
        lcd.print('%');
      } else if (paramType == 1) {
        // Rate (0.0-256.0)
        if (lfoRates[wheelIndex] < 10) lcd.print('0');
        if (lfoRates[wheelIndex] < 100) lcd.print('0');
        lcd.print(lfoRates[wheelIndex], 1);
      } else {
        // Polarity (UNI/BI)
        lcd.print(lfoPolarities[wheelIndex] ? F("BI") : F("UNI"));
      }
      break;
      
    case MENU_RATIO:
      if (confirmingRatio) {
        // Display confirmation screen
        lcd.setCursor(0, 0);
        lcd.print(F("APPLY RATIO?"));
        lcd.setCursor(0, 1);
        lcd.print(ratioChoice ? F(" NO >YES") : F(">NO  YES"));
      } else {
        // Display ratio preset screen
        lcd.setCursor(0, 0);
        lcd.print(F("RATIO PRESET: "));
        lcd.print(selectedRatioPreset + 1);
        
        // Display ratio values
        lcd.setCursor(0, 1);
        for (byte i = 0; i < MOTORS_COUNT; i++) {
          // Print ratio values compactly
          int ratio = (int)ratioPresets[selectedRatioPreset][i];
          lcd.print(ratio);
          if (i < MOTORS_COUNT - 1) lcd.print(':');
        }
      }
      break;
      
    case MENU_MASTER:
      // Display master time screen
      lcd.setCursor(0, 0);
      lcd.print(F("MASTER TIME:"));
      if (editingMaster) lcd.print('#');
      
      // Format with leading zeros
      lcd.setCursor(0, 1);
      lcd.print(F("Value: "));
      if (masterTime < 10) lcd.print('0');
      if (masterTime < 100) lcd.print('0');
      lcd.print(masterTime, 2);
      lcd.print(F(" S"));
      break;
      
    case MENU_MICROSTEP:
      // Display microstepping configuration
      lcd.setCursor(0, 0);
      lcd.print(F("MICROSTEP:"));
      if (editingMicrostep) lcd.print('#');
      
      lcd.setCursor(0, 1);
      lcd.print(F("Value: "));
      lcd.print(currentMicrostepMode);
      lcd.print(F("x"));
      break;
      
    case MENU_RESET:
      // Display reset confirmation screen
      lcd.setCursor(0, 0);
      lcd.print(F("RESET TO DEFLT?"));
      lcd.setCursor(0, 1);
      lcd.print(resetChoice ? F(" NO >YES") : F(">NO  YES"));
      break;
  }
}

void updateMotorSpeeds() {
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    // Get base speed
    float baseSpeed = wheelSpeeds[i];
    
    // Apply LFO modulation if depth > 0
    if (lfoDepths[i] > 0) {
      baseSpeed += calculateLfoModulation(i);
    }
    
    // Calculate steps per second, accounting for microstepping
    float stepsPerSecond = (float)getStepsPerWheelRev() / (masterTime * baseSpeed);
    
    // Ensure speed is within valid range
    if (stepsPerSecond < 0.1) stepsPerSecond = 0.1;
    if (stepsPerSecond > 2000 * currentMicrostepMode) stepsPerSecond = 2000 * currentMicrostepMode;
    
    // Update motor speed
    motors[i].setSpeed(stepsPerSecond);
  }
}

float calculateLfoModulation(byte motorIndex) {
  // Calculate sine value from current phase (0-999 maps to 0-2π)
  float phase = (2.0 * PI * lfoPhases[motorIndex]) / LFO_RESOLUTION;
  float sineValue = sin(phase);
  
  // Apply based on polarity setting
  if (lfoPolarities[motorIndex]) {
    // Bipolar modulation (-1.0 to 1.0)
    return wheelSpeeds[motorIndex] * (lfoDepths[motorIndex]/100.0) * sineValue;
  } else {
    // Unipolar modulation (0.0 to 1.0)
    float uniSine = (sineValue + 1.0) / 2.0;  // Convert -1:1 to 0:1
    // Subtract modulation to avoid negative/reverse speeds (reduced speed only)
    return -wheelSpeeds[motorIndex] * (lfoDepths[motorIndex]/100.0) * uniSine;
  }
}

void applyRatioPreset(byte presetIndex) {
  if (presetIndex < 4) {
    // Apply selected preset to wheel speeds
    for (byte i = 0; i < MOTORS_COUNT; i++) {
      wheelSpeeds[i] = ratioPresets[presetIndex][i];
    }
    
    // Return to main menu
    currentMenu = MENU_MAIN;
    confirmingRatio = false;
    
    Serial.print(F("Applied ratio preset "));
    Serial.println(presetIndex + 1);
  }
}

void resetToDefaults() {
  // Reset speed parameters
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    wheelSpeeds[i] = 10.0;
    lfoDepths[i] = 0.0;
    lfoRates[i] = 0.0;
    lfoPolarities[i] = false;
    lfoPhases[i] = 0;
  }
  
  // Reset other parameters
  masterTime = 1.00;
  currentMicrostepMode = MICROSTEP_FULL;
  updateMicrostepMode(MICROSTEP_FULL);
  
  // Reset menu state
  currentMenu = MENU_MAIN;
  selectedOption = 0;
  selectedSpeedWheel = 0;
  selectedLfoParam = 0;
  selectedRatioPreset = 0;
  currentMicrostepIndex = 0;
  
  // Reset editing states
  editingSpeed = false;
  editingLfo = false;
  confirmingRatio = false;
  editingMaster = false;
  editingMicrostep = false;
  confirmingReset = false;
  resetChoice = false;
  
  Serial.println(F("All settings reset to defaults"));
}

// ===== SERIAL COMMAND PROCESSING =====
void processSerialCommands() {
  // Buffer for storing the command
  static char cmdBuffer[64];
  static byte cmdIndex = 0;
  
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    // Store character if not end of command
    if (c != '\n' && c != '\r') {
      if (cmdIndex < 63) {
        cmdBuffer[cmdIndex++] = c;
      }
    } else if (cmdIndex > 0) {
      // Null-terminate the string
      cmdBuffer[cmdIndex] = '\0';
      
      // Process the command
      parseAndExecuteCommand(cmdBuffer);
      
      // Reset the buffer for next command
      cmdIndex = 0;
    }
  }
}

void parseAndExecuteCommand(char* cmd) {
  // Convert to uppercase for case-insensitive comparison
  for (byte i = 0; cmd[i] != '\0'; i++) {
    cmd[i] = toupper(cmd[i]);
  }
  
  // Command buffer for splitting into tokens
  char* token;
  token = strtok(cmd, " ");
  
  if (token != NULL) {
    if (strcmp(token, "HELP") == 0) {
      showHelp();
      
    } else if (strcmp(token, "STATUS") == 0) {
      showStatus();
      
    } else if (strcmp(token, "PAUSE") == 0) {
      systemPaused = true;
      for (byte i = 0; i < MOTORS_COUNT; i++) {
        motors[i].stop();
      }
      Serial.println(F("System paused"));
      
    } else if (strcmp(token, "RESUME") == 0) {
      systemPaused = false;
      Serial.println(F("System resumed"));
      
    } else if (strcmp(token, "RESET") == 0) {
      resetToDefaults();
      
    } else if (strcmp(token, "MICROSTEP") == 0) {
      // MICROSTEP value
      char* valueToken = strtok(NULL, " ");
      
      if (valueToken) {
        int value = atoi(valueToken);
        if (updateMicrostepMode(value)) {
          Serial.print(F("Set microstepping mode to "));
          Serial.print(currentMicrostepMode);
          Serial.println(F("x"));
        } else {
          Serial.println(F("Invalid microstepping mode (use 1, 2, 4, 8, 16, 32, 64, or 128)"));
        }
      } else {
        Serial.println(F("Usage: MICROSTEP value (1, 2, 4, 8, 16, 32, 64, or 128)"));
      }
    } else if (strcmp(token, "SPEED") == 0) {
      // SPEED X/Y/Z/A value
      char* wheelToken = strtok(NULL, " ");
      char* valueToken = strtok(NULL, " ");
      
      if (wheelToken && valueToken) {
        float value = atof(valueToken);
        byte wheelIndex = 0;
        
        if (wheelToken[0] == 'X') wheelIndex = 0;
        else if (wheelToken[0] == 'Y') wheelIndex = 1;
        else if (wheelToken[0] == 'Z') wheelIndex = 2;
        else if (wheelToken[0] == 'A') wheelIndex = 3;
        else {
          Serial.println(F("Invalid wheel. Use X, Y, Z, or A"));
          return;
        }
        
        if (value >= 0.1 && value <= 256.0) {
          wheelSpeeds[wheelIndex] = value;
          Serial.print(F("Set "));
          Serial.print(wheelToken[0]);
          Serial.print(F(" speed to "));
          Serial.println(value);
        } else {
          Serial.println(F("Speed must be between 0.1 and 256.0"));
        }
      } else {
        Serial.println(F("Usage: SPEED X/Y/Z/A value"));
      }
      
    } else if (strcmp(token, "LFO") == 0) {
      // LFO X/Y/Z/A DEPTH/RATE/POL value
      char* wheelToken = strtok(NULL, " ");
      char* paramToken = strtok(NULL, " ");
      char* valueToken = strtok(NULL, " ");
      
      if (wheelToken && paramToken && valueToken) {
        float value = atof(valueToken);
        byte wheelIndex = 0;
        
        if (wheelToken[0] == 'X') wheelIndex = 0;
        else if (wheelToken[0] == 'Y') wheelIndex = 1;
        else if (wheelToken[0] == 'Z') wheelIndex = 2;
        else if (wheelToken[0] == 'A') wheelIndex = 3;
        else {
          Serial.println(F("Invalid wheel. Use X, Y, Z, or A"));
          return;
        }
        
        if (strcmp(paramToken, "DEPTH") == 0) {
          if (value >= 0.0 && value <= 100.0) {
            lfoDepths[wheelIndex] = value;
            Serial.print(F("Set LFO depth for "));
            Serial.print(wheelToken[0]);
            Serial.print(F(" to "));
            Serial.print(value);
            Serial.println(F("%"));
          } else {
            Serial.println(F("Depth must be between 0.0 and 100.0"));
          }
        } else if (strcmp(paramToken, "RATE") == 0) {
          if (value >= 0.0 && value <= 256.0) {
            lfoRates[wheelIndex] = value;
            Serial.print(F("Set LFO rate for "));
            Serial.print(wheelToken[0]);
            Serial.print(F(" to "));
            Serial.println(value);
          } else {
            Serial.println(F("Rate must be between 0.0 and 256.0"));
          }
        } else if (strcmp(paramToken, "POL") == 0) {
          if (value == 0 || value == 1) {
            lfoPolarities[wheelIndex] = (value == 1);
            Serial.print(F("Set LFO polarity for "));
            Serial.print(wheelToken[0]);
            Serial.print(F(" to "));
            Serial.println(lfoPolarities[wheelIndex] ? F("BI") : F("UNI"));
          } else {
            Serial.println(F("Polarity must be 0 (UNI) or 1 (BI)"));
          }
        } else {
          Serial.println(F("Invalid parameter. Use DEPTH, RATE, or POL"));
        }
      } else {
        Serial.println(F("Usage: LFO X/Y/Z/A DEPTH/RATE/POL value"));
      }
      
    } else if (strcmp(token, "MASTER") == 0) {
      // MASTER value
      char* valueToken = strtok(NULL, " ");
      
      if (valueToken) {
        float value = atof(valueToken);
        
        if (value >= 0.01 && value <= 999.99) {
          masterTime = value;
          Serial.print(F("Set master time to "));
          Serial.print(value);
          Serial.println(F(" seconds"));
        } else {
          Serial.println(F("Master time must be between 0.01 and 999.99"));
        }
      } else {
        Serial.println(F("Usage: MASTER value"));
      }
      
    } else if (strcmp(token, "RATIO") == 0) {
      // RATIO preset number (1-4)
      char* presetToken = strtok(NULL, " ");
      
      if (presetToken) {
        int preset = atoi(presetToken);
        
        if (preset >= 1 && preset <= 4) {
          applyRatioPreset(preset - 1);
        } else {
          Serial.println(F("Preset must be between 1 and 4"));
        }
      } else {
        Serial.println(F("Usage: RATIO preset_number (1-4)"));
      }
      
    } else {
      Serial.println(F("Unknown command. Type HELP for available commands."));
    }
  }
  
  // Update display to reflect any changes
  updateDisplay();
}

void showHelp() {
  Serial.println(F("\n=== Cycloid Machine Commands ==="));
  Serial.println(F("HELP              - Display this help message"));
  Serial.println(F("STATUS            - Show current system status"));
  Serial.println(F("PAUSE             - Pause the system"));
  Serial.println(F("RESUME            - Resume the system"));
  Serial.println(F("RESET             - Reset to default values"));
  Serial.println(F("SPEED X/Y/Z/A val - Set wheel speed (0.1-256.0)"));
  Serial.println(F("LFO X/Y/Z/A DEPTH val - Set LFO depth (0.0-100.0%)"));
  Serial.println(F("LFO X/Y/Z/A RATE val  - Set LFO rate (0.0-256.0)"));
  Serial.println(F("LFO X/Y/Z/A POL val   - Set LFO polarity (0=UNI, 1=BI)"));
  Serial.println(F("MASTER val        - Set master time (0.01-999.99)"));
  Serial.println(F("RATIO val         - Apply ratio preset (1-4)"));
  Serial.println(F("MICROSTEP val     - Set microstepping mode (1, 2, 4, 8, 16, 32, 64, or 128)"));
  Serial.println(F("==============================\n"));
}

void showStatus() {
  Serial.println(F("\n=== Cycloid Machine Status ==="));
  Serial.print(F("System state: "));
  Serial.println(systemPaused ? F("PAUSED") : F("RUNNING"));
  
  Serial.print(F("Master time: "));
  Serial.print(masterTime);
  Serial.println(F(" seconds"));
  
  Serial.print(F("Microstepping: "));
  Serial.print(currentMicrostepMode);
  Serial.println(F("x"));
  
  Serial.println(F("\nWheel speeds:"));
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    char wheel = 'X' + i;
    if (i == 3) wheel = 'A';  // X, Y, Z, A
    
    Serial.print(wheel);
    Serial.print(F(": "));
    Serial.print(wheelSpeeds[i]);
    
    if (lfoDepths[i] > 0) {
      Serial.print(F(" (LFO: depth="));
      Serial.print(lfoDepths[i]);
      Serial.print(F(", rate="));
      Serial.print(lfoRates[i]);
      Serial.print(F(", polarity="));
      Serial.print(lfoPolarities[i] ? F("BI") : F("UNI"));
      Serial.print(F(")"));
    }
    
    Serial.println();
  }
  Serial.println(F("==============================\n"));
}

bool updateMicrostepMode(byte newMode) {
  // Check if the mode is valid (must be a power of 2 up to 128)
  if (newMode != 1 && newMode != 2 && newMode != 4 && newMode != 8 && 
      newMode != 16 && newMode != 32 && newMode != 64 && newMode != 128) {
    Serial.println(F("Invalid microstepping mode"));
    return false;
  }
  
  // Store the new microstepping mode
  currentMicrostepMode = newMode;
  
  // Reconfigure motor parameters for new step resolution
  for (byte i = 0; i < MOTORS_COUNT; i++) {
    float maxSpeed = 2000.0 * currentMicrostepMode;
    motors[i].setMaxSpeed(maxSpeed);
    motors[i].setAcceleration(500 * currentMicrostepMode);
  }
  
  Serial.print(F("Microstepping mode set to "));
  Serial.print(currentMicrostepMode);
  Serial.println(F("x"));
  
  return true;
}

unsigned long getStepsPerWheelRev() {
  return STEPS_PER_MOTOR_REV * GEAR_RATIO * currentMicrostepMode;
} 