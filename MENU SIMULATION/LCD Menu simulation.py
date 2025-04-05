import tkinter as tk

class LCDMenuSimulator:
    """
    Simulates an LCD menu system controlled by a rotary encoder.
    This class provides a GUI for testing and visualizing how an LCD menu
    on a physical device would behave when controlled by rotary encoder inputs.
    """

    def __init__(self, root):
        """
        Initializes the menu system with default values and creates the GUI.
        
        Args:
            root: The tkinter root window
        """
        self.root = root
        self.root.title("LCD Menu Simulator")

        # ---- Menu Structure Configuration ----
        self.menu_options = ["SPEED", "LFO", "RATIO", "MASTER", "RESET"]
        self.current_menu = "MAIN"  # Start in main menu
        self.selected_option = 0    # First option selected by default
        
        # ---- Wheel Speed Parameters ----
        self.wheel_speeds = [10.0, 10.0, 10.0, 10.0]  # Default speeds for wheels X,Y,Z,A
        self.selected_wheel = 0                        # Currently selected wheel (0-3)
        self.editing_speed = False                     # Flag to track if we're in edit mode
        
        # ---- LFO (Low Frequency Oscillator) Parameters ----
        self.lfo_rates = [0.0, 0.0, 0.0, 0.0]    # Default rates for X,Y,Z,A oscillators
        self.lfo_depths = [0.0, 0.0, 0.0, 0.0]   # Default depths for X,Y,Z,A oscillators
        self.selected_param = 0                   # Current parameter index (0-11)
        self.editing_lfo = False                  # Flag to track if we're in edit mode
        
        # ---- Ratio Presets ----
        # Each row represents a preset with 4 values for the 4 wheels
        self.ratios = [
            [100, 100, 100, 100],  # Equal ratios
            [50, 100, 150, 200],   # Increasing ratios
            [200, 150, 100, 50],   # Decreasing ratios
            [75, 125, 175, 225],   # Varied ratios
        ]
        self.selected_ratio_index = 0  # Currently selected ratio preset
        self.applying_ratio = False    # Flag for apply confirmation state
        self.apply_choice = 0          # 0 for No, 1 for Yes
        
        # ---- Master Parameters ----
        self.master_time = 1.00        # Default time in seconds
        self.editing_master = False    # Flag to track if we're editing
        
        # ---- Reset Menu Parameters ----
        self.reset_choice = 0          # 0 for NO, 1 for YES in reset menu
        
        # ---- System State ----
        self.system_paused = False     # System running by default
        self.encoder_value = 0         # Tracks cumulative encoder rotation

        # ---- Create GUI Elements ----
        # Main display area (simulates LCD)
        self.display_label = tk.Label(root, text="", font=("Courier", 12), justify=tk.LEFT)
        self.display_label.pack(pady=10)

        # Control buttons frame
        button_frame = tk.Frame(root)
        button_frame.pack()

        # Buttons to simulate encoder actions
        self.click_button = tk.Button(button_frame, text="Click", command=self.handle_button_short_press)
        self.click_button.pack(side=tk.LEFT, padx=5)
        
        self.long_button = tk.Button(button_frame, text="Long Press", command=self.handle_button_long_press)
        self.long_button.pack(side=tk.LEFT, padx=5)
        
        self.cw_button = tk.Button(button_frame, text="CW", command=self.handle_encoder_cw)
        self.cw_button.pack(side=tk.LEFT, padx=5)
        
        self.ccw_button = tk.Button(button_frame, text="CCW", command=self.handle_encoder_ccw)
        self.ccw_button.pack(side=tk.LEFT, padx=5)

        # Initialize the display
        self.update_display()

    def handle_encoder_cw(self):
        """Simulates turning the encoder clockwise (increment)."""
        self.handle_encoder(1)

    def handle_encoder_ccw(self):
        """Simulates turning the encoder counter-clockwise (decrement)."""
        self.handle_encoder(-1)

    def handle_encoder(self, increment):
        """
        Processes rotary encoder input based on current menu context.
        
        This method routes the encoder input to the appropriate handler
        based on which menu is currently active.
        
        Args:
            increment: The direction and amount of change (+1 for CW, -1 for CCW)
        """
        # Track total encoder movement (useful for debugging)
        self.encoder_value += increment

        # Handle encoder input based on current menu context
        if self.current_menu == "MAIN":
            # In main menu, cycle through available options
            self.selected_option = (self.selected_option + increment) % len(self.menu_options)
            
        elif self.current_menu == "SPEED":
            if self.editing_speed:
                # When editing, adjust the selected wheel's speed
                self.wheel_speeds[self.selected_wheel] += increment * 0.1  # Fine adjustment (0.1 increments)
                # Clamp value between 0.0 and 256.0
                self.wheel_speeds[self.selected_wheel] = max(min(self.wheel_speeds[self.selected_wheel], 256.0), 0.0)
            else:
                # When not editing, select which wheel to adjust (X, Y, Z, or A)
                self.selected_wheel = (self.selected_wheel + increment) % 4
                
        elif self.current_menu == "LFO":
            if self.editing_lfo:
                # When editing, adjust either depth or rate based on parameter index
                if self.selected_param % 2 == 0:  # Even indices are depths
                    self.lfo_depths[self.selected_param // 2] += increment * 0.1
                    # Clamp depth between 0.0 and 100.0
                    self.lfo_depths[self.selected_param // 2] = max(min(self.lfo_depths[self.selected_param // 2], 100.0), 0.0)
                else:  # Odd indices are rates
                    self.lfo_rates[self.selected_param // 2] += increment * 0.1
                    # Clamp rate between 0.0 and 256.0
                    self.lfo_rates[self.selected_param // 2] = max(min(self.lfo_rates[self.selected_param // 2], 256.0), 0.0)
            else:
                # When not editing, cycle through the parameter list (0-11)
                # Parameters alternate: X-depth, X-rate, Y-depth, Y-rate, etc.
                self.selected_param = (self.selected_param + increment) % 12
                
        elif self.current_menu == "MASTER":
            if self.editing_master:
                # Adjust master time with finer granularity (0.01 increments)
                self.master_time += increment * 0.01
                # Clamp time between 0.01 and 999.99 seconds
                self.master_time = max(min(self.master_time, 999.99), 0.01)
                
        elif self.current_menu == "RATIO":
            if self.applying_ratio:
                # Toggle between Yes/No in the confirmation dialog
                self.apply_choice = (self.apply_choice + increment) % 2
            else:
                # Cycle through available ratio presets
                self.selected_ratio_index = (self.selected_ratio_index + increment) % len(self.ratios)
                
        elif self.current_menu == "RESET":
            # Toggle between NO and YES options in reset menu
            self.reset_choice = (self.reset_choice + increment) % 2

        # Update the display to reflect changes
        self.update_display()

    def handle_button_short_press(self):
        """
        Processes short button press actions based on current menu context.
        
        This simulates clicking the rotary encoder, with different behaviors
        depending on which menu is active and what state we're in.
        """
        if self.current_menu == "MAIN":
            # Navigate from main menu to selected submenu
            self.current_menu = self.menu_options[self.selected_option]
            
            # Initialize submenu states
            if self.current_menu == "SPEED":
                self.selected_wheel = 0
                self.editing_speed = False
            elif self.current_menu == "LFO":
                self.selected_param = 0
                self.editing_lfo = False
            elif self.current_menu == "RATIO":
                self.applying_ratio = True
                self.apply_choice = 0
            elif self.current_menu == "MASTER":
                self.editing_master = not self.editing_master
            elif self.current_menu == "RESET":
                self.reset_choice = 0  # Default to NO
                
        elif self.current_menu == "SPEED":
            # Toggle editing mode for speed
            self.editing_speed = not self.editing_speed
            
        elif self.current_menu == "LFO":
            # Toggle editing mode for LFO parameters
            self.editing_lfo = not self.editing_lfo
            
        elif self.current_menu == "MASTER":
            if self.editing_master:
                # Exit editing mode
                self.editing_master = False
            else:
                # Return to main menu
                self.current_menu = "MAIN"
                
        elif self.current_menu == "RATIO":
            if self.applying_ratio:
                if self.apply_choice == 1:  # YES selected
                    # Apply the selected ratio preset to wheel speeds
                    for i in range(4):
                        self.wheel_speeds[i] = self.ratios[self.selected_ratio_index][i]
                    # Return to main menu after applying
                    self.current_menu = "MAIN"
                else:  # NO selected
                    # Exit apply confirmation state
                    self.applying_ratio = False
            else:
                # Return to main menu
                self.current_menu = "MAIN"
                
        elif self.current_menu == "RESET":
            if self.reset_choice == 1:  # YES selected
                # Reset all values to defaults
                self.wheel_speeds = [10.0, 10.0, 10.0, 10.0]
                self.lfo_rates = [0.0, 0.0, 0.0, 0.0]
                self.lfo_depths = [0.0, 0.0, 0.0, 0.0]
                self.master_time = 1.00
                # Return to main menu after reset
                self.current_menu = "MAIN"
            else:  # NO selected
                # Return to main menu without reset
                self.current_menu = "MAIN"
                
        # Update the display to reflect changes
        self.update_display()

    def handle_button_long_press(self):
        """
        Processes long button press actions.
        
        Long press has consistent behavior:
        - In main menu: Toggle system pause state
        - In any submenu: Return to main menu
        """
        if self.current_menu == "MAIN":
            # Toggle pause state
            self.system_paused = not self.system_paused
        else:
            # Return to main menu from any submenu
            self.current_menu = "MAIN"
            
        # Update the display to reflect changes
        self.update_display()

    def update_display(self):
        """
        Formats and updates the simulated LCD display based on current menu and state.
        
        Each menu has a specific display format with indicators for selection and editing.
        The display is limited to simulate a real LCD screen's constraints.
        """
        display_text = ""
        
        # System pause state overrides normal menu display
        if self.system_paused:
            display_text = "System Paused   *"
            
        # Main menu display
        elif self.current_menu == "MAIN":
            # Show all menu options with selection marker
            for i, option in enumerate(self.menu_options):
                if i == self.selected_option:
                    display_text += ">"  # Selection indicator
                display_text += option + " "
            # Limit to 16 characters (typical LCD width)
            display_text = display_text[:16]
            
        # Speed menu display
        elif self.current_menu == "SPEED":
            display_text = "WHEEL SPEED\n"
            # Show selected wheel (X, Y, Z, or A)
            display_text += ["X:", "Y:", "Z:", "A:"][self.selected_wheel]
            # Format speed value with fixed width and precision
            display_text += f"{self.wheel_speeds[self.selected_wheel]:05.1f}"
            # Add edit indicator if in editing mode
            if self.editing_speed:
                display_text = display_text[:16] + "#"
            # Limit to 16 characters
            display_text = display_text[:16]
            
        # LFO menu display
        elif self.current_menu == "LFO":
            if not self.editing_lfo:
                # Show parameter name based on selection
                if self.selected_param % 2 == 0:  # Depth parameters
                    wheel_labels = ["X DEPTH: ", "Y DEPTH: ", "Z DEPTH: ", "A DEPTH: "]
                    display_text = wheel_labels[self.selected_param // 2]
                    # Format depth value
                    display_text += f"{self.lfo_depths[self.selected_param // 2]:05.1f}#"
                else:  # Rate parameters
                    wheel_labels = ["X RATE: ", "Y RATE: ", "Z RATE: ", "A RATE: "]
                    display_text = wheel_labels[self.selected_param // 2]
                    # Format rate value
                    display_text += f"{self.lfo_rates[self.selected_param // 2]:05.1f}#"
            else:
                # Display format when in editing mode
                if self.selected_param % 2 == 0:  # Editing depth
                    display_text = "LFO DEPTH\n"
                    # Show wheel identifier
                    wheel_identifiers = ["X:", "Y:", "Z:", "A:"]
                    display_text += wheel_identifiers[self.selected_param // 2]
                    # Format depth value
                    display_text += f"{self.lfo_depths[self.selected_param // 2]:05.1f}#"
                else:  # Editing rate
                    display_text = "LFO RATE\n"
                    # Show wheel identifier
                    wheel_identifiers = ["X:", "Y:", "Z:", "A:"]
                    display_text += wheel_identifiers[self.selected_param // 2]
                    # Format rate value
                    display_text += f"{self.lfo_rates[self.selected_param // 2]:05.1f}#"
            
            # Limit to 16 characters
            display_text = display_text[:16]
            
        # Master time menu display
        elif self.current_menu == "MASTER":
            display_text = "Master Time\n"
            # Format time value
            display_text += f"{self.master_time:05.2f} Sec"
            # Add edit indicator if in editing mode
            if self.editing_master:
                display_text = display_text[:16] + "#"
            # Limit to 16 characters
            display_text = display_text[:16]
            
        # Ratio menu display
        elif self.current_menu == "RATIO":
            if not self.applying_ratio:
                # Show the currently selected ratio preset
                display_text = "RATIO SET\n"
                # Format first two ratios
                display_text += f"1:{self.ratios[self.selected_ratio_index][0]:05.1f}, 2:{self.ratios[self.selected_ratio_index][1]:05.1f}\n"
                # Format last two ratios
                display_text += f"3:{self.ratios[self.selected_ratio_index][2]:05.1f}, 4:{self.ratios[self.selected_ratio_index][3]:05.1f}"
                # Allow up to 32 characters (two LCD lines)
                display_text = display_text[:32]
            else:
                # Apply confirmation dialog
                display_text = "APPLY: "
                display_text += "Y#" if self.apply_choice == 1 else "N#"
                # Limit to 16 characters
                display_text = display_text[:16]
                
        # Reset menu display
        elif self.current_menu == "RESET":
            display_text = "RESET all values?\n"
            # Show NO or YES based on selection
            display_text += "NO" if self.reset_choice == 0 else "YES"
            # Limit to 16 characters
            display_text = display_text[:16]

        # Update the display label with formatted text
        self.display_label.config(text=display_text)


def main():
    """
    Main function to run the LCD Menu Simulator.
    Creates the tkinter root window and initializes the simulator.
    """
    root = tk.Tk()
    menu_simulator = LCDMenuSimulator(root)
    root.mainloop()


if __name__ == "__main__":
    main()
