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

// --- Pin Definitions ---
// Common enable pin for all drivers
#define ENABLE_PIN 8

// Stepper Motor Pins (Using CNC Shield v3 defaults)
#define X_STEP_PIN 2
#define X_DIR_PIN 5
#define Y_STEP_PIN 3
#define Y_DIR_PIN 6
#define Z_STEP_PIN 4
#define Z_DIR_PIN 7
#define A_STEP_PIN 12 // Using D12 as Step pin for A axis
#define A_DIR_PIN 13  // Using D13 as Dir pin for A axis

// Rotary Encoder Pins
#define ENCODER_PIN_A A0
#define ENCODER_PIN_B A1
#define ENCODER_BTN_PIN A2

// For backwards compatibility with InputHandling.cpp
#define ENC_A_PIN ENCODER_PIN_A
#define ENC_B_PIN ENCODER_PIN_B
#define ENC_BTN_PIN ENCODER_BTN_PIN
#define DEBOUNCE_TIME 50    // Button debounce time in ms
#define LONG_PRESS_TIME 1000 // Long press detection threshold in ms

// LCD I2C Address
#define LCD_SDA A4
#define LCD_SCL A5

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

// --- SYSTEM CONFIGURATION ---
#define SERIAL_BAUD 115200
#define LCD_I2C_ADDR 0x27
#define LCD_COLS 16
#define LCD_ROWS 2
#define MAX_BUFFER_SIZE 256

// --- MENU CONFIGURATION ---
enum MenuState {
  MENU_MAIN,
  MENU_SPEED,
  MENU_LFO,
  MENU_RATIO,
  MENU_MASTER,
  MENU_MICROSTEP,
  MENU_RESET,
  MENU_PAUSE  // New pause menu state
};

// --- MOTOR CONFIGURATION ---
#define MOTORS_COUNT 4  // Number of motors in the system

// --- RATIO PRESETS CONFIGURATION ---
#define NUM_RATIO_PRESETS 4
// Ratio presets define the relative speeds between motors
const float RATIO_PRESETS[NUM_RATIO_PRESETS][MOTORS_COUNT] = {
  {1.0, 1.0, 1.0, 1.0},    // Preset 1: 1:1:1:1 (All equal)
  {1.0, 2.0, 3.0, 4.0},    // Preset 2: 1:2:3:4 (Linear progression)
  {1.0, -1.0, 1.0, -1.0},  // Preset 3: 1:-1:1:-1 (Alternating directions)
  {1.0, 1.5, 2.25, 3.375}  // Preset 4: Geometric progression (1:1.5:2.25:3.375)
};

// --- LFO CONFIGURATION ---
#define LFO_DEPTH_MAX 100   // Maximum LFO depth as a percentage
#define LFO_RATE_MAX 10     // Maximum LFO rate in Hz
#define LFO_UPDATE_INTERVAL 5 // Update interval in milliseconds
#define LFO_RESOLUTION 1000   // Phase resolution for smoother LFO

// --- MICROSTEPPING CONFIGURATION ---
#define NUM_VALID_MICROSTEPS 8
const int VALID_MICROSTEPS[NUM_VALID_MICROSTEPS] = {1, 2, 4, 8, 16, 32, 64, 128};

// --- DEFAULT VALUES ---
#define DEFAULT_MASTER_TIME 1000 // Default master time (period) in milliseconds (e.g., 1000ms for 60RPM at speed 1.0)
#define DEFAULT_SPEED_RATIO 1.0 // Default ratio for all motors
#define DEFAULT_LFO_DEPTH 0     // Default LFO depth (0 = off)
#define DEFAULT_LFO_RATE 1      // Default LFO rate in Hz
#define DEFAULT_LFO_POLARITY false // Default LFO polarity (false = unipolar)
#define DEFAULT_MICROSTEP 16    // Default microstepping mode (MATCH YOUR JUMPERS)

// --- GLOBAL HARDWARE OBJECTS ---
// Declare global hardware objects defined in main.ino
extern LiquidCrystal_I2C lcd;
extern AccelStepper stepperX;
extern AccelStepper stepperY;
extern AccelStepper stepperZ;
extern AccelStepper stepperA;
extern AccelStepper* steppers[MOTORS_COUNT];
extern const char* wheelLabels[MOTORS_COUNT];

#endif // CONFIG_H 