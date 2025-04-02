import tkinter as tk

class LCDMenuSimulator:
    """
    Simulates an LCD menu system controlled by a rotary encoder.
    """

    def __init__(self, root):
        """
        Initializes the menu system with variables, initial display, and GUI elements.
        """
        self.root = root
        self.root.title("LCD Menu Simulator")

        # Initialize variables
        self.menu_options = ["SPEED", "LFO", "RATIO", "MASTER"]
        self.current_menu = "MAIN"  # MAIN, SPEED, LFO, RATIO, MASTER
        self.selected_option = 0  # Index of the selected menu option
        self.wheel_speeds = [100.0, 100.0, 100.0, 100.0]  # X, Y, Z, A
        self.lfo_rates = [1.0, 1.0, 1.0, 1.0]
        self.lfo_depths = [0.0, 0.0, 0.0, 0.0]
        self.selected_wheel = 0
        self.editing_speed = False
        self.selected_param = 0  # 0-7: X_DEPTH, X_RATE, Y_DEPTH, Y_RATE, ...
        self.editing_lfo = False
        self.system_paused = False
        self.encoder_value = 0  # Keep track of encoder value

        # Ratio Menu Specific
        self.ratios = [
            [100, 100, 100, 100],
            [50, 100, 150, 200],
            [200, 150, 100, 50],
            [75, 125, 175, 225],
        ]
        self.selected_ratio_index = 0
        self.applying_ratio = False  # State for APPLY? Y/N
        self.apply_choice = 0  # 0: No, 1: Yes

        # Create GUI elements
        self.display_label = tk.Label(root, text="", font=("Courier", 12), justify=tk.LEFT)
        self.display_label.pack(pady=10)

        button_frame = tk.Frame(root)
        button_frame.pack()

        self.click_button = tk.Button(button_frame, text="Click", command=self.handle_button_short_press)
        self.click_button.pack(side=tk.LEFT, padx=5)
        self.long_button = tk.Button(button_frame, text="Long Press", command=self.handle_button_long_press)
        self.long_button.pack(side=tk.LEFT, padx=5)
        self.cw_button = tk.Button(button_frame, text="CW", command=self.handle_encoder_cw)
        self.cw_button.pack(side=tk.LEFT, padx=5)
        self.ccw_button = tk.Button(button_frame, text="CCW", command=self.handle_encoder_ccw)
        self.ccw_button.pack(side=tk.LEFT, padx=5)

        self.update_display()  # Initial display

    def handle_encoder_cw(self):
        """Simulates turning the encoder clockwise."""
        self.handle_encoder(1)

    def handle_encoder_ccw(self):
        """Simulates turning the encoder counter-clockwise."""
        self.handle_encoder(-1)

    def handle_encoder(self, increment):
        """
        Simulates the rotary encoder input.

        Args:
            increment: The amount the encoder value has changed.
        """
        self.encoder_value += increment

        if self.current_menu == "MAIN":
            self.selected_option = (self.selected_option + increment) % len(self.menu_options)
        elif self.current_menu == "SPEED":
            if self.editing_speed:
                self.wheel_speeds[self.selected_wheel] += increment * 1.0
                self.wheel_speeds[self.selected_wheel] = max(min(self.wheel_speeds[self.selected_wheel], 256.0), -256.0)
            else:
                self.selected_wheel = (self.selected_wheel + increment) % 4
        elif self.current_menu == "LFO":
            if self.editing_lfo:
                if self.selected_param % 2 == 0:  # Even: Depth
                    self.lfo_depths[self.selected_param // 2] += increment * 0.01
                    self.lfo_depths[self.selected_param // 2] = max(min(self.lfo_depths[self.selected_param // 2], 1.0), 0.0)
                else:  # Odd: Rate
                    self.lfo_rates[self.selected_param // 2] += increment * 0.1
                    self.lfo_rates[self.selected_param // 2] = max(min(self.lfo_rates[self.selected_param // 2], 10.0), 0.1)
            else:
                self.selected_param = (self.selected_param + increment) % 8
        elif self.current_menu == "MASTER":
            self.master_speed += increment * 0.01
            self.master_speed = max(min(self.master_speed, 2.0), 0.0)
        elif self.current_menu == "RATIO":
            if self.applying_ratio:
                self.apply_choice = (self.apply_choice + increment) % 2
            else:
                self.selected_ratio_index = (self.selected_ratio_index + increment) % len(self.ratios)
        self.update_display()

    def handle_button_short_press(self):
        """
        Simulates a short press of the encoder button.
        """
        if self.current_menu == "MAIN":
            self.current_menu = self.menu_options[self.selected_option]
            if self.current_menu == "SPEED":
                self.selected_wheel = 0
                self.editing_speed = False
            elif self.current_menu == "LFO":
                self.selected_param = 0
                self.editing_lfo = False
            elif self.current_menu == "RATIO":
                self.applying_ratio = True
                self.apply_choice = 0
        elif self.current_menu == "SPEED":
            if self.editing_speed:
                self.editing_speed = False
            else:
                self.editing_speed = True
        elif self.current_menu == "LFO":
            if self.editing_lfo:
                self.editing_lfo = False
            else:
                self.editing_lfo = True
        elif self.current_menu == "MASTER":
            self.current_menu = "MAIN"
        elif self.current_menu == "RATIO":
            if self.applying_ratio:
                if self.apply_choice == 1:
                    self.wheel_speeds = self.ratios[self.selected_ratio_index]
                    self.current_menu = "MAIN"
                else:
                    self.applying_ratio = False
            else:
                self.current_menu = "MAIN"
        self.update_display()

    def handle_button_long_press(self):
        """
        Simulates a long press of the encoder button.
        """
        if self.current_menu == "MAIN":
            self.system_paused = not self.system_paused
        else:
            self.current_menu = "MAIN"
        self.update_display()

    def update_display(self):
        """
        Simulates updating the LCD display based on the current screen.
        """
        display_text = ""
        if self.system_paused:
            display_text = "System Paused   *"
        elif self.current_menu == "MAIN":
            display_text = ""
            for i, option in enumerate(self.menu_options):
                if i == self.selected_option:
                    display_text += ">"
                display_text += option + " "
            display_text = display_text[:16]
        elif self.current_menu == "SPEED":
            display_text = "WHEEL SPEED\n"
            display_text += ["X:", "Y:", "Z:", "A:"][self.selected_wheel]
            display_text += f"{self.wheel_speeds[self.selected_wheel]:.2f}"
            if self.editing_speed:
                display_text += "#"
            display_text = display_text[:16]
        elif self.current_menu == "LFO":
            if not self.editing_lfo:
                if self.selected_param % 2 == 0:
                    display_text = "X DEPTH: " if self.selected_param == 0 else "Y DEPTH: " if self.selected_param == 2 else "Z DEPTH: " if self.selected_param == 4 else "A DEPTH: "
                    display_text += f"{self.lfo_depths[self.selected_param // 2]:.2f}#"
                else:
                    display_text = "X RATE: " if self.selected_param == 1 else "Y RATE: " if self.selected_param == 3 else "Z RATE: " if self.selected_param == 5 else "A RATE: "
                    display_text += f"{self.lfo_rates[self.selected_param // 2]:.3f}#"
                display_text = display_text[:16]
            else:
                if self.selected_param % 2 == 0:
                    display_text = "LFO DEPTH\n"
                    display_text += ["X:", "X:", "Y:", "Y:", "Z:", "Z:", "A:", "A:"][self.selected_param]
                    display_text += f"{self.lfo_depths[self.selected_param // 2]:.2f}#"
                    display_text = display_text[:16]
                else:
                    display_text = "LFO RATE\n"
                    display_text += ["X:", "X:", "Y:", "Y:", "Z:", "Z:", "A:", "A:"][self.selected_param]
                    display_text += f"{self.lfo_rates[self.selected_param // 2]:.3f}#"
                    display_text = display_text[:16]
        elif self.current_menu == "MASTER":
            display_text = "Master Speed\n"
            display_text += f"{self.master_speed * 100:.0f}%"
            display_text = display_text[:16]
        elif self.current_menu == "RATIO":
            if not self.applying_ratio:
                display_text = "RATIO SET\n"
                display_text += f"1:{self.ratios[self.selected_ratio_index][0]}, 2:{self.ratios[self.selected_ratio_index][1]}\n"
                display_text += f"3:{self.ratios[self.selected_ratio_index][2]}, 4:{self.ratios[self.selected_ratio_index][3]}"
                display_text = display_text[:32]
            else:
                display_text = "APPLY: "
                display_text += "Y#" if self.apply_choice == 1 else "N#"
                display_text = display_text[:16]
        self.display_label.config(text=display_text)

def main():
    """
    Main function to run the LCD Menu Simulator.
    """
    root = tk.Tk()
    menu_simulator = LCDMenuSimulator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
