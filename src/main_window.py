from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QFrame, QFileDialog)
from PyQt6.QtCore import Qt, QSize, QPointF, QObject, QEvent
from PyQt6.QtGui import QAction
from drawing_canvas import DrawingCanvas
from parameter_panel import ParameterPanel
from components import Wheel, Rod
from typing import Optional, Union, Dict
from PyQt6.QtWidgets import QApplication
import math
import os

# Import loader and writer functions
from config_loader import load_config_from_xml, MachineConfig, populate_canvas_from_config
from config_writer import generate_xml_tree, prettify_xml

class MainWindow(QMainWindow):
    def __init__(self, initial_config_path: Optional[str] = None):
        super().__init__()
        self.current_config_path: Optional[str] = initial_config_path
        
        # Set initial window title
        self._update_window_title()
        
        self.setMinimumSize(QSize(800, 800))
        
        # --- Main Layout --- 
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # --- Parameter Panel --- 
        self.parameter_panel = ParameterPanel()
        self.parameter_panel.setFixedWidth(288)
        main_layout.addWidget(self.parameter_panel)
        
        # --- Drawing Canvas --- 
        self.canvas = DrawingCanvas()
        main_layout.addWidget(self.canvas)
        
        # --- Status Bar --- 
        self.statusBar().showMessage("Ready")
        
        # --- Setup UI Elements & Connections ---
        self._setup_menu_bar()
        self._connect_signals()
        
        self.canvas.setFocus() # Give canvas initial focus
        self.installEventFilter(self) # For global key handling
        
    def _update_window_title(self):
        """Sets the window title based on the current config path."""
        base_title = "Cycloid Machine Simulator"
        if self.current_config_path:
            file_name = os.path.basename(self.current_config_path)
            self.setWindowTitle(f"{base_title} - {file_name}")
        else:
            self.setWindowTitle(f"{base_title} - New Configuration")

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter events to handle arrow keys globally, but allow panel input."""
        if event.type() == QEvent.Type.KeyPress and \
           event.key() in [Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down]:
            
            panel_has_focus = False
            focus_widget = QApplication.focusWidget() 
            if focus_widget:
                widget = focus_widget
                while widget is not None:
                    if widget == self.parameter_panel:
                        panel_has_focus = True
                        break
                    widget = widget.parentWidget()
            
            # If panel has focus, let it handle the key press
            if panel_has_focus:
                return False 
            
            # Otherwise, if canvas has a selected component, let canvas handle it
            elif self.canvas.selected_component:
                self.canvas.setFocus()
                # Let the normal event loop pass the key to the focused canvas
                return False 
                
        # Let other events pass through normally
        return super(MainWindow, self).eventFilter(obj, event)

    def _setup_menu_bar(self):
        """Creates the main menu bar and actions."""
        menubar = self.menuBar()
        
        # --- File Menu ---
        file_menu = menubar.addMenu('&File')
        
        open_action = QAction('&Open...', self)
        open_action.setShortcut(Qt.Modifier.CTRL | Qt.Key.Key_O)
        open_action.triggered.connect(self._handle_open)
        file_menu.addAction(open_action)

        new_action = QAction('&New', self)
        new_action.setShortcut(Qt.Modifier.CTRL | Qt.Key.Key_N)
        new_action.triggered.connect(self._handle_new)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()

        save_action = QAction('&Save', self)
        save_action.setShortcut(Qt.Modifier.CTRL | Qt.Key.Key_S)
        save_action.triggered.connect(self._handle_save)
        file_menu.addAction(save_action)
        
        # Correct action label
        save_as_action = QAction('Save &As...', self) 
        save_as_action.setShortcut(Qt.Modifier.CTRL | Qt.Modifier.SHIFT | Qt.Key.Key_S)
        save_as_action.triggered.connect(self._handle_save_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('E&xit', self)
        exit_action.triggered.connect(self.close) 
        file_menu.addAction(exit_action)
        
        # --- View Menu (Placeholder) ---
        view_menu = menubar.addMenu('&View')
        # TODO: Add view actions (e.g., grid, zoom)
        
        # --- Help Menu (Placeholder) ---
        help_menu = menubar.addMenu('&Help')
        # TODO: Add help actions (e.g., about)
        
    def _connect_signals(self):
        """Connect signals between components."""
        self.parameter_panel.snap_changed.connect(self.canvas.set_snap_size)
        self.parameter_panel._add_wheel_button.clicked.connect(self._on_add_wheel)
        self.parameter_panel.add_rod_requested.connect(self.canvas.start_rod_creation)
        self.canvas.component_selected.connect(self._on_component_selected)
        self.parameter_panel.parameter_changed.connect(self._on_parameter_changed)
        self.parameter_panel.pen_assigned.connect(self._handle_pen_assignment)
        
        # Connect simulation control signals
        self.parameter_panel.start_simulation_requested.connect(self.canvas.start_simulation)
        self.parameter_panel.stop_simulation_requested.connect(self.canvas.stop_simulation)
        
    # --- UI Action Handlers --- 
    def _on_snap_changed(self, snap_value: int):
        """Handle snap setting changes (now just updates status bar)."""
        self.statusBar().showMessage(f"Grid snap set to {snap_value}mm")
        
    def _on_add_wheel(self):
        """Handle adding a new wheel via the panel button."""
        # Add wheel at a default position
        self.canvas.add_wheel(QPointF(200, 200), 100) 
        self.canvas.setFocus() 
        self.statusBar().showMessage("Added new wheel")
        
    def _on_component_selected(self, component: Optional[Union[Wheel, Rod]]):
        """Update parameter panel when a component is selected/deselected on canvas."""
        if component is None:
            self.parameter_panel.clear_details()
        elif isinstance(component, Wheel):
            self.parameter_panel.show_wheel_details(component, self.canvas.components_by_id)
        elif isinstance(component, Rod):
            self.parameter_panel.show_rod_details(component, self.canvas.components_by_id)
        else:
            self.parameter_panel.clear_details()
            
    def _on_parameter_changed(self, component: Union[Wheel, Rod], param_name: str, new_value: object):
        """Handle parameter changes submitted from the ParameterPanel."""
        try:
            needs_constraint_update = False
            if isinstance(component, Wheel):
                if param_name == 'diameter': component.diameter = float(new_value)
                elif param_name == 'center_x': 
                    component.center.setX(float(new_value))
                    needs_constraint_update = True # Moving center affects constraints
                elif param_name == 'center_y': 
                    component.center.setY(float(new_value))
                    needs_constraint_update = True # Moving center affects constraints
                elif param_name == 'speed_ratio': component.speed_ratio = float(new_value)
                elif param_name == 'p1_radius':
                    if 'p1' in component.connection_points:
                        new_radius = max(0.0, float(new_value))
                        component.connection_points['p1'].radius = new_radius
                        if new_radius != float(new_value) and 'p1_radius' in self.parameter_panel.detail_widgets:
                            self.parameter_panel.detail_widgets['p1_radius'].setValue(new_radius)
                        needs_constraint_update = True # Changing radius affects constraints
                    else: print("Warning: Tried to set p1_radius, but point 'p1' does not exist.")
            
            elif isinstance(component, Rod):
                if param_name == 'length': print("Note: Setting rod length directly from panel is not implemented yet.")
                elif param_name == 'start_x': component.start_pos.setX(float(new_value))
                elif param_name == 'start_y': component.start_pos.setY(float(new_value))
                elif param_name == 'end_x': component.end_pos.setX(float(new_value))
                elif param_name == 'end_y': component.end_pos.setY(float(new_value))
                
                # Recalculate length after moving ends via panel & update constraints
                if param_name in ['start_x', 'start_y', 'end_x', 'end_y']:
                    # Disconnect if moving endpoints via panel
                    if component.start_connection: component.start_connection = None
                    if component.end_connection: component.end_connection = None
                    dx = component.end_pos.x() - component.start_pos.x()
                    dy = component.end_pos.y() - component.start_pos.y()
                    component.length = math.sqrt(dx*dx + dy*dy)
                    if self.parameter_panel.detail_widgets.get('length'):
                        self.parameter_panel.detail_widgets['length'].setValue(component.length)
                    needs_constraint_update = True 

                elif param_name == 'mid_point_distance':
                    old_value = component.mid_point_distance
                    if new_value is None: component.mid_point_distance = None
                    else:
                        dist = max(0, min(float(new_value), component.length)) # Clamp value
                        component.mid_point_distance = dist
                        # Update UI if clamped
                        if dist != float(new_value) and 'mid_dist_spin' in self.parameter_panel.detail_widgets:
                            self.parameter_panel.detail_widgets['mid_dist_spin'].setValue(dist)
                    if old_value != component.mid_point_distance:
                         needs_constraint_update = True # Changing mid-point requires update
                
                elif param_name == 'pen_distance_from_start':
                    old_value = component.pen_distance_from_start
                    if new_value is None: # Should not happen from spinbox, but handle defensively
                        component.pen_distance_from_start = None
                    else:
                        dist = max(0, min(float(new_value), component.length)) # Clamp value
                        component.pen_distance_from_start = dist
                        # Update UI if clamped
                        if dist != float(new_value) and 'pen_distance_spin' in self.parameter_panel.detail_widgets:
                            self.parameter_panel.detail_widgets['pen_distance_spin'].setValue(dist)
                    # Set flag to ensure update/redraw occurs, similar to mid-point
                    if old_value != component.pen_distance_from_start:
                         needs_constraint_update = True 
            
            # Propagate constraints if necessary and update canvas
            if needs_constraint_update:
                # Provide initial targets based on the moved component for efficiency
                initial_targets = {}
                if isinstance(component, Wheel):
                     for point_id in component.connection_points:
                         pos = component.get_connection_point_position(point_id)
                         if pos: initial_targets[(component.id, point_id)] = pos
                elif isinstance(component, Rod) and param_name in ['start_x', 'start_y', 'end_x', 'end_y']:
                    initial_targets[(component.id, 'start')] = component.start_pos
                    initial_targets[(component.id, 'end')] = component.end_pos
                    # Mid-point constraint will be handled within propagate
                self.canvas._propagate_constraints(initial_targets)
            
            # Always trigger a repaint after handling a parameter change
            self.canvas.update() 
            
        except Exception as e:
            print(f"Error updating component parameter '{param_name}': {e}")
            self.statusBar().showMessage(f"Error updating {param_name}: {e}", 3000)
            
    def _handle_pen_assignment(self, assigned_rod: Rod, is_pen_now: bool):
        """Handle the pen_assigned signal, ensuring only one rod has the pen."""
        if is_pen_now:
            print(f"MainWindow: Rod {assigned_rod.id} assigned as pen carrier.")
            for rod in self.canvas.rods:
                if rod.id != assigned_rod.id and rod.pen_distance_from_start is not None:
                    print(f"MainWindow: Removing pen from previous carrier Rod {rod.id}.")
                    rod.pen_distance_from_start = None
                    # If this other rod happens to be selected, refresh its panel display
                    if self.canvas.selected_component == rod:
                         self.parameter_panel.show_rod_details(rod, self.canvas.components_by_id)
        # Update canvas to show/hide the pen marker
        self.canvas.update()

    # --- File Action Handlers ---
    def _handle_open(self):
        """Handle the File -> Open... action."""
        # TODO: Check for unsaved changes before opening
        start_dir = os.path.dirname(self.current_config_path) if self.current_config_path else ""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Configuration File", start_dir, "XML Files (*.xml);;All Files (*)")
        
        if file_path:
            try:
                machine_config = load_config_from_xml(file_path)
                # Clear selection before clearing canvas content
                if self.canvas.selected_component:
                    self.canvas.selected_component.selected = False
                    self.canvas.selected_component = None
                    self.canvas.component_selected.emit(None)
                # Populate canvas (this clears existing components)
                populate_canvas_from_config(self.canvas, machine_config)
                self.current_config_path = file_path
                self._update_window_title()
                self.statusBar().showMessage(f"Loaded configuration from {file_path}", 3000)
            except Exception as e:
                print(f"Error loading configuration from {file_path}: {e}")
                self.statusBar().showMessage(f"Error loading file: {e}", 5000)
                # Consider showing a QMessageBox here
                
    def _handle_new(self):
        """Handle the File -> New action."""
        # TODO: Add check for unsaved changes before clearing
        self._clear_canvas()
        self.current_config_path = None 
        self._update_window_title()

    def _handle_save(self):
        """Handle the File -> Save action."""
        if not self.current_config_path:
            self._handle_save_as() # Acts like Save As if no path
            return
        self._save_to_file(self.current_config_path)
            
    def _handle_save_as(self):
        """Handle the File -> Save As... action."""
        start_dir = os.path.dirname(self.current_config_path) if self.current_config_path else ""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Configuration As", start_dir, "XML Files (*.xml);;All Files (*)")
        
        if file_path:
            # Ensure .xml extension
            if not file_path.lower().endswith('.xml'): 
                file_path += '.xml'
                
            if self._save_to_file(file_path):
                self.current_config_path = file_path # Update path only on successful save
                self._update_window_title()

    def _save_to_file(self, file_path: str) -> bool:
        """Generates XML and saves it to the specified file path."""
        try:
            xml_tree = generate_xml_tree(self.canvas.wheels, self.canvas.rods, self.canvas.components_by_id)
            pretty_xml_string = prettify_xml(xml_tree.getroot())
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml_string)
            self.statusBar().showMessage(f"Configuration saved to {file_path}", 3000)
            # Mark changes as saved (if implementing unsaved changes check)
            return True
        except Exception as e:
            print(f"Error saving configuration to {file_path}: {e}")
            self.statusBar().showMessage(f"Error saving file: {e}", 5000)
            # Consider showing a QMessageBox here
            return False
            
    def _clear_canvas(self):
        """Clears all components from the drawing canvas."""
        self.canvas.wheels.clear()
        self.canvas.rods.clear()
        self.canvas.components_by_id.clear()
        self.canvas.pen_path_points.clear()
        self.canvas.selected_component = None
        self.canvas.dragging = False
        self.canvas.drag_start = None
        self.canvas.hover_component = None
        self.canvas.dragging_point = None
        self.canvas.hover_connection = None
        self.canvas.creating_rod = False
        self.canvas.rod_start_pos = None
        self.canvas._next_component_id = 1
        self.canvas.update()
        self.parameter_panel.clear_details()
        self.statusBar().showMessage("Canvas cleared", 2000)
        # Mark changes as saved (or prompt user)
