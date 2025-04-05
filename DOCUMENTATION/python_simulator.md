# Python LCD Menu Simulator

This document describes the Python simulator for the Cycloid Machine's LCD menu system.

## Overview

The `LCD Menu simulation.py` file contains a Python implementation that simulates the LCD menu interface of the Cycloid Machine using Tkinter. This simulator allows testing and refinement of the menu system before implementing it on the actual Arduino hardware.

## Features

The simulator provides a virtual version of the physical interface, including:

1. A simulated 16×2 LCD display
2. Buttons to simulate rotary encoder inputs:
   - CW (clockwise rotation)
   - CCW (counter-clockwise rotation)
   - Click (short press)
   - Long Press

## Implementation Details

### Main Components

The simulator is implemented as a Python class called `LCDMenuSimulator` with the following structure:

1. Initialization (`__init__`): Sets up the GUI and initializes variables
2. Event handlers: Functions to handle encoder and button events
3. Display update: Function to update the simulated LCD display

### Key Variables

The simulator tracks various state variables:

- `menu_options`: List of main menu options ("SPEED", "LFO", "RATIO", "MASTER", "RESET")
- `current_menu`: The currently active menu
- `selected_option`: The currently selected option in the main menu
- `wheel_speeds`: List of speeds for the four wheels (X, Y, Z, A)
- `lfo_rates` and `lfo_depths`: Lists for LFO parameters
- `selected_wheel`: The currently selected wheel in the SPEED menu
- `editing_speed`: Boolean flag indicating if the user is editing a speed value
- `selected_param`: The currently selected parameter in the LFO menu
- `editing_lfo`: Boolean flag indicating if the user is editing an LFO value
- `system_paused`: Flag indicating if the system is paused
- `ratios`: Predefined ratio sets for the wheels
- `master_time`: Value for the master timing control

### Methods

The simulator implements the following key methods:

1. `handle_encoder_cw()` and `handle_encoder_ccw()`: Simulate clockwise and counter-clockwise rotation
2. `handle_encoder(increment)`: Core method for processing encoder input
3. `handle_button_short_press()`: Simulates a short press of the encoder button
4. `handle_button_long_press()`: Simulates a long press of the encoder button
5. `update_display()`: Updates the simulated LCD display based on the current state

## Menu Functionality

The simulator accurately replicates the functionality described in the menu system documentation:

1. **Main Menu Navigation**: Allows scrolling through menu options
2. **SPEED Menu**: Enables viewing and editing of individual wheel speeds
3. **LFO Menu**: Provides access to LFO parameters for each wheel
4. **RATIO Menu**: Enables selection and application of predefined speed ratios
5. **MASTER Menu**: Allows adjustment of the master speed multiplier
6. **RESET Menu**: Provides option to reset all values to defaults
7. **System Pause/Resume**: Toggles the system's pause state

## Value Constraints

The simulator enforces the same value constraints as defined in the menu system:

- Wheel speeds: Limited to 0.0 - 256.0
- LFO depths: Limited to 0.0 - 100.0
- LFO rates: Limited to 0.0 - 256.0
- Master time: Limited to 0.01 - 999.99

## Running the Simulator

The simulator can be executed as a standalone Python application. The entry point is the `main()` function, which creates a Tkinter root window and instantiates the `LCDMenuSimulator` class.

```python
def main():
    """
    Main function to run the LCD Menu Simulator.
    """
    root = tk.Tk()
    menu_simulator = LCDMenuSimulator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
```

## Limitations

While the simulator provides a close approximation of the intended menu system, it has the following limitations:

1. It does not control actual motors or hardware
2. The display is rendered using Tkinter rather than an actual LCD
3. Some aspects of the LFO functionality (UNI/BI toggle) may not be fully implemented

## Intended Use

This simulator serves as:

1. A prototype for testing the menu system before hardware implementation
2. A reference implementation for the Arduino code
3. A tool for refining the user interface design
4. A demonstration of the system's functionality 