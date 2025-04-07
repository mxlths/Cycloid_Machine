/**
 * Config.h
 * 
 * Configuration file for Cycloid Machine
 * Contains pin definitions, constants, and configuration settings
 */

#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <AccelStepper.h>

// ---- PIN DEFINITIONS ----
// CNC Shield connections (standard)
#define X_STEP_PIN 2
#define X_DIR_PIN 5
#define Y_STEP_PIN 3
#define Y_DIR_PIN 6
#define Z_STEP_PIN 4
#define Z_DIR_PIN 7
#define A_STEP_PIN 12
#define A_DIR_PIN 13
#define ENABLE_PIN 8

// Rotary Encoder (connected to limit switch pins on CNC Shield)
#define ENC_A_PIN 9    // CLK
#define ENC_B_PIN 10   // DT
#define ENC_BTN_PIN 11 // SW

// ---- CONSTANTS ----
#define MOTORS_COUNT 4
#define LCD_COLS 16
#define LCD_ROWS 2
#define LCD_I2C_ADDR 0x27  // Change to 0x3F if needed

// Microstepping configuration
#define MICROSTEP_FULL 1       // Full step mode (default)
#define MICROSTEP_HALF 2       // Half step mode
#define MICROSTEP_QUARTER 4    // Quarter step mode
#define MICROSTEP_EIGHTH 8     // Eighth step mode
#define MICROSTEP_SIXTEENTH 16 // Sixteenth step mode
#define MICROSTEP_32 32        // 32 microsteps (TMC2208 only)
#define MICROSTEP_64 64        // 64 microsteps (TMC2208 only)
#define MICROSTEP_128 128      // 128 microsteps (TMC2208 only)

#define STEPS_PER_MOTOR_REV 200  // 1.8° stepper motors
#define GEAR_RATIO 3             // 1:3 gear reduction
#define STEPS_PER_WHEEL_REV (STEPS_PER_MOTOR_REV * GEAR_RATIO) // 600 steps

#define SERIAL_BAUD_RATE 9600

// Add MenuState enum
enum MenuState {
  MENU_MAIN = 0, // Keep explicit values for compatibility if needed, though not strictly necessary
  MENU_SPEED,
  MENU_LFO,
  MENU_RATIO,
  MENU_MASTER,
  MENU_MICROSTEP,
  MENU_RESET
};

// Button timing
#define DEBOUNCE_TIME 50        // ms
#define LONG_PRESS_TIME 1000    // ms

// Motor update interval
#define MOTOR_UPDATE_INTERVAL 5 // ms

// LFO resolution
#define LFO_RESOLUTION 1000     // Phase resolution for smoother LFO

// ---- EXTERNAL DECLARATIONS ----

// LCD display
extern LiquidCrystal_I2C lcd;

// Stepper motors
extern AccelStepper stepperX;
extern AccelStepper stepperY;
extern AccelStepper stepperZ;
extern AccelStepper stepperA;
extern AccelStepper* steppers[MOTORS_COUNT];

// Wheel labels
extern const char* wheelLabels[MOTORS_COUNT];

#endif // CONFIG_H 