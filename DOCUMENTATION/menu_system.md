# Menu System

This document details the menu system for the Cycloid Machine, which is designed to provide control over all aspects of the machine's operation.

## Overview

The menu system is designed to control a 4-wheel stepper motor system using an LCD display and a rotary encoder. It provides a user interface for adjusting various parameters, including wheel speeds, LFO settings, speed ratios, and master timing.

## User Interface Components

### Input

- **Rotary Encoder**: The primary input device
  - Turning the encoder scrolls through options or adjusts values
  - Short press: Selects an option or toggles editing mode
  - Long press: Returns to the main menu or pauses/resumes the system

### Output

- **LCD Display**: 16×2 character display showing the menu structure, options, and parameter values

## Menu Structure

The menu has the following hierarchy:

```
MAIN MENU
├── SPEED
│   ├── X:010.0
│   ├── Y:010.0
│   ├── Z:010.0
│   └── A:010.0
├── LFO
│   ├── XDEPTH:030.0
│   ├── XRATE:004.2
│   ├── XUNI/BI:UNI
│   ├── YDEPTH:000.0
│   ├── YRATE:256.0
│   ├── YUNI/BI:UNI
│   ├── ZDEPTH:006.0
│   ├── ZRATE:000.0
│   ├── ZUNI/BI:UNI
│   ├── ADEPTH:010.0
│   ├── ARATE:012.0
│   └── AUNI/BI:BI
├── RATIO
│   ├── X001.0 : Y001.0 : Z001.0 : A001.0
│   └── X001.0 : Y002.0 : Z003.0 : A004.0
├── MASTER
│   └── mTIME:010.00
└── RESET
    └── YES / NO
```

## Menu Navigation Details

### 1. Main Menu

- Upon startup, displays the available options (SPEED, LFO, RATIO, MASTER, RESET)
- The encoder is used to scroll through these options
- A short press selects the highlighted option
- A long press toggles the system's pause state

### 2. SPEED Menu

- Displays the speed of the currently selected wheel
- Turning the encoder selects between the four wheels (X, Y, Z, A)
- A short press toggles between selecting a wheel and editing its speed
- When editing, turning the encoder changes the wheel's speed in increments of 0.1
- Speed range is 000.0 to 256.0, displayed as a 4-digit number with 1 decimal place
- Default speed on boot is 010.0 for all wheels
- A long press returns to the main menu

### 3. LFO Menu

- Allows configuration of Low-Frequency Oscillator parameters for each wheel
- The encoder scrolls through parameters (X Depth, X Rate, X Uni/Bi, Y Depth, etc.)
- Depth range is 000.0 to 100.0 (percentage)
- Rate range is 000.0 to 256.0
- Uni/Bi toggles between unipolar and bipolar transformations
- A short press toggles between selecting a parameter and editing its value
- When editing, turning the encoder adjusts the value in appropriate increments
- A long press returns to the main menu

### 4. RATIO Menu

- Provides predefined speed ratios for the wheels
- The encoder scrolls through the available ratio sets
- A short press takes the user to an "APPLY" confirmation screen
- The user can choose "Y" (Yes) or "N" (No) using the encoder
- Selecting "Y" applies the ratios to the wheel speeds and returns to the main menu
- Selecting "N" returns to the ratio selection screen

### 5. MASTER Menu

- Allows adjustment of a master speed multiplier
- A short press toggles the ability to alter the master speed
- Turning the encoder changes the master speed (when editing)
- Master speed is displayed as a 5-digit number with a range of 000.01 to 999.99
- Default value is 001.00
- A long press returns to the main menu

### 6. RESET Menu

- The user can choose "Y" (Yes) or "N" (No) using the encoder
- Selecting "Y" resets all values to the default boot values
- Selecting "N" returns to the main menu

## System Pause/Resume

- A long press on the encoder in the main menu toggles the system's pause state
- When paused, "*PAUSED*" is displayed on the LCD and the motors stop
- Another long press resumes normal operation

## Default Values

- Wheel speeds: 010.0 for all wheels
- LFO depths: 000.0 for all wheels
- LFO rates: 000.0 for all wheels
- Master time: 001.00

## Implementation Status

The menu system has been designed in detail and simulated using a Python program (LCD Menu simulation.py), but the actual Arduino implementation appears to be pending. 