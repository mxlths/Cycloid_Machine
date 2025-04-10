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
  
  // Only check encoder at suitable intervals (debounce)
  if (currentTime - lastEncoderTime < 1000) return;
  
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
    
    // Apply the change to our position
    if (change != 0) {
      encoderPos += change;
      
      // Debug output
      Serial.print(F("Encoder: "));
      Serial.println(change);
      
      // Forward to the menu system to handle
      handleMenuNavigation(change);
    }
    
    // Save current state
    lastEncoded = encoded;
    MSBPrev = MSB;
    LSBPrev = LSB;
    lastEncoderTime = currentTime;
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
  // Debug output
  Serial.println(F("Button: Short Press"));
  
  // Forward to menu system to handle
  handleMenuSelection();
}

// Handle long button press
static void handleLongPress() {
  // Debug output
  Serial.println(F("Button: Long Press"));
  
  // Forward to menu system to handle
  handleMenuReturn();
} 