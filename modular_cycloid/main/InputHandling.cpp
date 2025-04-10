/**
 * InputHandling.cpp
 * 
 * Implements rotary encoder and button input for the Cycloid Machine
 */

#include "InputHandling.h"
#include "MenuSystem.h"

// --- Internal State Variables (moved from Config.h) ---
static int encoderPos = 0;
static int lastEncoded = 0;
static int MSBPrev = 0;
static int LSBPrev = 0;
static unsigned long lastEncoderTime = 0;
static unsigned long lastEncoderChangeTime = 0;
static int lastChange = 0;
static int accumulatedChange = 0;
static int stableStateCounter = 0;
static unsigned long lastActionTime = 0;
static int consecutiveSteps = 0;

// Enhanced debounce parameters
#define ENCODER_DEBOUNCE_TIME 5000    // Microseconds between readings
#define ENCODER_STABLE_TIME 50000     // Microseconds before considering state stable
#define ENCODER_ACCUMULATION_THRESHOLD 2 // Minimum accumulated changes to register
#define ACCELERATION_TIMEOUT 400      // ms - if no movement for this time, reset acceleration (reduced for quicker response)
#define MAX_ACCELERATION 30           // Maximum acceleration multiplier (increased from 15)

static volatile bool buttonPressed = false;
static volatile bool buttonLongPressed = false;
static volatile unsigned long buttonPressTime = 0;
static volatile bool buttonState = true; // Assume released (HIGH) initially
static volatile bool lastButtonState = true;
static volatile unsigned long lastButtonDebounceTime = 0;

// --- Forward Declarations for Static Functions ---
static void handleShortPress();
static void handleLongPress();

// Initialize encoder pins
void setupEncoder() {
  pinMode(ENC_A_PIN, INPUT_PULLUP);
  pinMode(ENC_B_PIN, INPUT_PULLUP);
  pinMode(ENC_BTN_PIN, INPUT_PULLUP);
  
  // Initial encoder state
  MSBPrev = digitalRead(ENC_A_PIN);
  LSBPrev = digitalRead(ENC_B_PIN);
  lastEncoded = (MSBPrev << 1) | LSBPrev;
  
  // No interrupts needed for polling-based approach
}

// Process encoder changes by polling (called from main loop)
void processEncoderChanges() {
  // Get current time
  unsigned long currentTime = micros();
  
  // Only check encoder at suitable intervals (basic debounce)
  if (currentTime - lastEncoderTime < ENCODER_DEBOUNCE_TIME) return;
  lastEncoderTime = currentTime;
  
  // Read current encoder state
  int MSB = digitalRead(ENC_A_PIN);
  int LSB = digitalRead(ENC_B_PIN);
  
  // Check if anything changed
  if (MSB != MSBPrev || LSB != LSBPrev) {
    // Convert the readings to a single number
    int encoded = (MSB << 1) | LSB;
    
    // Compare with previous reading to determine direction
    int sum = (lastEncoded << 2) | encoded;
    
    // Lookup table for direction: 0=no change, 1=CW, -1=CCW
    static const int lookup_table[] = {0,-1,1,0,1,0,0,-1,-1,0,0,1,0,1,-1,0};
    int change = lookup_table[sum & 0x0F];
    
    // Only consider valid state changes (non-zero changes)
    if (change != 0) {
      // First valid change after a period of stability, or change in same direction
      if (lastChange == 0 || lastChange == change) {
        accumulatedChange += change;
        lastChange = change;
        lastEncoderChangeTime = currentTime;
        stableStateCounter = 0;
      } 
      // Direction reversal - check if it's valid or a bounce
      else if (currentTime - lastEncoderChangeTime > ENCODER_STABLE_TIME) {
        // If enough time has passed, this is likely a real direction change
        accumulatedChange = change;
        lastChange = change;
        lastEncoderChangeTime = currentTime;
        stableStateCounter = 0;
      }
      // Else ignore this as a noise spike (do nothing)
    }
    
    // Save current state
    lastEncoded = encoded;
    MSBPrev = MSB;
    LSBPrev = LSB;
  }
  
  // Check if we have a stable reading with accumulated changes
  stableStateCounter++;
  
  // After a certain number of stable readings, if we have accumulated changes, process them
  if (stableStateCounter >= 3 && accumulatedChange != 0) {
    // Determine final change direction and magnitude
    int finalChange = (accumulatedChange > 0) ? 1 : -1;
    
    // Only register changes if they exceed the threshold for solid rejection of bounces
    if (abs(accumulatedChange) >= ENCODER_ACCUMULATION_THRESHOLD) {
      // Update encoder position
      encoderPos += finalChange;
      
      // Calculate acceleration based on timing
      unsigned long currentMillis = millis();
      
      // Check if this is part of a continuous motion
      if (currentMillis - lastActionTime < ACCELERATION_TIMEOUT) {
        // This is a continuous movement, increase acceleration
        consecutiveSteps++;
        // Cap the acceleration at a maximum value
        if (consecutiveSteps > MAX_ACCELERATION) {
          consecutiveSteps = MAX_ACCELERATION;
        }
      } else {
        // This is a new movement after a pause, reset acceleration
        consecutiveSteps = 1;
      }
      
      // Save the time of this action
      lastActionTime = currentMillis;
      
      // Apply acceleration to the final change
      int acceleratedChange = finalChange * consecutiveSteps;
      
      // Remove debug output
      // Serial.print(F("Encoder: "));
      // Serial.print(finalChange);
      // Serial.print(F(" Accel: "));
      // Serial.print(consecutiveSteps);
      // Serial.print(F(" Final: "));
      // Serial.println(acceleratedChange);
      
      // Forward to the menu system to handle with acceleration
      handleMenuNavigation(acceleratedChange);
    }
    
    // Reset accumulated change after processing
    accumulatedChange = 0;
    lastChange = 0;
    stableStateCounter = 0;
  }
}

// Check for button presses (regularly called from loop)
void checkButtonPress() {
  // Read the button state
  bool reading = digitalRead(ENC_BTN_PIN);
  
  // Debounce the button
  if (reading != lastButtonState) {
    lastButtonDebounceTime = millis();
  }
  
  if ((millis() - lastButtonDebounceTime) > DEBOUNCE_TIME) {
    // If the button state has changed and is stable
    if (reading != buttonState) {
      buttonState = reading;
      
      // Button pressed (LOW due to INPUT_PULLUP)
      if (buttonState == LOW) {
        buttonPressTime = millis();
        buttonPressed = true;
        buttonLongPressed = false;
      }
      // Button released
      else if (buttonPressed) {
        unsigned long pressDuration = millis() - buttonPressTime;
        
        if (pressDuration > LONG_PRESS_TIME) {
          handleLongPress();
          buttonLongPressed = true;
        } else if (!buttonLongPressed) {
          handleShortPress();
        }
        
        buttonPressed = false;
      }
    }
    
    // Check for long press while button is still down
    if (buttonState == LOW && buttonPressed && !buttonLongPressed) {
      if ((millis() - buttonPressTime) > LONG_PRESS_TIME) {
        handleLongPress();
        buttonLongPressed = true;
      }
    }
  }
  
  lastButtonState = reading;
}

// Handle short button press
static void handleShortPress() {
  // Remove debug output
  // Serial.println(F("Button: Short Press"));
  
  // Forward to menu system to handle
  handleMenuSelection();
}

// Handle long button press
static void handleLongPress() {
  // Remove debug output
  // Serial.println(F("Button: Long Press"));
  
  // Forward to menu system to handle
  handleMenuReturn();
} 