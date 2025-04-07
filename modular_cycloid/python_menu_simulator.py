#!/usr/bin/env python3
"""
Cycloid Machine Menu System Simulator v1.4

This program simulates the 16x2 LCD menu navigation system of the Cycloid Machine,
allowing for testing and demonstration of the menu flow and interactions without
requiring physical hardware.

Matches the current implementation in modular_cycloid v1.4
"""

import tkinter as tk
from tkinter import ttk
import math

class CycloidMenuSimulator:
    """
    Simulates the 16x2 LCD menu system based on the modular_cycloid implementation.
    Handles rotary encoder inputs (CW, CCW, Short Press, Long Press)
    and updates a simulated 16x2 display.
    """

    # --- Constants matching Config.h ---
    # Menu states
    MENU_MAIN = 0
    MENU_SPEED = 1
    MENU_LFO = 2
    MENU_RATIO = 3
    MENU_MASTER = 4
    MENU_MICROSTEP = 5
    MENU_RESET = 6

    # LCD dimensions
    LCD_COLS = 16
    LCD_ROWS = 2

    # Motor configuration
    MOTORS_COUNT = 4
    
    # LFO configuration
    LFO_DEPTH_MAX = 100
    LFO_RATE_MAX = 10
    LFO_RESOLUTION = 1000

    # Ratio presets from Config.h
    NUM_RATIO_PRESETS = 4
    RATIO_PRESETS = [
        [1.0, 1.0, 1.0, 1.0],    # Preset 1: 1:1:1:1 (All equal)
        [1.0, 2.0, 3.0, 4.0],    # Preset 2: 1:2:3:4 (Linear progression)
        [1.0, -1.0, 1.0, -1.0],  # Preset 3: 1:-1:1:-1 (Alternating directions)
        [1.0, 1.5, 2.25, 3.375]  # Preset 4: Geometric progression
    ]

    # Microstepping configuration
    NUM_VALID_MICROSTEPS = 8
    VALID_MICROSTEPS = [1, 2, 4, 8, 16, 32, 64, 128]
    
    # Default values
    DEFAULT_MASTER_TIME = 1000
    DEFAULT_SPEED_RATIO = 1.0
    DEFAULT_LFO_DEPTH = 0
    DEFAULT_LFO_RATE = 1
    DEFAULT_LFO_POLARITY = False  # False = unipolar
    DEFAULT_MICROSTEP = 16

    def __init__(self, root):
        """
        Initializes the simulator with default values and GUI elements.
        """
        self.root = root
        self.root.title("Cycloid Machine Menu Simulator v1.4")
        
        # --- Menu State Variables ---
        self.currentMenu = self.MENU_MAIN
        self.selectedMainMenuOption = 0
        self.selectedSpeedWheel = 0
        self.selectedLfoParam = 0
        self.selectedRatioPreset = 0
        self.selectedMicrostepIndex = 4  # Default to 16x (index 4 in VALID_MICROSTEPS)
        self.pendingMicrostepMode = self.DEFAULT_MICROSTEP
        
        # --- Editing Mode Flags ---
        self.editingSpeed = False
        self.editingLfo = False
        self.editingMaster = False
        self.editingMicrostep = False
        self.confirmingRatio = False
        self.confirmingReset = False
        self.ratioChoice = False  # false=NO, true=YES for ratio preset confirmation
        self.resetChoice = False  # false=NO, true=YES for reset confirmation
        
        # --- System State ---
        self.systemPaused = False
        
        # --- Motor Settings ---
        self.wheelSpeeds = [self.DEFAULT_SPEED_RATIO] * self.MOTORS_COUNT
        self.lfoDepths = [self.DEFAULT_LFO_DEPTH] * self.MOTORS_COUNT
        self.lfoRates = [self.DEFAULT_LFO_RATE] * self.MOTORS_COUNT
        self.lfoPolarities = [self.DEFAULT_LFO_POLARITY] * self.MOTORS_COUNT
        self.masterTime = self.DEFAULT_MASTER_TIME
        self.currentMicrostepMode = self.DEFAULT_MICROSTEP
        
        # --- Define Wheel Labels ---
        self.wheelLabels = ["X", "Y", "Z", "A"]
        
        # --- GUI Setup ---
        self.setup_gui()
        
        # Initialize display
        self.update_display()

    def setup_gui(self):
        """Sets up the GUI elements for the simulator."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # LCD Display (fixed width font for accurate representation)
        self.lcd_frame = ttk.Frame(main_frame, borderwidth=2, relief="groove", padding="5")
        self.lcd_frame.grid(row=0, column=0, columnspan=4, pady=10)
        
        self.lcd_line1 = ttk.Label(self.lcd_frame, font=("Courier New", 12), width=16)
        self.lcd_line1.grid(row=0, column=0)
        
        self.lcd_line2 = ttk.Label(self.lcd_frame, font=("Courier New", 12), width=16)
        self.lcd_line2.grid(row=1, column=0)
        
        # Control buttons
        ttk.Button(main_frame, text="◀", width=5, 
                   command=lambda: self.handle_encoder(-1)).grid(row=1, column=0, padx=5, pady=10)
        
        ttk.Button(main_frame, text="▶", width=5, 
                   command=lambda: self.handle_encoder(1)).grid(row=1, column=1, padx=5, pady=10)
        
        ttk.Button(main_frame, text="Short Press", 
                   command=self.handle_short_press).grid(row=1, column=2, padx=5, pady=10)
        
        ttk.Button(main_frame, text="Long Press", 
                   command=self.handle_long_press).grid(row=1, column=3, padx=5, pady=10)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="System Status", padding="5")
        status_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)
        
        # Status indicators
        self.status_text = tk.StringVar(value="RUNNING")
        ttk.Label(status_frame, text="System:").grid(row=0, column=0, padx=5)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_text)
        self.status_label.grid(row=0, column=1, padx=5)
        
        self.menu_text = tk.StringVar(value="MAIN")
        ttk.Label(status_frame, text="Menu:").grid(row=0, column=2, padx=5)
        self.menu_label = ttk.Label(status_frame, textvariable=self.menu_text)
        self.menu_label.grid(row=0, column=3, padx=5)
        
        # Motor values frame
        motor_frame = ttk.LabelFrame(main_frame, text="Motor Values", padding="5")
        motor_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)
        
        # Column headers
        for i, label in enumerate(["Wheel", "Speed", "LFO Depth", "LFO Rate", "LFO Mode"]):
            ttk.Label(motor_frame, text=label).grid(row=0, column=i, padx=5)
        
        # Motor values
        self.motor_values = []
        for i in range(self.MOTORS_COUNT):
            wheel_label = ttk.Label(motor_frame, text=self.wheelLabels[i])
            wheel_label.grid(row=i+1, column=0, padx=5, pady=2)
            
            row_values = []
            for j in range(4):  # Speed, Depth, Rate, Polarity
                value_var = tk.StringVar(value="0.0")
                value_label = ttk.Label(motor_frame, textvariable=value_var, width=8)
                value_label.grid(row=i+1, column=j+1, padx=5, pady=2)
                row_values.append(value_var)
            
            self.motor_values.append(row_values)
        
        # Update motor display values
        self.update_motor_display()

    def update_motor_display(self):
        """Updates the motor value display in the GUI."""
        for i in range(self.MOTORS_COUNT):
            self.motor_values[i][0].set(f"{self.wheelSpeeds[i]:.1f}")
            self.motor_values[i][1].set(f"{self.lfoDepths[i]:.1f}%")
            self.motor_values[i][2].set(f"{self.lfoRates[i]:.1f} Hz")
            self.motor_values[i][3].set("Bipolar" if self.lfoPolarities[i] else "Unipolar")
        
        # Update status indicators
        self.status_text.set("PAUSED" if self.systemPaused else "RUNNING")
        
        menu_names = ["MAIN", "SPEED", "LFO", "RATIO", "MASTER", "MICROSTEP", "RESET"]
        self.menu_text.set(menu_names[self.currentMenu])

    def handle_encoder(self, change):
        """
        Handles encoder rotation events.
        
        Args:
            change: Integer indicating direction (1 for CW, -1 for CCW)
        """
        if self.systemPaused and self.currentMenu != self.MENU_MAIN:
            return
        
        if self.currentMenu == self.MENU_MAIN:
            # Cycle through main menu options (6 options total)
            self.selectedMainMenuOption = (self.selectedMainMenuOption + 6 + change) % 6
        
        elif self.currentMenu == self.MENU_SPEED:
            if self.editingSpeed:
                # Update wheel speed
                current_speed = self.wheelSpeeds[self.selectedSpeedWheel]
                new_speed = current_speed + change * 0.1
                # Apply constraints
                if new_speed < -10.0:
                    new_speed = -10.0
                elif new_speed > 10.0:
                    new_speed = 10.0
                self.wheelSpeeds[self.selectedSpeedWheel] = new_speed
            else:
                # Cycle through wheels
                self.selectedSpeedWheel = (self.selectedSpeedWheel + self.MOTORS_COUNT + change) % self.MOTORS_COUNT
        
        elif self.currentMenu == self.MENU_LFO:
            if self.editingLfo:
                wheel_index = self.selectedLfoParam // 3
                param_type = self.selectedLfoParam % 3
                
                if param_type == 0:  # Depth
                    current_depth = self.lfoDepths[wheel_index]
                    new_depth = current_depth + change * 0.1
                    # Apply constraints
                    if new_depth < 0:
                        new_depth = 0
                    elif new_depth > self.LFO_DEPTH_MAX:
                        new_depth = self.LFO_DEPTH_MAX
                    self.lfoDepths[wheel_index] = new_depth
                
                elif param_type == 1:  # Rate
                    current_rate = self.lfoRates[wheel_index]
                    new_rate = current_rate + change * 0.1
                    # Apply constraints
                    if new_rate < 0:
                        new_rate = 0
                    elif new_rate > self.LFO_RATE_MAX:
                        new_rate = self.LFO_RATE_MAX
                    self.lfoRates[wheel_index] = new_rate
                
                else:  # Polarity (toggle)
                    if change != 0:
                        self.lfoPolarities[wheel_index] = not self.lfoPolarities[wheel_index]
            else:
                # Cycle through LFO parameters (12 total: 4 wheels x 3 params each)
                total_params = self.MOTORS_COUNT * 3
                self.selectedLfoParam = (self.selectedLfoParam + total_params + change) % total_params
        
        elif self.currentMenu == self.MENU_RATIO:
            if self.confirmingRatio:
                # Toggle YES/NO choice
                if change != 0:
                    self.ratioChoice = not self.ratioChoice
            else:
                # Cycle through ratio presets
                self.selectedRatioPreset = (self.selectedRatioPreset + self.NUM_RATIO_PRESETS + change) % self.NUM_RATIO_PRESETS
        
        elif self.currentMenu == self.MENU_MASTER:
            if self.editingMaster:
                # Update master time
                current_time = self.masterTime
                new_time = current_time + change * 10.0  # Adjust by 10ms increments
                # Apply constraints
                if new_time < 10.0:
                    new_time = 10.0  # Min 10ms
                elif new_time > 60000.0:
                    new_time = 60000.0  # Max 60s
                self.masterTime = new_time
        
        elif self.currentMenu == self.MENU_MICROSTEP:
            if self.editingMicrostep:
                # Adjust the index based on encoder change
                if change > 0:
                    self.selectedMicrostepIndex = (self.selectedMicrostepIndex + 1) % self.NUM_VALID_MICROSTEPS
                elif change < 0:
                    self.selectedMicrostepIndex = (self.selectedMicrostepIndex + self.NUM_VALID_MICROSTEPS - 1) % self.NUM_VALID_MICROSTEPS
                
                # Update pending microstepping mode
                if change != 0:
                    self.pendingMicrostepMode = self.VALID_MICROSTEPS[self.selectedMicrostepIndex]
        
        elif self.currentMenu == self.MENU_RESET:
            if self.confirmingReset:
                # Toggle YES/NO choice
                if change != 0:
                    self.resetChoice = not self.resetChoice
        
        # Update display after any change
        self.update_display()
        self.update_motor_display()

    def handle_short_press(self):
        """Handles short button press events."""
        if self.systemPaused and self.currentMenu != self.MENU_MAIN:
            return
        
        if self.currentMenu == self.MENU_MAIN:
            # Enter selected submenu (adding 1 because MENU_MAIN is 0)
            self.currentMenu = self.selectedMainMenuOption + 1
        
        elif self.currentMenu == self.MENU_SPEED:
            # Toggle editing mode
            self.editingSpeed = not self.editingSpeed
        
        elif self.currentMenu == self.MENU_LFO:
            # Toggle editing mode
            self.editingLfo = not self.editingLfo
        
        elif self.currentMenu == self.MENU_RATIO:
            if not self.confirmingRatio:
                # Enter confirmation mode
                self.confirmingRatio = True
                self.ratioChoice = False  # Default to NO
            else:
                # Process confirmation choice
                if self.ratioChoice:  # YES selected
                    self.apply_ratio_preset()
                    self.confirmingRatio = False
                    self.currentMenu = self.MENU_MAIN
                else:  # NO selected
                    self.confirmingRatio = False  # Return to ratio selection
            
        elif self.currentMenu == self.MENU_MASTER:
            # Toggle editing mode
            self.editingMaster = not self.editingMaster
        
        elif self.currentMenu == self.MENU_MICROSTEP:
            # Toggle editing mode
            self.editingMicrostep = not self.editingMicrostep
        
        elif self.currentMenu == self.MENU_RESET:
            if self.confirmingReset:
                # Process confirmation choice
                if self.resetChoice:  # YES selected
                    self.reset_to_defaults()
                    self.confirmingReset = False
                    self.currentMenu = self.MENU_MAIN
                else:  # NO selected
                    self.confirmingReset = False
                    self.currentMenu = self.MENU_MAIN
            
        # Update display after any change
        self.update_display()
        self.update_motor_display()

    def handle_long_press(self):
        """Handles long button press events."""
        if self.currentMenu == self.MENU_MAIN:
            # Toggle pause
            self.systemPaused = not self.systemPaused
            if self.systemPaused:
                print("System Paused")
            else:
                print("System Resumed")
        
        elif self.editingSpeed or self.editingLfo or self.editingMaster:
            # Exit edit mode
            self.editingSpeed = False
            self.editingLfo = False
            self.editingMaster = False
            print("Exited edit mode")
        
        elif self.currentMenu == self.MENU_MICROSTEP:
            if self.editingMicrostep:
                # Apply the pending microstepping mode
                self.currentMicrostepMode = self.pendingMicrostepMode
                print(f"Microstepping updated to {self.currentMicrostepMode}x")
                self.editingMicrostep = False
            else:
                # Return to main menu
                self.currentMenu = self.MENU_MAIN
        
        elif self.confirmingRatio or self.confirmingReset:
            # Cancel confirmation and return to main menu
            self.confirmingRatio = False
            self.confirmingReset = False
            self.currentMenu = self.MENU_MAIN
        
        else:
            # Return to main menu from any other state
            self.currentMenu = self.MENU_MAIN
        
        # Update display after any change
        self.update_display()
        self.update_motor_display()

    def apply_ratio_preset(self):
        """Applies the selected ratio preset to all motors."""
        preset = self.RATIO_PRESETS[self.selectedRatioPreset]
        for i in range(self.MOTORS_COUNT):
            self.wheelSpeeds[i] = preset[i]
        print(f"Applied ratio preset {self.selectedRatioPreset + 1}")

    def reset_to_defaults(self):
        """Resets all settings to their default values."""
        # Reset motor settings
        self.wheelSpeeds = [self.DEFAULT_SPEED_RATIO] * self.MOTORS_COUNT
        self.lfoDepths = [self.DEFAULT_LFO_DEPTH] * self.MOTORS_COUNT
        self.lfoRates = [self.DEFAULT_LFO_RATE] * self.MOTORS_COUNT
        self.lfoPolarities = [self.DEFAULT_LFO_POLARITY] * self.MOTORS_COUNT
        self.masterTime = self.DEFAULT_MASTER_TIME
        self.currentMicrostepMode = self.DEFAULT_MICROSTEP
        
        # Reset menu state variables
        self.currentMenu = self.MENU_MAIN
        self.selectedMainMenuOption = 0
        self.selectedSpeedWheel = 0
        self.selectedLfoParam = 0
        self.selectedRatioPreset = 0
        self.selectedMicrostepIndex = 4  # Default to 16x microstepping index
        self.pendingMicrostepMode = self.DEFAULT_MICROSTEP
        
        # Reset state flags
        self.editingSpeed = False
        self.editingLfo = False
        self.editingMaster = False
        self.editingMicrostep = False
        self.confirmingRatio = False
        self.confirmingReset = False
        self.systemPaused = False
        
        print("All motor settings reset to defaults")

    def update_display(self):
        """Updates the LCD display based on current menu and state."""
        line1 = ""
        line2 = ""
        
        if self.systemPaused:
            line1 = "** SYSTEM **"
            line2 = "*** PAUSED ***"
        
        elif self.currentMenu == self.MENU_MAIN:
            # Get main menu option names
            options = ["SPEED", "LFO", "RATIO", "MASTER", "STEP", "RESET"]
            selected = options[self.selectedMainMenuOption]
            
            # Calculate previous and next options for display
            prev = (self.selectedMainMenuOption + 5) % 6
            next = (self.selectedMainMenuOption + 1) % 6
            next2 = (self.selectedMainMenuOption + 2) % 6
            
            line1 = f">{selected}"
            line2 = f" {options[prev]} {options[next]} {options[next2]}"
        
        elif self.currentMenu == self.MENU_SPEED:
            wheel_label = self.wheelLabels[self.selectedSpeedWheel]
            
            if self.editingSpeed:
                line1 = f"SPEED: {wheel_label}#"
            else:
                line1 = f"SPEED: {wheel_label}"
            
            line2 = f"Value: {self.wheelSpeeds[self.selectedSpeedWheel]:05.1f}"
        
        elif self.currentMenu == self.MENU_LFO:
            wheel_index = self.selectedLfoParam // 3
            param_type = self.selectedLfoParam % 3
            wheel_label = self.wheelLabels[wheel_index]
            
            param_names = ["DPT", "RTE", "POL"]
            param_name = param_names[param_type]
            
            if self.editingLfo:
                line1 = f"LFO: {wheel_label} {param_name}#"
            else:
                line1 = f"LFO: {wheel_label} {param_name}"
            
            if param_type == 0:  # Depth
                line2 = f"Value: {self.lfoDepths[wheel_index]:05.1f}%"
            elif param_type == 1:  # Rate
                line2 = f"Value: {self.lfoRates[wheel_index]:05.1f}"
            else:  # Polarity
                line2 = f"Value: {'BI' if self.lfoPolarities[wheel_index] else 'UNI'}"
        
        elif self.currentMenu == self.MENU_RATIO:
            if self.confirmingRatio:
                line1 = "Apply Preset?"
                
                # Show ratios from the preset
                preset = self.RATIO_PRESETS[self.selectedRatioPreset]
                ratio_str = ":".join([f"{r:.1f}" for r in preset])
                line2 = f"P{self.selectedRatioPreset + 1}: {ratio_str}"
                
                if self.ratioChoice:
                    line2 = " NO   >YES"
                else:
                    line2 = ">NO    YES"
            else:
                line1 = "Select Ratio"
                line2 = f"Preset {self.selectedRatioPreset + 1}"
        
        elif self.currentMenu == self.MENU_MASTER:
            if self.editingMaster:
                line1 = "MASTER TIME:#"
            else:
                line1 = "MASTER TIME:"
            
            # Format master time in seconds
            line2 = f"Value: {self.masterTime/1000.0:06.2f} S"
        
        elif self.currentMenu == self.MENU_MICROSTEP:
            if self.editingMicrostep:
                line1 = "MICROSTEP:#"
                line2 = f"Value: {self.pendingMicrostepMode}x"
            else:
                line1 = "MICROSTEP:"
                line2 = f"Value: {self.currentMicrostepMode}x"
        
        elif self.currentMenu == self.MENU_RESET:
            if self.confirmingReset:
                line1 = "RESET TO DEFLT?"
                if self.resetChoice:
                    line2 = " NO   >YES"
                else:
                    line2 = ">NO    YES"
            else:
                line1 = "RESET"
                line2 = "Press to confirm"
        
        # Pad lines to LCD width
        line1 = line1.ljust(self.LCD_COLS)[:self.LCD_COLS]
        line2 = line2.ljust(self.LCD_COLS)[:self.LCD_COLS]
        
        # Update LCD display
        self.lcd_line1.config(text=line1)
        self.lcd_line2.config(text=line2)


def main():
    """Main function to run the simulator."""
    root = tk.Tk()
    root.resizable(False, False)
    app = CycloidMenuSimulator(root)
    root.mainloop()


if __name__ == "__main__":
    main() 