# Modular Cycloid Machine Controller

An Arduino-based control system for a modular Cycloid Machine that controls four stepper motors with adjustable speed ratios, LFO modulation, and a user interface with encoder navigation.

## Features

- Control up to 4 stepper motors with individual speed settings
- Low Frequency Oscillator (LFO) modulation for each motor
- LCD display with menu navigation via rotary encoder
- Preset ratio patterns for quick setup
- Serial command interface for remote control
- Microstepping support (hardware jumper-configured)
- Debug capabilities for diagnostics and development

## Hardware Requirements

- Arduino Mega or compatible board
- 4 stepper motors with drivers (A4988 or similar)
- 16x2 LCD with I2C interface
- Rotary encoder with push button
- Power supply appropriate for your stepper motors

## Wiring

See `Config.h` for pin definitions and configuration options.

## Installation and Usage

1. Upload the code to your Arduino
2. Set microstepping jumpers on your stepper drivers to match `DEFAULT_MICROSTEP` in Config.h
3. Use the rotary encoder to navigate menus:
   - Rotate to select options
   - Press briefly to enter/confirm
   - Long press to return to main menu or toggle pause
4. Use serial commands for remote control:
   - 115200 baud rate
   - Type "help" to see available commands

## Serial Commands

- `status` - Display current system status
- `help` - Show all available commands
- `pause` - Pause all motor movement
- `resume` - Resume motor movements
- `reset` - Reset all settings to defaults
- `enable` - Enable stepper motor drivers
- `disable` - Disable stepper motor drivers
- `master=<value>` - Set master time in milliseconds
- `wheel<n>=<value>` - Set wheel speed ratio (n=1-4)
- `depth<n>=<value>` - Set LFO depth 0-100% (n=1-4)
- `rate<n>=<value>` - Set LFO rate 0-10Hz (n=1-4)
- `polarity<n>=<0/1>` - Set LFO polarity: 0=uni, 1=bi (n=1-4)
- `microstep=<value>` - Set software microstepping mode (1,2,4,8,16,32,64,128)
- `preset=<value>` - Apply ratio preset (1-4)

## Version History

### v1.3 (Current)
- Fixed inconsistencies in function visibility across all modules
- Removed direct hardware microstepping pin control (now jumper-configured)
- Improved input validation in all setter functions with bounds checking
- Consolidated duplicate code, particularly ratio presets
- Added proper error handling throughout the codebase
- Corrected timing calculations to ensure consistent motor speeds
- Enhanced documentation with clear function descriptions
- Improved serial command interface with user-friendly formatting
- Fixed several bug fixes related to menu navigation
- Optimized display updates to reduce flicker

### v1.2
- Enhanced code organization with centralized configuration
- Implemented complete getter/setter API pattern for module abstraction
- Added debug capabilities with configurable debug outputs
- Moved ratio presets to central configuration
- Enhanced serial interface with modern command handling
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

- `main.ino` - Main program flow and global hardware definitions
- `Config.h` - Central configuration and pin definitions
- `MotorControl.cpp/h` - Stepper motor control API and implementation
- `MenuSystem.cpp/h` - LCD display and menu navigation
- `InputHandling.cpp/h` - Rotary encoder and button input
- `SerialInterface.cpp/h` - Serial command processing

## Debug Configuration

For development, you can enable various debug outputs by uncommenting these flags in `main.ino`:
- `DEBUG_TIMING` - Show loop timing information
- `DEBUG_INPUT` - Show encoder input details
- `DEBUG_MOTORS` - Show detailed motor state information

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 