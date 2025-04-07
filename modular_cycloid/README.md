# Modular Cycloid Machine Controller

An Arduino-based control system for a modular Cycloid Machine that controls four stepper motors with adjustable speed ratios, LFO modulation, and a user interface with encoder navigation.

## Features

- Control up to 4 stepper motors with individual speed settings
- Low Frequency Oscillator (LFO) modulation for each motor
- LCD display with menu navigation via rotary encoder
- Preset ratio patterns for quick setup
- Serial command interface for remote control
- Microstepping support for smoother operation

## Hardware Requirements

- Arduino Mega or compatible board
- 4 stepper motors with drivers (A4988 or similar)
- 16x2 LCD with I2C interface
- Rotary encoder with push button
- Power supply appropriate for your stepper motors

## Wiring

See `Config.h` for pin definitions and configuration options.

## Usage

1. Upload the code to your Arduino
2. Use the rotary encoder to navigate menus:
   - Rotate to select options
   - Press to enter/confirm
3. Use serial commands for remote control:
   - 115200 baud rate
   - Type "help" to see available commands

## Version History

### v1.2 (Current)
- Enhanced code organization with centralized configuration
- Improved error handling and input validation
- Implemented complete getter/setter API pattern for module abstraction
- Added debug capabilities with configurable debug outputs
- Moved ratio presets to central configuration
- Enhanced serial interface with better command handling
- Added more extensive documentation

### v1.1
- Refactored code to remove global variables
- Implemented getter/setter pattern for system pause state
- Centralized pause state management in MenuSystem module
- Improved code modularity and organization
- Fixed static function visibility in MenuSystem
- Implemented display helper functions

### v1.0
- Initial release with basic functionality
- Individual motor control
- LFO modulation
- LCD menu system
- Serial command interface

## Project Structure

- `main.ino` - Main program flow
- `Config.h` - Central configuration and pin definitions
- `MotorControl.cpp/h` - Stepper motor control functions
- `MenuSystem.cpp/h` - LCD display and menu navigation
- `InputHandling.cpp/h` - Rotary encoder and button input
- `SerialInterface.cpp/h` - Serial command processing

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 