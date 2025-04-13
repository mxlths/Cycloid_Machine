from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QFrame,
                               QFileDialog)
from PyQt6.QtCore import Qt, QSize, QPointF, QObject, QEvent
from PyQt6.QtGui import QAction
from drawing_canvas import DrawingCanvas
from parameter_panel import ParameterPanel
from components import Wheel, Rod
from typing import Optional, Union, Dict
from PyQt6.QtWidgets import QApplication
import math
import xml.etree.ElementTree as ET
import os

# Import the config writer and loader
from config_writer import generate_xml_tree, prettify_xml 
# Import loader functions and populate function from config_loader
from config_loader import load_config_from_xml, MachineConfig, populate_canvas_from_config
# Import the SymPy solver function
from sympy_solver import calculate_path_sympy

class MainWindow(QMainWindow):
    def __init__(self, initial_config_path: Optional[str] = None):
        super().__init__()
        self.current_config_path: Optional[str] = initial_config_path
        window_title = "Cycloid Machine Simulator"
        if self.current_config_path:
            window_title += f" - {os.path.basename(self.current_config_path)}"
        else:
            window_title += " - New Configuration"
        self.setWindowTitle(window_title)
        
        self.setMinimumSize(QSize(800, 800))
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Create parameter panel (left side)
        self.parameter_panel = ParameterPanel()
        main_layout.addWidget(self.parameter_panel)
        
        # Create drawing canvas (center)
        self.canvas = DrawingCanvas()
        main_layout.addWidget(self.canvas)
        
        # Set fixed width for the parameter panel (240px * 1.2 = 288px)
        self.parameter_panel.setFixedWidth(288)
        
        # Create status bar
        self.statusBar().showMessage("Ready")
        
        # Setup menu bar
        self._setup_menu_bar()
        
        # Connect signals
        self._connect_signals()
        
        # Set canvas as focus proxy <-- Try disabling this
        # self.setFocusProxy(self.canvas) # <<-- COMMENTED OUT
        self.canvas.setFocus() # Still give canvas initial focus
        
        # Temporarily disable event filter for debugging QLineEdit input
        # print("Installing event filter")
        self.installEventFilter(self) # <<-- RE-ENABLED
        
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events to handle arrow keys globally, but allow panel input."""
        if event.type() == QEvent.Type.KeyPress and \
           event.key() in [Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down]:
            
            # Check if the ParameterPanel or one of its children has focus
            panel_has_focus = False
            focus_widget = QApplication.focusWidget() # Use QApplication to get global focus
            if focus_widget:
                # Check if focus widget is the panel or a descendant of the panel
                widget = focus_widget
                while widget is not None:
                    if widget == self.parameter_panel:
                        panel_has_focus = True
                        break
                    widget = widget.parentWidget()
            
            # If panel has focus, don't interfere, let the panel handle the key press
            if panel_has_focus:
                # print("EventFilter: Panel has focus, ignoring arrow key.") # Debug
                return False # Let the event propagate to the focused widget (QLineEdit)
            
            # Otherwise, if canvas has a selected component, let canvas handle arrow keys for nudging
            elif self.canvas.selected_component:
                # print("EventFilter: Panel lacks focus, canvas selected, redirecting arrow key to canvas.") # Debug
                self.canvas.setFocus()
                # Let canvas handle its key press, but filter might need adjustment
                # self.canvas.keyPressEvent(event) # Directly calling might bypass canvas filters
                # Instead, let the normal event loop handle it after setting focus
                return False # Let event propagate to canvas now that it has focus
                
        # Let other events pass through
        return super(MainWindow, self).eventFilter(obj, event)

    def _setup_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_action = QAction('Open...', self)
        # Connect open_action to handler
        open_action.triggered.connect(self._handle_open)
        file_menu.addAction(open_action)
        
        save_action = QAction('Save', self)
        save_action.triggered.connect(self._handle_save)
        file_menu.addAction(save_action)
        
        save_as_action = QAction('Save As && New...', self)
        save_as_action.triggered.connect(self._handle_save_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        # Add view menu actions here
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        # Add help menu actions here
        
    def _connect_signals(self):
        # Connect snap changed signal
        self.parameter_panel.snap_changed.connect(self._on_snap_changed)
        
        # Connect add wheel button
        self.parameter_panel._add_wheel_button.clicked.connect(self._on_add_wheel)
        
        # Connect add canvas button
        self.parameter_panel.add_canvas_requested.connect(self._on_add_canvas)
        
        # Connect add rod request signal to canvas start_rod_creation
        self.parameter_panel.add_rod_requested.connect(self.canvas.start_rod_creation)
        
        # Connect canvas component selection signal
        self.canvas.component_selected.connect(self._on_component_selected)
        
        # Connect parameter panel change signal
        self.parameter_panel.parameter_changed.connect(self._on_parameter_changed)
        
        # Connect pen assignment signal
        self.parameter_panel.pen_assigned.connect(self._handle_pen_assignment)
        
        # Connect simulation control signals
        self.parameter_panel.start_simulation_requested.connect(self.canvas.start_simulation)
        self.parameter_panel.stop_simulation_requested.connect(self.canvas.stop_simulation)
        
        # Connect image generation signal
        self.parameter_panel.image_generate_requested.connect(self._on_generate_image)
        
    def _on_snap_changed(self, snap_value: int):
        """Handle snap setting changes"""
        print(f"MainWindow received snap change: {snap_value}mm")  # Debug print
        self.canvas.set_snap_size(snap_value)
        self.statusBar().showMessage(f"Grid snap set to {snap_value}mm")
        self.canvas.repaint()
        
    def _on_add_wheel(self):
        """Handle adding a new wheel"""
        # For now, add a wheel at a default position with default size
        center = QPointF(200, 200)
        diameter = 100.0
        new_wheel = self.canvas.add_wheel(center, diameter)
        
        if new_wheel:
            # Select the newly added wheel
            self.canvas.selected_component = new_wheel
            new_wheel.selected = True
            # Emit signal from canvas to update parameter panel
            self.canvas.component_selected.emit(new_wheel)
            self.canvas.update()
            self.statusBar().showMessage(f"Added new wheel (ID: {new_wheel.id})")
        else:
             self.statusBar().showMessage("Failed to add wheel.", 3000)

        self.canvas.setFocus()  # Ensure canvas has focus after adding wheel
        # self.statusBar().showMessage("Added new wheel") # Old message
        
    def _on_component_selected(self, component: Optional[Union[Wheel, Rod]]):
        """Handle component selection changes from the canvas."""
        print(f"DEBUG: MainWindow._on_component_selected called with: {component}")
        if component is None:
            # print("MainWindow received: No component selected") # Removed Debug
            self.parameter_panel.clear_details()
        elif isinstance(component, Wheel):
            # print(f"MainWindow received: Wheel selected - {component}") # Removed Debug
            # Pass the components dictionary when showing wheel details too (might be useful later)
            self.parameter_panel.show_wheel_details(component, self.canvas.components_by_id)
        elif isinstance(component, Rod):
            # print(f"MainWindow received: Rod selected - {component}") # Removed Debug
            # Pass the components dictionary when showing rod details
            self.parameter_panel.show_rod_details(component, self.canvas.components_by_id)
        else:
            # print(f"MainWindow received: Unknown component type selected - {type(component)}") # Removed Debug
            self.parameter_panel.clear_details()
            
    def _on_parameter_changed(self, component: Union[Wheel, Rod], param_name: str, new_value: object):
        """Handle parameter changes submitted from the ParameterPanel."""
        # print(f"MainWindow received parameter change: Comp={type(component)}, Param='{param_name}', Value={new_value} (Type: {type(new_value)})") # Removed Debug
        
        try:
            if isinstance(component, Wheel):
                if param_name == 'diameter':
                    component.diameter = float(new_value)
                elif param_name == 'center_x':
                    # Keep y, update x
                    component.center.setX(float(new_value))
                elif param_name == 'center_y':
                    # Keep x, update y
                    component.center.setY(float(new_value))
                elif param_name == 'speed_ratio':
                    component.speed_ratio = float(new_value)
                elif param_name == 'rotation_rate':
                    component.rotation_rate = float(new_value)
                elif param_name == 'p1_radius':
                    # Update radius of the specific connection point 'p1'
                    if 'p1' in component.connection_points:
                        new_radius = float(new_value)
                        # Ensure non-negative radius
                        component.connection_points['p1'].radius = max(0.0, new_radius)
                        # Update UI if clamped
                        if new_radius < 0:
                             if 'p1_radius' in self.parameter_panel.detail_widgets:
                                self.parameter_panel.detail_widgets['p1_radius'].setValue(0.0)
                    else:
                        print("Warning: Tried to set p1_radius, but point 'p1' does not exist.")
            
            elif isinstance(component, Rod):
                # For rods, changing positions might affect length unless handled carefully
                # Current implementation: change position, length might change
                # TODO: Decide if length should be constrained or recalculated when positions change via panel
                if param_name == 'length':
                     # Changing length directly is tricky - which end moves?
                     # For now, let's make length read-only from panel, or update it based on end points
                     print("Note: Setting rod length directly from panel is not implemented yet.")
                     # component.length = float(new_value)
                     # Need logic to move one end based on the length change
                elif param_name == 'start_x':
                    old_length = component.length # Store old length if needed
                    component.start_pos.setX(float(new_value))
                    # Recalculate length if desired (otherwise length changes)
                    dx = component.end_pos.x() - component.start_pos.x()
                    dy = component.end_pos.y() - component.start_pos.y()
                    component.length = math.sqrt(dx*dx + dy*dy)
                    # Update panel if length changed
                    if self.parameter_panel.detail_widgets.get('length'):
                        self.parameter_panel.detail_widgets['length'].setValue(component.length)
                elif param_name == 'start_y':
                    component.start_pos.setY(float(new_value))
                    dx = component.end_pos.x() - component.start_pos.x()
                    dy = component.end_pos.y() - component.start_pos.y()
                    component.length = math.sqrt(dx*dx + dy*dy)
                    if self.parameter_panel.detail_widgets.get('length'):
                        self.parameter_panel.detail_widgets['length'].setValue(component.length)
                elif param_name == 'end_x':
                    component.end_pos.setX(float(new_value))
                    dx = component.end_pos.x() - component.start_pos.x()
                    dy = component.end_pos.y() - component.start_pos.y()
                    component.length = math.sqrt(dx*dx + dy*dy)
                    if self.parameter_panel.detail_widgets.get('length'):
                        self.parameter_panel.detail_widgets['length'].setValue(component.length)
                elif param_name == 'end_y':
                    component.end_pos.setY(float(new_value))
                    dx = component.end_pos.x() - component.start_pos.x()
                    dy = component.end_pos.y() - component.start_pos.y()
                    component.length = math.sqrt(dx*dx + dy*dy)
                    if self.parameter_panel.detail_widgets.get('length'):
                        self.parameter_panel.detail_widgets['length'].setValue(component.length)
                elif param_name == 'mid_point_distance':
                    # Value can be float or None
                    if new_value is None:
                        component.mid_point_distance = None
                    else:
                        dist = float(new_value)
                        # Clamp distance to be within rod length
                        if 0 <= dist <= component.length:
                            component.mid_point_distance = dist
                        else:
                            print(f"Warning: Mid-point distance {dist} clamped to rod length {component.length}.")
                            component.mid_point_distance = max(0, min(dist, component.length))
                            # Update UI if clamped (requires getting the spinbox)
                            if 'mid_dist_spin' in self.parameter_panel.detail_widgets:
                                self.parameter_panel.detail_widgets['mid_dist_spin'].setValue(component.mid_point_distance)
                elif param_name == 'pen_distance_from_start':
                    # Value can be float or None (though panel logic should handle None via checkbox)
                    if new_value is None:
                        component.pen_distance_from_start = None
                    else:
                        dist = float(new_value)
                        # Clamp distance to be within rod length
                        if 0 <= dist <= component.length:
                            component.pen_distance_from_start = dist
                        else:
                            print(f"Warning: Pen distance {dist} clamped to rod length {component.length}.")
                            component.pen_distance_from_start = max(0, min(dist, component.length))
                            # Update UI if clamped
                            if 'pen_distance_from_start' in self.parameter_panel.detail_widgets:
                                self.parameter_panel.detail_widgets['pen_distance_from_start'].setValue(component.pen_distance_from_start)
            
            # After updating the component, refresh the canvas
            self.canvas.update()
            # Also refresh the parameter panel display in case the value was adjusted (e.g. clamped)
            # or if changing one value affects others (like rod length)
            # self._on_component_selected(component) # Re-call to refresh panel (optional)
            
        except Exception as e:
            print(f"Error updating component parameter '{param_name}': {e}")
            # Optionally show error in status bar or dialog
            self.statusBar().showMessage(f"Error updating {param_name}: {e}", 3000) 

    def _handle_pen_assignment(self, assigned_rod_id: int, is_pen_now: bool):
        """Handle the pen_assigned signal from ParameterPanel.
        Ensures only one rod has the pen at a time.
        Accepts rod_id (int) from the signal.
        """
        # Get the actual Rod object using the ID
        assigned_rod = self.canvas.components_by_id.get(assigned_rod_id)
        if not assigned_rod or not isinstance(assigned_rod, Rod):
            print(f"ERROR: _handle_pen_assignment received invalid rod ID {assigned_rod_id}")
            return
            
        if is_pen_now:
            print(f"MainWindow: Rod {assigned_rod.id} assigned as pen carrier.")
            # Iterate through all rods on the canvas
            for rod_id, component in self.canvas.components_by_id.items():
                if isinstance(component, Rod):
                    # If this is NOT the rod that was just assigned the pen,
                    # and it currently has a pen, remove its pen status.
                    if rod_id != assigned_rod_id and component.pen_distance_from_start is not None:
                        print(f"MainWindow: Removing pen from previous carrier Rod {rod_id}.")
                        component.pen_distance_from_start = None
                        # If this rod happens to be selected, refresh its panel display
                        if self.canvas.selected_component == component:
                             self.parameter_panel.show_rod_details(component, self.canvas.components_by_id)
        else:
            # Pen was removed from assigned_rod, nothing else to do here
            # The ParameterPanel._handle_pen_toggled already updated the model
            print(f"MainWindow: Pen removed from Rod {assigned_rod.id}.") # Use looked-up assigned_rod here

    def _handle_open(self):
        """Handle the File -> Open... action."""
        start_dir = os.path.dirname(self.current_config_path) if self.current_config_path else ""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Configuration File",
            start_dir,
            "XML Files (*.xml);;All Files (*)"
        )
        
        if file_path:
            try:
                # Load the configuration
                machine_config = load_config_from_xml(file_path)
                
                # Clear current selection/panel before loading
                if self.canvas.selected_component:
                    self.canvas.selected_component.selected = False
                    self.canvas.selected_component = None
                    self.canvas.component_selected.emit(None)
                    
                # Populate the canvas with the loaded config
                populate_canvas_from_config(self.canvas, machine_config)
                
                # Update current path and window title
                self.current_config_path = file_path
                self.setWindowTitle(f"Cycloid Machine Simulator - {os.path.basename(file_path)}")
                self.statusBar().showMessage(f"Loaded configuration from {file_path}", 3000)
                
            except Exception as e:
                print(f"Error loading configuration from {file_path}: {e}")
                self.statusBar().showMessage(f"Error loading file: {e}", 5000)
                # TODO: Show error dialog

    def _handle_save(self):
        """Handle the File -> Save action."""
        if not self.current_config_path:
            # If no path is set, act like Save As (but don't clear after)
            self._handle_save_as(clear_after=False) 
            return
            
        self._save_to_file(self.current_config_path)
            
    def _handle_save_as(self, clear_after=True):
        """Handle the File -> Save As... action.
           If clear_after is True, clears the canvas after saving.
        """
        # Start in the directory of the current file, or the workspace root
        start_dir = os.path.dirname(self.current_config_path) if self.current_config_path else ""
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Configuration As", 
            start_dir, # Start directory
            "XML Files (*.xml);;All Files (*)"
        )
        
        if file_path:
            # Ensure .xml extension if not provided
            if not file_path.lower().endswith('.xml'):
                file_path += '.xml'
                
            if self._save_to_file(file_path):
                self.current_config_path = file_path # Update current path
                self.setWindowTitle(f"Cycloid Machine Simulator - {os.path.basename(file_path)}")
                if clear_after:
                    self._clear_canvas()
                    self.current_config_path = None # Clear path after 'New'
                    self.setWindowTitle("Cycloid Machine Simulator - New Configuration")

    def _save_to_file(self, file_path: str) -> bool:
        """Generates XML and saves it to the specified file path."""
        try:
            # Get components from canvas
            wheels = self.canvas.wheels
            rods = self.canvas.rods
            components_dict = self.canvas.components_by_id
            
            # Generate XML tree
            xml_tree = generate_xml_tree(wheels, rods, components_dict)
            
            # Get pretty XML string
            pretty_xml_string = prettify_xml(xml_tree.getroot())
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml_string)
                
            self.statusBar().showMessage(f"Configuration saved to {file_path}", 3000)
            return True
        except Exception as e:
            print(f"Error saving configuration to {file_path}: {e}")
            self.statusBar().showMessage(f"Error saving file: {e}", 5000)
            # TODO: Show error dialog
            return False
            
    def _clear_canvas(self):
        """Clears all components from the drawing canvas."""
        # Clear component lists
        self.canvas.wheels.clear()
        self.canvas.rods.clear()
        self.canvas.components_by_id.clear()
        self.canvas.pen_path_points.clear()
        
        # Reset selection and state
        self.canvas.selected_component = None
        self.canvas.dragging = False
        self.canvas.drag_start = None
        self.canvas.hover_component = None
        self.canvas.dragging_point = None
        self.canvas.hover_connection = None
        self.canvas.creating_rod = False
        self.canvas.rod_start_pos = None
        
        # Reset ID counter
        self.canvas._next_component_id = 1
        
        # Update UI
        self.canvas.update()
        self.parameter_panel.clear_details()
        self.statusBar().showMessage("Canvas cleared", 2000) 

    def _on_add_canvas(self):
        """Handle adding the special canvas wheel."""
        # Check if a canvas wheel already exists (using the canvas's attribute)
        if self.canvas.canvas_wheel is not None:
            print("Canvas wheel already exists. Only one allowed.")
            self.statusBar().showMessage("Canvas wheel already exists.", 3000)
            # Optionally select the existing one?
            # if self.canvas.canvas_wheel != self.canvas.selected_component:
            #     self.canvas.selected_component = self.canvas.canvas_wheel
            #     self.canvas.canvas_wheel.selected = True
            #     self.component_selected.emit(self.canvas.canvas_wheel)
            #     self.canvas.update()
            return

        # Determine center (default)
        center = self.canvas._snap_to_grid(self.canvas._screen_to_canvas(QPointF(self.canvas.width()/2, self.canvas.height()/2)))
        diameter = 500.0 # Default diameter

        # Ensure canvas has focus to potentially capture subsequent interactions
        self.canvas.setFocus()

        # Call the DEDICATED canvas method to add the special wheel
        self.canvas.add_canvas_wheel(center, diameter) # <-- CHANGED: Call add_canvas_wheel

        # The add_canvas_wheel method should now handle setting self.canvas.canvas_wheel
        # and adding to lists/dicts. We just need to handle UI feedback.
        if self.canvas.canvas_wheel:
            # Select the newly added canvas wheel
            self.canvas.selected_component = self.canvas.canvas_wheel
            self.canvas.canvas_wheel.selected = True
            # Emit the signal FROM THE CANVAS to update the panel
            self.canvas.component_selected.emit(self.canvas.canvas_wheel) # <-- CORRECTED: Emit from self.canvas
            self.canvas.update()
            self.statusBar().showMessage(f"Added Canvas Wheel {self.canvas.canvas_wheel.id} at ({center.x():.0f}, {center.y():.0f})", 2000)
        else:
            # This case should ideally not happen if the check at the start works
            self.statusBar().showMessage("Failed to add canvas wheel.", 3000)

    def _on_generate_image(self, filename: str, width: int, height: int, line_color: str, line_width: int):
        """Trigger the path calculation and image generation."""
        print("Requesting path calculation from SymPy solver...")
        
        # Extract configuration from canvas
        all_wheels = self.canvas.wheels
        rods = self.canvas.rods
        components_dict = self.canvas.components_by_id
        
        # Use the dedicated attribute from the canvas directly
        canvas_wheel_obj = self.canvas.canvas_wheel # <-- CHANGED: Use direct attribute
        # driving_wheels = []
        # for wheel in all_wheels:
        #     if wheel.is_canvas:
        #         if canvas_wheel_obj is None:
        #             canvas_wheel_obj = wheel
        #         else:
        #             print("WARNING: Multiple canvas wheels found! Using the first one.")
        #     else:
        #         driving_wheels.append(wheel)

        # Determine the pen rod and distance
        pen_rod_id = None
        pen_distance_from_start = None
        for rod in rods:
            if rod.pen_distance_from_start is not None:
                pen_rod_id = rod.id
                pen_distance_from_start = rod.pen_distance_from_start
                break # Assume only one pen

        if pen_rod_id is None:
            print("ERROR: No pen assigned to any rod.")
            self.statusBar().showMessage("Error: Assign a pen to a rod first.", 3000)
            return

        # Get calculation parameters (e.g., duration, steps - maybe from UI later?)
        duration = 10.0 # Seconds
        steps = 600    # Number of steps

        try:
            # Call the sympy solver
            calculated_path = calculate_path_sympy(
                wheels=all_wheels, # Pass ALL wheels (solver should handle canvas vs driving)
                rods=rods,
                canvas_wheel=canvas_wheel_obj, # Pass the identified canvas wheel
                pen_rod_id=pen_rod_id,
                pen_distance_from_start=pen_distance_from_start,
                duration=duration,
                steps=steps,
                components_dict=components_dict
            )
            
            # Store the calculated path in the canvas
            self.canvas.pen_path_points = calculated_path
            
            # Generate the image using the canvas method (using its stored path)
            print(f"Generating image from {len(calculated_path)} calculated points...")
            success = self.canvas.generate_image(filename, width, height, line_color, line_width)
            if success:
                self.statusBar().showMessage(f"Image saved to {filename}", 5000)
            else:
                self.statusBar().showMessage("Error generating image.", 3000)

        except Exception as e:
            print(f"ERROR during SymPy calculation or image generation: {e}")
            # Optionally show a more detailed error to the user
            self.statusBar().showMessage(f"Calculation/Generation Error: {e}", 5000)
            # Print traceback for debugging
            import traceback
            traceback.print_exc()


    def _on_start_simulation(self):
        # This method is mentioned in the _on_generate_image method but not implemented in the original file or the new code block.
        # If this method is intended to be called when starting a simulation, it should be implemented here.
        # For now, we'll just print a message.
        print("Starting simulation...")
        # In a real application, you might want to call self.canvas.start_simulation() here.

    def _on_add_wheel(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when adding a new wheel, it should be implemented here.
        # For now, we'll just print a message.
        print("Adding new wheel...")
        # In a real application, you might want to call self.canvas.add_wheel() here.

    def _on_handle_pen_assignment(self, assigned_rod: Rod, is_pen_now: bool):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when a pen is assigned to a rod, it should be implemented here.
        # For now, we'll just print a message.
        print(f"Pen assignment: Rod {assigned_rod.id}, is_pen_now={is_pen_now}")
        # In a real application, you might want to call self.canvas.update() here to refresh the canvas.

    def _on_handle_open(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when opening a file, it should be implemented here.
        # For now, we'll just print a message.
        print("Opening file...")
        # In a real application, you might want to call self.canvas.update() here to refresh the canvas.

    def _on_handle_save(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when saving a file, it should be implemented here.
        # For now, we'll just print a message.
        print("Saving file...")
        # In a real application, you might want to call self._save_to_file(self.current_config_path) here.

    def _on_handle_save_as(self, clear_after=True):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when saving a file as, it should be implemented here.
        # For now, we'll just print a message.
        print(f"Handling save as: clear_after={clear_after}")
        # In a real application, you might want to call self._handle_save_as(clear_after) here.

    def _on_handle_clear_canvas(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when clearing the canvas, it should be implemented here.
        # For now, we'll just print a message.
        print("Clearing canvas...")
        # In a real application, you might want to call self._clear_canvas() here.

    def _on_handle_save_to_file(self, file_path: str) -> bool:
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when saving to a file, it should be implemented here.
        # For now, we'll just print a message.
        print(f"Saving to file: {file_path}")
        # In a real application, you might want to call self._save_to_file(file_path) here.
        return True

    def _on_handle_event_filter(self, obj: QObject, event: QEvent) -> bool:
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when an event is filtered, it should be implemented here.
        # For now, we'll just print a message.
        print(f"Event filtered: obj={obj}, event={event}")
        # In a real application, you might want to call super(MainWindow, self).eventFilter(obj, event) here.
        return False

    def _on_handle_setup_menu_bar(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when setting up the menu bar, it should be implemented here.
        # For now, we'll just print a message.
        print("Setting up menu bar...")
        # In a real application, you might want to call self.menuBar() here to add menu items.

    def _on_handle_connect_signals(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when connecting signals, it should be implemented here.
        # For now, we'll just print a message.
        print("Connecting signals...")
        # In a real application, you might want to call self._connect_signals() here.

    def _on_handle_set_focus(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when setting focus, it should be implemented here.
        # For now, we'll just print a message.
        print("Setting focus...")
        # In a real application, you might want to call self.canvas.setFocus() here.

    def _on_handle_install_event_filter(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when installing an event filter, it should be implemented here.
        # For now, we'll just print a message.
        print("Installing event filter...")
        # In a real application, you might want to call self.installEventFilter(self) here.

    def _on_handle_event_filter_result(self, obj: QObject, event: QEvent) -> bool:
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when an event filter result is returned, it should be implemented here.
        # For now, we'll just print a message.
        print(f"Event filter result: obj={obj}, event={event}")
        # In a real application, you might want to call super(MainWindow, self).eventFilter(obj, event) here.
        return False

    def _on_handle_handle_pen_assignment(self, assigned_rod: Rod, is_pen_now: bool):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling a pen assignment, it should be implemented here.
        # For now, we'll just print a message.
        print(f"Handling pen assignment: Rod {assigned_rod.id}, is_pen_now={is_pen_now}")
        # In a real application, you might want to call self._handle_pen_assignment(assigned_rod, is_pen_now) here.

    def _on_handle_handle_open(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling an open action, it should be implemented here.
        # For now, we'll just print a message.
        print("Handling open...")
        # In a real application, you might want to call self._handle_open() here.

    def _on_handle_handle_save(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling a save action, it should be implemented here.
        # For now, we'll just print a message.
        print("Handling save...")
        # In a real application, you might want to call self._handle_save() here.

    def _on_handle_handle_save_as(self, clear_after=True):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling a save as action, it should be implemented here.
        # For now, we'll just print a message.
        print(f"Handling save as: clear_after={clear_after}")
        # In a real application, you might want to call self._handle_save_as(clear_after) here.

    def _on_handle_handle_clear_canvas(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling a clear canvas action, it should be implemented here.
        # For now, we'll just print a message.
        print("Handling clear canvas...")
        # In a real application, you might want to call self._clear_canvas() here.

    def _on_handle_handle_save_to_file(self, file_path: str) -> bool:
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling a save to file action, it should be implemented here.
        # For now, we'll just print a message.
        print(f"Handling save to file: {file_path}")
        # In a real application, you might want to call self._save_to_file(file_path) here.
        return True

    def _on_handle_handle_event_filter(self, obj: QObject, event: QEvent) -> bool:
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling an event filter action, it should be implemented here.
        # For now, we'll just print a message.
        print(f"Handling event filter: obj={obj}, event={event}")
        # In a real application, you might want to call super(MainWindow, self).eventFilter(obj, event) here.
        return False

    def _on_handle_handle_setup_menu_bar(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling a setup menu bar action, it should be implemented here.
        # For now, we'll just print a message.
        print("Handling setup menu bar...")
        # In a real application, you might want to call self._setup_menu_bar() here.

    def _on_handle_handle_connect_signals(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling a connect signals action, it should be implemented here.
        # For now, we'll just print a message.
        print("Handling connect signals...")
        # In a real application, you might want to call self._connect_signals() here.

    def _on_handle_handle_set_focus(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling a set focus action, it should be implemented here.
        # For now, we'll just print a message.
        print("Handling set focus...")
        # In a real application, you might want to call self.canvas.setFocus() here.

    def _on_handle_handle_install_event_filter(self):
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling an install event filter action, it should be implemented here.
        # For now, we'll just print a message.
        print("Handling install event filter...")
        # In a real application, you might want to call self.installEventFilter(self) here.

    def _on_handle_handle_event_filter_result(self, obj: QObject, event: QEvent) -> bool:
        # This method is mentioned in the _connect_signals method but not implemented in the original file or the new code block.
        # If this method is intended to be called when handling an event filter result action, it should be implemented here.
        # For now, we'll just print a message.
        print(f"Handling event filter result: obj={obj}, event={event}")
        # In a real application, you might want to call super(MainWindow, self).eventFilter(obj, event) here.
        return False 