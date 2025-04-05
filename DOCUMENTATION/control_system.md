# Control System

This document outlines the control system for the Cycloid Machine, based on an Arduino microcontroller.

## Overview

The control system uses an Arduino microcontroller to:
1. Drive four stepper motors (X, Y, Z, and A axes)
2. Read input from a rotary encoder with a button
3. Display information on an LCD screen
4. Manage the menu interface and parameter settings

## Arduino Pin Configuration

The following pin configuration has been defined for the Arduino:

### Motor Control Pins

```
#define X_STEP_PIN    2
#define X_DIR_PIN     5
#define Y_STEP_PIN    3
#define Y_DIR_PIN     6
#define Z_STEP_PIN    4
#define Z_DIR_PIN     7
#define A_STEP_PIN    8  // Platen Wheel
#define A_DIR_PIN     9
```

### User Interface Pins

```
// Rotary Encoder Pins
#define ENCODER_PIN_A   10
#define ENCODER_PIN_B   11
#define ENCODER_BUTTON  12

// LCD Pins
#define LCD_ADDR    0x27  // Common I2C address, may need adjustment
#define LCD_COLS    16    // 16 columns
#define LCD_ROWS    2     // 2 rows
```

## Hardware Interface

### Stepper Motors

The machine uses four stepper motors, one for each of the X, Y, Z, and A axes. Each motor requires:
- A STEP pin, which receives pulses to move the motor
- A DIR pin, which determines the direction of rotation

The motors are likely connected to stepper motor drivers which then connect to the Arduino.

### Rotary Encoder

The rotary encoder serves as the primary input device for the menu system:
- ENCODER_PIN_A and ENCODER_PIN_B read the rotational movement
- ENCODER_BUTTON detects when the encoder is pressed (short or long press)

### LCD Display

The LCD display is connected via I2C:
- Uses address 0x27 (standard for many I2C LCD modules)
- Configured as 16 columns × 2 rows
- Requires SDA and SCL pins from the Arduino (typically A4 and A5 on Uno)

## Alternative Pin Configurations

An alternative pin configuration suggested for the motors is:

```
Motor       Step Pin    Dir Pin
X-Axis      D2          D5
Y-Axis      D3          D6
Z-Axis      D4          D7
A-Axis      D12         D13
```

## CNC Shield Compatibility

The project appears to be compatible with a standard CNC shield, which uses the following pins:

```
Function            UNO Pin
X Step              D2
X Dir               D5
Y Step              D3
Y Dir               D6
Z Step              D4
Z Dir               D7
Enable (all axes)   D8
Spindle (PWM)       D11
Coolant/Fan         D12
Limit Switches      D9, D10
```

## Display Recommendations

For displays, the documentation recommends:

1. **I2C Display (Recommended)**
   - Uses only 2 pins (A4 & A5 for SDA/SCL)
   - Examples: 0.96" OLED or 16x2 LCD with an I2C backpack
   - Pros: Saves pins, simple wiring

2. **SPI Display (Alternative)**
   - Uses more pins (D10, D11, D13, etc.)
   - May conflict with CNC shield
   - Examples: TFT LCD, OLED SPI
   - Pros: Faster refresh rate, but needs more wiring

## Recommended Setup

The recommended setup for the user interface components is:
- Use an I2C display (A4, A5)
- Connect the rotary encoder to D13, A0, A1
- This leaves A2, A3 available for extra buttons or inputs

## Implementation Status

The pin definitions have been specified, but the actual Arduino code implementation appears to be pending. The LCD menu has been simulated in Python to demonstrate functionality. 