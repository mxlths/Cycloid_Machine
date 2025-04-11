from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QPushButton, QFrame)
from PyQt6.QtCore import Qt, QSize, QPointF, QObject, QEvent
from drawing_canvas import DrawingCanvas
from parameter_panel import ParameterPanel
from components import Wheel, Rod
from typing import Optional, Union
from PyQt6.QtWidgets import QApplication
import math

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cycloid Machine Simulator")
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
        # Add file menu actions here
        
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
        
        # Connect add rod request signal to canvas start_rod_creation
        self.parameter_panel.add_rod_requested.connect(self.canvas.start_rod_creation)
        
        # Connect canvas component selection signal
        self.canvas.component_selected.connect(self._on_component_selected)
        
        # Connect parameter panel change signal
        self.parameter_panel.parameter_changed.connect(self._on_parameter_changed)
        
    def _on_snap_changed(self, snap_value: int):
        """Handle snap setting changes"""
        print(f"MainWindow received snap change: {snap_value}mm")  # Debug print
        self.canvas.set_snap_size(snap_value)
        self.statusBar().showMessage(f"Grid snap set to {snap_value}mm")
        
    def _on_add_wheel(self):
        """Handle adding a new wheel"""
        # For now, add a wheel at a default position with default size
        self.canvas.add_wheel(QPointF(200, 200), 100)
        self.canvas.setFocus()  # Ensure canvas has focus after adding wheel
        self.statusBar().showMessage("Added new wheel")
        
    def _on_component_selected(self, component: Optional[Union[Wheel, Rod]]):
        """Handle component selection changes from the canvas."""
        if component is None:
            # print("MainWindow received: No component selected") # Removed Debug
            self.parameter_panel.clear_details()
        elif isinstance(component, Wheel):
            # print(f"MainWindow received: Wheel selected - {component}") # Removed Debug
            self.parameter_panel.show_wheel_details(component)
        elif isinstance(component, Rod):
            # print(f"MainWindow received: Rod selected - {component}") # Removed Debug
            self.parameter_panel.show_rod_details(component)
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
                elif param_name == 'connection_radius':
                    component.connection_radius = float(new_value) if new_value >= 0 else 0 # Ensure non-negative
                elif param_name == 'connection_phase_deg':
                    component.connection_phase_deg = float(new_value) % 360 # Wrap degrees
                    
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
            
            # After updating the component, refresh the canvas
            self.canvas.update()
            # Also refresh the parameter panel display in case the value was adjusted (e.g. clamped)
            # or if changing one value affects others (like rod length)
            # self._on_component_selected(component) # Re-call to refresh panel (optional)
            
        except Exception as e:
            print(f"Error updating component parameter '{param_name}': {e}")
            # Optionally show error in status bar or dialog
            self.statusBar().showMessage(f"Error updating {param_name}: {e}", 3000) 