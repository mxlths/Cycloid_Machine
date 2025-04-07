/**
 * InputHandling.cpp
 * 
 * Implements rotary encoder and button input for the Cycloid Machine
 */

#include "InputHandling.h"
#include "MenuSystem.h"

// --- Internal State Variables (moved from Config.h) ---
static volatile int encoderPos = 0;
static volatile int lastEncoded = 0;
static volatile long lastEncoderTime = 0;

static volatile bool buttonPressed = false;
static volatile bool buttonLongPressed = false;
static volatile unsigned long buttonPressTime = 0;
static volatile bool buttonState = true; // Assume released (HIGH) initially
static volatile bool lastButtonState = true;
static volatile unsigned long lastButtonDebounceTime = 0;

// --- Forward Declarations for Static Functions ---
static void updateEncoderPosition();
static void processEncoderChange(int change);
static void handleShortPress();
static void handleLongPress();

// Initialize encoder pins
void setupEncoder() {
  pinMode(ENC_A_PIN, INPUT_PULLUP);
  pinMode(ENC_B_PIN, INPUT_PULLUP);
  pinMode(ENC_BTN_PIN, INPUT_PULLUP);
  
  // Initial encoder state
  lastEncoded = (digitalRead(ENC_A_PIN) << 1) | digitalRead(ENC_B_PIN);
  
  // Set up interrupts
  attachInterrupt(digitalPinToInterrupt(ENC_A_PIN), updateEncoderPosition, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_B_PIN), updateEncoderPosition, CHANGE);
}

// Encoder position update (interrupt-driven)
static void updateEncoderPosition() {
  // Simple debounce
  long time = micros();
  if (time - lastEncoderTime < 1000) return;  // Ignore changes within 1ms
  lastEncoderTime = time;
  
  // Read encoder pins
  int MSB = digitalRead(ENC_A_PIN);
  int LSB = digitalRead(ENC_B_PIN);
  
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
    processEncoderChange(change);
  }
  
  // Save current state
  lastEncoded = encoded;
}

// Process encoder changes
static void processEncoderChange(int change) {
  // Forward to the menu system to handle
  handleMenuNavigation(change);
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
  // Forward to menu system to handle
  handleMenuSelection();
}

// Handle long button press
static void handleLongPress() {
  // Forward to menu system to handle
  handleMenuReturn();
} 