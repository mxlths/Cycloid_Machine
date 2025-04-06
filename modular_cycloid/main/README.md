# Cycloid Machine Control System

A modular Arduino-based control system for a Cycloid Machine that controls four stepper motors with adjustable speed ratios, LFO modulation, and a user interface with rotary encoder navigation.

## Features

- **Four Motor Control**: Control up to four stepper motors (X, Y, Z, A) with individual speed settings
- **LFO Modulation**: Apply Low Frequency Oscillation to each motor with adjustable depth, rate, and polarity
- **Menu Navigation**: Intuitive menu system using a rotary encoder and button
- **Serial Interface**: Command-line interface for remote control and monitoring
- **Preset System**: Save and load different ratio presets

## Hardware Requirements

- Arduino board (Uno, Mega, or similar)
- 4 stepper motors and drivers (compatible with AccelStepper library)
- Rotary encoder with button
- 16x2 or 20x4 LCD display (I2C interface recommended)
- Power supply appropriate for your stepper motors

## Pin Configuration

Pin assignments can be modified in the `Config.h` file:

- **Stepper Motors**: Pins 2-9 (2 pins per motor)
- **Encoder**: Pins 10, 11, 12 (CLK, DT, SW)
- **LCD Display**: I2C pins (A4, A5 on most Arduino boards)

## Software Structure

The codebase is organized into multiple modules:

- **Config.h**: Global configuration and pin definitions
- **MenuSystem**: Manages the LCD display and menu navigation
- **MotorControl**: Handles stepper motor control and LFO modulation
- **InputHandling**: Processes rotary encoder and button inputs
- **SerialInterface**: Provides serial command interface for control and monitoring

## Getting Started

1. Connect hardware according to pin configuration
2. Upload the code to your Arduino board
3. Use the rotary encoder to navigate through menus
4. Use serial commands (115200 baud) for remote control

## Serial Commands

Available commands via Serial (115200 baud):

- `HELP` - Show help information
- `STATUS` - Show current system status
- `PAUSE` - Pause all motors
- `RESUME` - Resume operation
- `RESET` - Reset to default values
- `SPEED X value` - Set X wheel speed (0.1-256.0)
- `LFO X DEPTH value` - Set X LFO depth (0-100%)
- `LFO X RATE value` - Set X LFO rate (0-256)
- `LFO X POL UNI/BI` - Set X LFO polarity (UNI or BI)
- `MASTER value` - Set master time (0.01-999.99)
- `RATIO n` - Apply ratio preset (1-4)

Replace X with Y, Z, or A for other wheels. 