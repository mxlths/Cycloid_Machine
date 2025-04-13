import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow
from main_window import MainWindow  # Assuming MainWindow is in main_window.py
# Removed component imports - no longer needed here
# from components import Wheel, Rod 
# Import config loader only
from config_loader import MachineConfig, load_config_from_xml 
# Removed canvas import - no longer needed here
# from drawing_canvas import DrawingCanvas 
# Removed typing helpers - no longer needed here
# from typing import Dict, List, Tuple 
# Removed QPointF import - no longer needed here
# from PyQt6.QtCore import QPointF 

# Function moved to config_loader.py
# def populate_canvas_from_config(canvas: DrawingCanvas, config: MachineConfig):
#    ...

def main():
    app = QApplication(sys.argv)
    
    # --- Load Configuration --- 
    # Get the directory where main.py resides
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to config.xml relative to the script's parent directory
    config_file = os.path.join(script_dir, '..', 'config.xml')
    
    # Load the actual config file
    try:
        machine_config = load_config_from_xml(config_file)
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        # Optionally show an error dialog
        sys.exit(1) # Exit if config fails
    # --------------------------
    
    # Pass the loaded config path to MainWindow
    main_win = MainWindow(initial_config_path=config_file)
    
    # --- Populate Canvas --- 
    # Call the function from config_loader now
    from config_loader import populate_canvas_from_config
    populate_canvas_from_config(main_win.canvas, machine_config)
    # -----------------------
    
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 