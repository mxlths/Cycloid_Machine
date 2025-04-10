# Cycloid Machine Control System

A modular Arduino-based control system for a Cycloid Machine that controls four stepper motors with adjustable speed ratios, LFO modulation, and a user interface with rotary encoder navigation.

## Features

- **Four Motor Control**: Control up to four stepper motors (X, Y, Z, A) with individual speed settings
- **LFO Modulation**: Apply Low Frequency Oscillation to each motor with adjustable depth, rate, and polarity
- **Menu Navigation**: Intuitive menu system using a rotary encoder and button
- **Serial Interface**: Command-line interface for remote control and monitoring
- **Preset System**: Save and load different ratio presets
- **Microstepping Control**: Set microstepping mode (1x to 128x) to match jumper configuration

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

## Microstepping

The system supports various microstepping modes (1x, 2x, 4x, 8x, 16x, 32x, 64x, and 128x) which should be set to match the physical jumper configuration on your stepper drivers:

- **A4988 Drivers**: Supports 1x, 2x, 4x, 8x, 16x via jumpers
- **TMC2208 Drivers**: Supports 1x through 128x via jumpers

To change the microstepping mode:
1. Set the physical jumpers on your stepper driver boards
2. Select "MICROSTEP" from the main menu
3. Short press to enter edit mode
4. Turn the encoder to select the desired mode
5. Short press to exit edit mode
6. Long press to apply the changes

**Note:** Higher microstepping values provide smoother motion but reduce available torque. When using higher microstepping modes, you may need to adjust acceleration parameters for optimal performance.

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
4. Use serial commands (9600 baud) for remote control

## Serial Commands

Available commands via Serial (9600 baud):

- `HELP` - Show help information
- `STATUS` - Show current system status
- `PAUSE` - Pause all motors
- `RESUME` - Resume operation
- `RESET` - Reset to default values
- `MICROSTEP value` - Set microstepping mode as per board jumper settings (1, 2, 4, 8, 16, 32, 64, or 128)
- `SPEED X value` - Set X wheel speed (0.1-256.0)
- `LFO X DEPTH value` - Set X LFO depth (0-100%)
- `LFO X RATE value` - Set X LFO rate (0-256)
- `LFO X POL UNI/BI` - Set X LFO polarity (UNI or BI)
- `MASTER value` - Set master time (0.01-999.99)
- `RATIO n` - Apply ratio preset (1-4)

Replace X with Y, Z, or A for other wheels.

## Version History

### v1.2 (Current working 2024-04-10)
    *   Fixed serial status
    *   Microstepping implemented - useful for tuning coarse master speed.

### v1.1 (Refactored - 2024-04-07)

*   **Major Refactoring for Modularity and State Management:**
    *   Removed extensive use of global variables (`extern`) for application state.
    *   Encapsulated state within respective modules (`MotorControl`, `MenuSystem`, `InputHandling`) using `static` variables.
    *   Introduced a clean getter/setter API in `MotorControl.h` for interacting with motor parameters (speed, LFO, master time, microstep).
    *   Refactored `MenuSystem` and `SerialInterface` to use the new `MotorControl` API instead of direct global access.
    *   Moved application logic (applying ratio presets, resetting defaults) from `MotorControl` into `MenuSystem` and `SerialInterface` where the actions are triggered.
    *   Centralized pause state (`systemPaused`) management within `MenuSystem`, allowing control via both the menu (long press) and serial commands (`PAUSE`/`RESUME`).
    *   Defined hardware object instances (`lcd`, `steppers`) in `main.ino` instead of using `extern` declarations.
    *   Improved code readability by using `enum` for menu states, adding constants, and breaking down large functions (e.g., `updateDisplay`).
*   **Corrections (Post-Refactor):**
    *   Fixed `MenuSystem::handleMenuReturn` visibility (made public) and completed its implementation for correctly handling long presses in different menu contexts (exiting edit modes, applying microstepping, cancelling confirmations). 
*   **Benefits:**
    *   Improved code clarity and maintainability.
    *   Reduced coupling between modules.
    *   Lower risk of bugs caused by unintended global state modification.
    *   Easier future development and testing.

### v1.0 (Initial Version)

*   Basic functionality with 4-motor control.
*   LCD menu system via rotary encoder.
*   Adjustable speed, LFO modulation (depth, rate, polarity), master time, microstepping.
*   Serial command interface.
*   Relied heavily on global variables for state. 