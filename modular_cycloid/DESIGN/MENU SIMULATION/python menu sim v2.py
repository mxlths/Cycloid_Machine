import tkinter as tk

class LCDMenuSimulator16x2:
    """
    Simulates the 16x2 LCD menu system based on MENU SYSTEM DESCRIPTION.
    Handles rotary encoder inputs (CW, CCW, Short Press, Long Press)
    and updates a simulated 16x2 display.
    """

    # --- Constants ---
    MENU_MAIN = "MAIN"
    MENU_SPEED = "SPEED"
    MENU_LFO = "LFO"
    MENU_RATIO = "RATIO"
    MENU_MASTER = "MASTER"
    MENU_RESET = "RESET"

    WHEEL_LABELS = ["X", "Y", "Z", "A"]
    LFO_PARAM_TYPES = ["DPT", "RTE", "POL"] # Depth, Rate, Polarity
    POLARITY_OPTIONS = ["UNI", "BI"]
    YES_NO = ["NO", "YES"]

    # --- Defaults ---
    DEFAULT_WHEEL_SPEEDS = [10.0, 10.0, 10.0, 10.0]
    DEFAULT_LFO_DEPTHS = [0.0, 0.0, 0.0, 0.0]
    DEFAULT_LFO_RATES = [0.0, 0.0, 0.0, 0.0]
    DEFAULT_LFO_POLARITIES = [0, 0, 0, 0] # 0 for UNI, 1 for BI
    DEFAULT_MASTER_TIME = 1.00

    def __init__(self, root):
        """
        Initializes the simulator state, GUI, and default values.
        """
        self.root = root
        self.root.title("16x2 LCD Menu Simulator")

        # ---- Menu State ----
        self.menu_options = [self.MENU_SPEED, self.MENU_LFO, self.MENU_RATIO, self.MENU_MASTER, self.MENU_RESET]
        self.current_menu = self.MENU_MAIN
        self.selected_main_option_index = 0

        # ---- SPEED ----
        self.wheel_speeds = list(self.DEFAULT_WHEEL_SPEEDS)
        self.selected_speed_wheel_index = 0
        self.editing_speed = False

        # ---- LFO ----
        self.lfo_depths = list(self.DEFAULT_LFO_DEPTHS)
        self.lfo_rates = list(self.DEFAULT_LFO_RATES)
        self.lfo_polarities = list(self.DEFAULT_LFO_POLARITIES) # 0=UNI, 1=BI
        self.selected_lfo_param_index = 0 # 0-11 (X_DPT, X_RTE, X_POL, Y_DPT...)
        self.editing_lfo = False

        # ---- RATIO ----
        self.ratios = [
            [100, 100, 100, 100],
            [ 50, 100, 150, 200],
            [200, 150, 100,  50],
            [ 75, 125, 175, 225],
        ]
        self.selected_ratio_index = 0
        self.confirming_ratio_apply = False
        self.ratio_apply_choice = 0 # 0=NO, 1=YES

        # ---- MASTER ----
        self.master_time = self.DEFAULT_MASTER_TIME
        self.editing_master = False

        # ---- RESET ----
        self.confirming_reset = False # Added state for RESET confirmation
        self.reset_choice = 0 # 0=NO, 1=YES

        # ---- System State ----
        self.system_paused = False

        # ---- GUI Elements ----
        # Use Courier font for fixed width, vital for 16x2 simulation
        self.display_label = tk.Label(root, text="", font=("Courier", 14), justify=tk.LEFT, width=16, height=2, anchor='nw', borderwidth=2, relief="groove")
        self.display_label.pack(pady=10, padx=10)

        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)

        self.cw_button = tk.Button(button_frame, text="CW", command=self.handle_encoder_cw, width=8)
        self.cw_button.grid(row=0, column=0, padx=5)

        self.ccw_button = tk.Button(button_frame, text="CCW", command=self.handle_encoder_ccw, width=8)
        self.ccw_button.grid(row=0, column=1, padx=5)

        self.short_press_button = tk.Button(button_frame, text="Short Press", command=self.handle_button_short_press, width=10)
        self.short_press_button.grid(row=1, column=0, padx=5, pady=5)

        self.long_press_button = tk.Button(button_frame, text="Long Press", command=self.handle_button_long_press, width=10)
        self.long_press_button.grid(row=1, column=1, padx=5, pady=5)

        # Initial display update
        self.update_display()

    # --- Input Handlers ---
    def handle_encoder_cw(self):
        self._handle_encoder(1)

    def handle_encoder_ccw(self):
        self._handle_encoder(-1)

    def _handle_encoder(self, increment):
        """Internal logic for encoder turns."""
        if self.system_paused: return # No action when paused

        if self.current_menu == self.MENU_MAIN:
            self.selected_main_option_index = (self.selected_main_option_index + increment) % len(self.menu_options)

        elif self.current_menu == self.MENU_SPEED:
            if self.editing_speed:
                current_val = self.wheel_speeds[self.selected_speed_wheel_index]
                new_val = round(current_val + increment * 0.1, 1)
                # Ensure value stays within 0.0 to 256.0
                self.wheel_speeds[self.selected_speed_wheel_index] = max(0.0, min(256.0, new_val))
            else:
                self.selected_speed_wheel_index = (self.selected_speed_wheel_index + increment) % 4

        elif self.current_menu == self.MENU_LFO:
            if self.editing_lfo:
                wheel_idx = self.selected_lfo_param_index // 3
                param_type_idx = self.selected_lfo_param_index % 3

                if param_type_idx == 0: # Depth
                    current_val = self.lfo_depths[wheel_idx]
                    new_val = round(current_val + increment * 0.1, 1)
                    # Ensure value stays within 0.0 to 100.0
                    self.lfo_depths[wheel_idx] = max(0.0, min(100.0, new_val))
                elif param_type_idx == 1: # Rate
                    current_val = self.lfo_rates[wheel_idx]
                    new_val = round(current_val + increment * 0.1, 1)
                    # Ensure value stays within 0.0 to 256.0
                    self.lfo_rates[wheel_idx] = max(0.0, min(256.0, new_val))
                else: # Polarity
                    # Incrementing/decrementing toggles between 0 and 1
                    self.lfo_polarities[wheel_idx] = 1 - self.lfo_polarities[wheel_idx]
            else:
                self.selected_lfo_param_index = (self.selected_lfo_param_index + increment) % 12 # Total 12 LFO params

        elif self.current_menu == self.MENU_RATIO:
            if self.confirming_ratio_apply:
                self.ratio_apply_choice = (self.ratio_apply_choice + increment) % 2 # Toggle 0/1
            else:
                self.selected_ratio_index = (self.selected_ratio_index + increment) % len(self.ratios)

        elif self.current_menu == self.MENU_MASTER:
            if self.editing_master:
                current_val = self.master_time
                new_val = round(current_val + increment * 0.01, 2)
                # Ensure value stays within 0.01 to 999.99
                self.master_time = max(0.01, min(999.99, new_val))
            # No action if not editing master

        elif self.current_menu == self.MENU_RESET:
             if self.confirming_reset: # Only change choice when confirming
                self.reset_choice = (self.reset_choice + increment) % 2 # Toggle 0/1

        self.update_display()

    def handle_button_short_press(self):
        """Handles short press actions based on context."""
        if self.system_paused: return # No action when paused

        if self.current_menu == self.MENU_MAIN:
            # Enter selected submenu
            self.current_menu = self.menu_options[self.selected_main_option_index]
            # Reset submenu states/selections for clean entry
            if self.current_menu == self.MENU_SPEED:
                self.selected_speed_wheel_index = 0
                self.editing_speed = False
            elif self.current_menu == self.MENU_LFO:
                self.selected_lfo_param_index = 0
                self.editing_lfo = False
            elif self.current_menu == self.MENU_RATIO:
                # Short press enters ratio select, doesn't confirm apply yet
                self.confirming_ratio_apply = False # Start in selection mode
                # Keep self.selected_ratio_index
            elif self.current_menu == self.MENU_MASTER:
                self.editing_master = True # Enter edit mode directly
            elif self.current_menu == self.MENU_RESET:
                self.confirming_reset = True # Enter confirmation mode
                self.reset_choice = 0 # Default NO

        elif self.current_menu == self.MENU_SPEED:
            # Toggle editing mode
            self.editing_speed = not self.editing_speed

        elif self.current_menu == self.MENU_LFO:
            # Toggle editing mode
            self.editing_lfo = not self.editing_lfo

        elif self.current_menu == self.MENU_RATIO:
            if not self.confirming_ratio_apply:
                 # Enter confirmation screen from ratio selection
                 self.confirming_ratio_apply = True
                 self.ratio_apply_choice = 0 # Default NO
            else:
                # Handle YES/NO confirmation
                if self.ratio_apply_choice == 1: # YES
                    # Apply ratio
                    selected_set = self.ratios[self.selected_ratio_index]
                    for i in range(4):
                        # Ensure applied ratios are within speed bounds
                        self.wheel_speeds[i] = max(0.0, min(256.0, float(selected_set[i])))
                    self.confirming_ratio_apply = False # Exit confirmation
                    self.current_menu = self.MENU_MAIN # Return to main
                else: # NO
                    # Exit confirmation, stay in RATIO select
                    self.confirming_ratio_apply = False
                    # Stay in ratio menu for selecting another preset


        elif self.current_menu == self.MENU_MASTER:
            # Short press toggles editing state
            self.editing_master = not self.editing_master
            # If exiting edit mode, stay in MASTER menu viewing the value

        elif self.current_menu == self.MENU_RESET:
             if self.confirming_reset:
                if self.reset_choice == 1: # YES
                    self._reset_defaults()
                    self.confirming_reset = False
                    self.current_menu = self.MENU_MAIN # Return to main
                else: # NO
                    self.confirming_reset = False
                    self.current_menu = self.MENU_MAIN # Return to main without reset
             # If not confirming, short press does nothing

        self.update_display()

    def handle_button_long_press(self):
        """Handles long press actions: return or pause."""
        if self.current_menu == self.MENU_MAIN:
            self.system_paused = not self.system_paused
        else:
            # Return to MAIN menu from any submenu/state
            # Reset potentially active editing/confirmation states
            self.editing_speed = False
            self.editing_lfo = False
            self.editing_master = False
            self.confirming_ratio_apply = False
            self.confirming_reset = False
            self.current_menu = self.MENU_MAIN
            # Keep main menu selection (self.selected_main_option_index) as it was

        self.update_display()

    def _reset_defaults(self):
        """Resets all parameters to their default values."""
        self.wheel_speeds = list(self.DEFAULT_WHEEL_SPEEDS)
        self.lfo_depths = list(self.DEFAULT_LFO_DEPTHS)
        self.lfo_rates = list(self.DEFAULT_LFO_RATES)
        self.lfo_polarities = list(self.DEFAULT_LFO_POLARITIES)
        self.master_time = self.DEFAULT_MASTER_TIME
        # Optionally reset selections as well
        self.selected_speed_wheel_index = 0
        self.selected_lfo_param_index = 0
        self.selected_ratio_index = 0
        print("System Reset to Defaults") # Console feedback for verification

    # --- Display Logic ---\
    def format_line(self, text):
        """Pads or truncates text to exactly 16 characters."""
        return text.ljust(16)[:16]

    def update_display(self):
        """Formats and updates the 16x2 display label."""
        line1 = ""
        line2 = ""

        if self.system_paused:
            line1 = self.format_line("** SYSTEM **")
            line2 = self.format_line("*** PAUSED ***")

        elif self.current_menu == self.MENU_MAIN:
            selected_name = self.menu_options[self.selected_main_option_index]
            line1 = self.format_line(f">{selected_name}")
            # Dynamically generate the second line with subsequent options
            options_display = []
            for i in range(1, len(self.menu_options)):
                idx = (self.selected_main_option_index + i) % len(self.menu_options)
                options_display.append(self.menu_options[idx][:4]) # Abbreviate if needed
            line2 = self.format_line(" ".join(options_display))


        elif self.current_menu == self.MENU_SPEED:
            wheel_label = self.WHEEL_LABELS[self.selected_speed_wheel_index]
            edit_char = "#" if self.editing_speed else ""
            line1 = self.format_line(f"SPEED: {wheel_label}{edit_char}")
            # Format 000.0 (5 chars total)
            value_str = f"{self.wheel_speeds[self.selected_speed_wheel_index]:05.1f}"
            line2 = self.format_line(f"Value: {value_str:>7}") # Right align value in 7 spaces

        elif self.current_menu == self.MENU_LFO:
            wheel_idx = self.selected_lfo_param_index // 3
            param_type_idx = self.selected_lfo_param_index % 3
            wheel_label = self.WHEEL_LABELS[wheel_idx]
            param_label = self.LFO_PARAM_TYPES[param_type_idx]
            edit_char = "#" if self.editing_lfo else ""

            line1 = self.format_line(f">LFO: {wheel_label} {param_label}{edit_char}") # Add > to show selection

            if param_type_idx == 0: # Depth
                 # Format 000.0 (5 chars total)
                 value_str = f"{self.lfo_depths[wheel_idx]:05.1f}"
                 line2 = self.format_line(f"Value: {value_str:>7}")
            elif param_type_idx == 1: # Rate
                 # Format 000.0 (5 chars total)
                 value_str = f"{self.lfo_rates[wheel_idx]:05.1f}"
                 line2 = self.format_line(f"Value: {value_str:>7}")
            else: # Polarity
                value_str = self.POLARITY_OPTIONS[self.lfo_polarities[wheel_idx]]
                line2 = self.format_line(f"Value: {value_str:>7}")

        elif self.current_menu == self.MENU_RATIO:
            if self.confirming_ratio_apply:
                line1 = self.format_line("APPLY RATIO?")
                no_select = ">" if self.ratio_apply_choice == 0 else " "
                yes_select = ">" if self.ratio_apply_choice == 1 else " "
                line2 = self.format_line(f"{no_select}NO    {yes_select}YES")
            else:
                line1 = self.format_line(f">RATIO PRESET: {self.selected_ratio_index + 1}") # Add >
                r = self.ratios[self.selected_ratio_index]
                # Format ratios compactly: remove decimals if whole numbers
                ratio_str = ":".join([f"{val:g}" for val in r])
                line2 = self.format_line(ratio_str)

        elif self.current_menu == self.MENU_MASTER:
            edit_char = "#" if self.editing_master else ""
            line1 = self.format_line(f">MASTER TIME:{edit_char}") # Add >
            # Format 001.00 (6 chars total)
            value_str = f"{self.master_time:06.2f}"
            line2 = self.format_line(f"Value: {value_str} S")

        elif self.current_menu == self.MENU_RESET:
             if self.confirming_reset:
                 line1 = self.format_line("RESET TO DEFLT?")
                 no_select = ">" if self.reset_choice == 0 else " "
                 yes_select = ">" if self.reset_choice == 1 else " "
                 line2 = self.format_line(f"{no_select}NO    {yes_select}YES")
             else:
                 # Should not happen if short press always enters confirmation
                 line1 = self.format_line(">RESET")
                 line2 = self.format_line("Press Short")


        # Combine lines and update the label, ensuring newline separation
        display_content = f"{line1}\n{line2}"
        self.display_label.config(text=display_content)


def main():
    """Sets up the Tkinter window and runs the simulator."""
    root = tk.Tk()
    # Prevent resizing, as layout is fixed for 16x2 simulation
    root.resizable(False, False)
    app = LCDMenuSimulator16x2(root)
    root.mainloop()

if __name__ == "__main__":
    main()