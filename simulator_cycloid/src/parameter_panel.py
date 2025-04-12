from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
                               QPushButton, QFrame, QScrollArea, QButtonGroup, QFormLayout, QSizePolicy, QLayout, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QFocusEvent
from components import Wheel, Rod
from typing import Optional, Dict, Tuple
from functools import partial

# Helper to format connection tuples back to strings
def _format_connection_target(connection: Optional[Tuple[int, str]], components_dict: Dict) -> Optional[str]:
    if connection is None:
        return None
        
    comp_id, point_id = connection
    
    if comp_id not in components_dict:
        print(f"Warning: Cannot format connection for missing component ID: {comp_id}")
        return "<Missing Comp>"
        
    component = components_dict[comp_id]
    
    if isinstance(component, Wheel):
        # Format: wheel_{id}_point_{point_id}
        return f"wheel_{comp_id}_point_{point_id}"
    elif isinstance(component, Rod):
        # Format: rod_{id}_{start|mid|end}
        # point_id should be 'start', 'mid', or 'end' for rods
        if point_id in ['start', 'mid', 'end']:
             return f"rod_{comp_id}_{point_id}"
        else:
             print(f"Warning: Invalid point_id '{point_id}' for rod connection {comp_id}")
             return f"<Invalid Pt {point_id}>"
    else:
        print(f"Warning: Unknown component type for connection: {type(component)}")
        return "<Unknown Comp>"

# --- Remove Debugging Subclass ---
# class DebuggingLineEdit(QLineEdit):
#     ...
# --- End Debugging Subclass ---

class CollapsibleSection(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0) # Compact

        self.toggle_button = QPushButton(title)
        self.toggle_button.setStyleSheet("text-align: left; padding: 5px;") 
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True) # Start expanded
        self.toggle_button.clicked.connect(self._toggle_content)

        # Content widget container (will hold the actual content layout)
        self.content_area = QWidget()
        self.content_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.content_area.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.content_area.setVisible(self.toggle_button.isChecked())

        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)
        
    def setContentLayout(self, content_layout: QLayout):
        """Sets the layout for the content area."""
        # Clear previous layout if any
        old_layout = self.content_area.layout()
        if old_layout is not None:
             # Cleanly remove widgets from old layout before deleting
             QWidget().setLayout(old_layout) 
             old_layout.deleteLater()
             
        self.content_area.setLayout(content_layout)
        # Adjust size based on new content
        self.content_area.adjustSize()
        # Update visibility based on button state
        self.content_area.setVisible(self.toggle_button.isChecked())
        
    def _toggle_content(self, checked):
        self.content_area.setVisible(checked)
        # When hiding, set maximum height to 0
        if not checked:
             self.content_area.setMaximumHeight(0)
        else:
             # Allow content area to expand vertically again
             self.content_area.setMaximumHeight(16777215) # Default max height
        # Request layout update
        self.parentWidget().layout().activate()

class ParameterPanel(QFrame):
    # Signal when snap size changes
    snap_changed = pyqtSignal(int)
    # Signal when add rod button is clicked
    add_rod_requested = pyqtSignal()
    # Signal when a rod is assigned/unassigned the pen
    pen_assigned = pyqtSignal(object, bool) # Emits (rod, is_pen_now)
    # Signals for simulation control
    start_simulation_requested = pyqtSignal()
    stop_simulation_requested = pyqtSignal()
    
    # Signal when a parameter is changed (placeholder)
    parameter_changed = pyqtSignal(object, str, object) # component, param_name, value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Container for sections
        container = QWidget()
        container.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.container_layout = QVBoxLayout(container)
        
        # Add sections
        self.wheels_section = CollapsibleSection("Wheels")
        self.rods_section = CollapsibleSection("Rods")
        self.settings_section = CollapsibleSection("Settings")
        self.details_section = CollapsibleSection("Selected Component Details")
        self.details_section.setVisible(False)
        
        self.container_layout.addWidget(self.wheels_section)
        self.container_layout.addWidget(self.rods_section)
        self.container_layout.addWidget(self.details_section)
        self.container_layout.addWidget(self.settings_section)
        
        # Add "Add" buttons to sections
        self._add_wheel_button = QPushButton("Add Wheel")
        wheels_layout = QVBoxLayout() # Create layout for wheel section content
        wheels_layout.addWidget(self._add_wheel_button)
        # TODO: Add wheel list/details placeholders here later
        self.wheels_section.setContentLayout(wheels_layout) # Set layout
        
        self._add_rod_button = QPushButton("Add Rod")
        rods_layout = QVBoxLayout() # Create layout for rod section content
        rods_layout.addWidget(self._add_rod_button)
        # TODO: Add rod list/details placeholders here later
        self.rods_section.setContentLayout(rods_layout) # Set layout
        self._add_rod_button.clicked.connect(self.add_rod_requested.emit)
        
        # Setup details section (placeholders for now)
        self._setup_details_section()
        
        # Add snap settings to settings section
        self._setup_settings()
        
        # --- Add Simulation Controls Section ---
        self.simulation_section = CollapsibleSection("Simulation")
        sim_layout = QVBoxLayout()
        self.start_button = QPushButton("Start Simulation")
        self.stop_button = QPushButton("Stop Simulation")
        self.stop_button.setEnabled(False) # Disabled initially
        sim_layout.addWidget(self.start_button)
        sim_layout.addWidget(self.stop_button)
        self.simulation_section.setContentLayout(sim_layout)
        self.container_layout.addWidget(self.simulation_section)
        # --- End Simulation Controls ---
        
        # Add container to scroll area
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Connect simulation buttons here, after they are created
        self.start_button.clicked.connect(self._handle_start_simulation)
        self.stop_button.clicked.connect(self._handle_stop_simulation)

        # Add stretch to push everything up
        self.container_layout.addStretch()
        
    def _setup_details_section(self):
        # Create the layout that will hold the details
        self.details_layout = QFormLayout()
        # Set this layout onto the content area of the details section
        self.details_section.setContentLayout(self.details_layout)
        # Store references to input widgets
        self.detail_widgets = {}

    def _clear_details_layout(self):
        """Remove all widgets from the details layout."""
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.detail_widgets = {}

    def clear_details(self):
        """Hide the details section and clear its content."""
        self._clear_details_layout()
        self.details_section.setVisible(False)
        print("ParameterPanel: Details cleared") # Debug

    def show_wheel_details(self, wheel: Wheel, components_dict: Dict):
        """Display editable details for the selected wheel."""
        self._clear_details_layout()
        self.details_section.toggle_button.setText(f"Wheel Details (ID: {wheel.id})")

        # Use QDoubleSpinBox for numerical values
        diameter_spin = QDoubleSpinBox()
        diameter_spin.setRange(1.0, 10000.0) # Example range
        diameter_spin.setDecimals(1)
        diameter_spin.setValue(wheel.diameter)
        self.detail_widgets['diameter'] = diameter_spin
        self.details_layout.addRow("Diameter:", diameter_spin)

        center_x_spin = QDoubleSpinBox()
        center_x_spin.setRange(-10000.0, 10000.0) # Example range
        center_x_spin.setDecimals(1)
        center_x_spin.setValue(wheel.center.x())
        self.detail_widgets['center_x'] = center_x_spin
        self.details_layout.addRow("Center X:", center_x_spin)
        
        center_y_spin = QDoubleSpinBox()
        center_y_spin.setRange(-10000.0, 10000.0) # Example range
        center_y_spin.setDecimals(1)
        center_y_spin.setValue(wheel.center.y())
        self.detail_widgets['center_y'] = center_y_spin
        self.details_layout.addRow("Center Y:", center_y_spin)

        speed_ratio_spin = QDoubleSpinBox()
        speed_ratio_spin.setRange(-100.0, 100.0) # Example range
        speed_ratio_spin.setDecimals(2)
        speed_ratio_spin.setValue(wheel.speed_ratio)
        self.detail_widgets['speed_ratio'] = speed_ratio_spin
        self.details_layout.addRow("Speed Ratio:", speed_ratio_spin)

        # --- Connection Point 'p1' Radius ---
        p1_radius_spin = QDoubleSpinBox()
        p1_radius_spin.setRange(0.0, 10000.0) # Radius >= 0
        p1_radius_spin.setDecimals(1)
        p1_radius_spin.setEnabled(False) # Disabled by default
        p1_radius_spin.setToolTip("Radius for connection point 'p1'")
        
        # Check if point 'p1' exists
        if 'p1' in wheel.connection_points:
            p1_radius_spin.setValue(wheel.connection_points['p1'].radius)
            p1_radius_spin.setEnabled(True)
            # Connect signal only if the point exists and is editable
            p1_radius_spin.valueChanged.connect(
                partial(self._handle_value_changed, wheel, 'p1_radius'))
        else:
            p1_radius_spin.setValue(0.0) # Default display value
            
        self.detail_widgets['p1_radius'] = p1_radius_spin
        self.details_layout.addRow("P1 Radius:", p1_radius_spin)

        # TODO: Add UI for managing multiple connection points here
        # For now, remove the old single connection point inputs
        # conn_radius_spin = QDoubleSpinBox()
        # ... (removed code for conn_radius_spin)
        # conn_phase_spin = QDoubleSpinBox()
        # ... (removed code for conn_phase_spin)
        
        # Connect signals (using valueChanged)
        diameter_spin.valueChanged.connect(
            partial(self._handle_value_changed, wheel, 'diameter'))
        center_x_spin.valueChanged.connect(
            partial(self._handle_value_changed, wheel, 'center_x'))
        center_y_spin.valueChanged.connect(
            partial(self._handle_value_changed, wheel, 'center_y'))
        speed_ratio_spin.valueChanged.connect(
            partial(self._handle_value_changed, wheel, 'speed_ratio'))
        # conn_radius_spin.valueChanged.connect(...)
        # conn_phase_spin.valueChanged.connect(...)

        self.details_section.setVisible(True)
        
    def show_rod_details(self, rod: Rod, components_dict: Dict):
        """Display editable details for the selected rod."""
        self._clear_details_layout()
        self.details_section.toggle_button.setText(f"Rod Details (ID: {rod.id})")

        # Use QDoubleSpinBox for numerical values
        length_spin = QDoubleSpinBox() # Maybe make read-only?
        length_spin.setRange(0.0, 10000.0)
        length_spin.setDecimals(1)
        length_spin.setValue(rod.length)
        length_spin.setReadOnly(True) # Length determined by endpoints
        length_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons) # Hide buttons if read-only
        self.detail_widgets['length'] = length_spin
        self.details_layout.addRow("Length:", length_spin)

        start_x_spin = QDoubleSpinBox()
        start_x_spin.setRange(-10000.0, 10000.0)
        start_x_spin.setDecimals(1)
        start_x_spin.setValue(rod.start_pos.x())
        self.detail_widgets['start_x'] = start_x_spin
        self.details_layout.addRow("Start X:", start_x_spin)
        
        start_y_spin = QDoubleSpinBox()
        start_y_spin.setRange(-10000.0, 10000.0)
        start_y_spin.setDecimals(1)
        start_y_spin.setValue(rod.start_pos.y())
        self.detail_widgets['start_y'] = start_y_spin
        self.details_layout.addRow("Start Y:", start_y_spin)
        
        end_x_spin = QDoubleSpinBox()
        end_x_spin.setRange(-10000.0, 10000.0)
        end_x_spin.setDecimals(1)
        end_x_spin.setValue(rod.end_pos.x())
        self.detail_widgets['end_x'] = end_x_spin
        self.details_layout.addRow("End X:", end_x_spin)
        
        end_y_spin = QDoubleSpinBox()
        end_y_spin.setRange(-10000.0, 10000.0)
        end_y_spin.setDecimals(1)
        end_y_spin.setValue(rod.end_pos.y())
        self.detail_widgets['end_y'] = end_y_spin
        self.details_layout.addRow("End Y:", end_y_spin)

        # --- Start/End Connection Display ---
        start_conn_label = QLabel("<Not Connected>")
        start_conn_label.setWordWrap(True)
        if rod.start_connection:
            formatted_conn = _format_connection_target(rod.start_connection, components_dict)
            start_conn_label.setText(formatted_conn if formatted_conn else "<Error>")
        self.details_layout.addRow("Start Conn:", start_conn_label)
        self.detail_widgets['start_conn_label'] = start_conn_label # Store label

        end_conn_label = QLabel("<Not Connected>")
        end_conn_label.setWordWrap(True)
        if rod.end_connection:
            formatted_conn = _format_connection_target(rod.end_connection, components_dict)
            end_conn_label.setText(formatted_conn if formatted_conn else "<Error>")
        self.details_layout.addRow("End Conn:", end_conn_label)
        self.detail_widgets['end_conn_label'] = end_conn_label # Store label

        # --- Mid-point Connection ---
        self.has_mid_point_checkbox = QCheckBox()
        self.mid_dist_spin = QDoubleSpinBox()
        self.mid_dist_spin.setRange(0.0, 10000.0) # Max length? Should update dynamically?
        self.mid_dist_spin.setDecimals(1)
        self.mid_dist_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        
        mid_conn_label = QLabel("N/A") # Default text
        mid_conn_label.setWordWrap(True) # Allow text wrapping
        
        if rod.mid_point_connection:
            target_comp_id, target_point_id = rod.mid_point_connection
            target_comp = components_dict.get(target_comp_id)
            if target_comp:
                comp_type_str = "Wheel" if isinstance(target_comp, Wheel) else "Rod"
                mid_conn_label.setText(f"{comp_type_str} {target_comp_id} :: {target_point_id}")
            else:
                mid_conn_label.setText(f"Missing Comp {target_comp_id}")
        
        if rod.mid_point_distance is not None:
            self.has_mid_point_checkbox.setChecked(True)
            self.mid_dist_spin.setValue(rod.mid_point_distance)
            self.mid_dist_spin.setEnabled(True)
            # Keep mid_conn_label visible if mid_point exists, even if not connected yet
        else:
             self.has_mid_point_checkbox.setChecked(False)
             self.mid_dist_spin.setValue(0.0)
             self.mid_dist_spin.setEnabled(False)
             mid_conn_label.setText("N/A") # Explicitly set back to N/A if no mid-point
        
        self.detail_widgets['has_mid_point'] = self.has_mid_point_checkbox
        self.detail_widgets['mid_dist_spin'] = self.mid_dist_spin 
        self.detail_widgets['mid_conn_label'] = mid_conn_label # Store label if needed

        self.details_layout.addRow("Has Mid-Point:", self.has_mid_point_checkbox)
        self.details_layout.addRow("Mid Dist:", self.mid_dist_spin)
        self.details_layout.addRow("Mid Conn:", mid_conn_label)
        
        # --- Pen Position ---
        self.has_pen_checkbox = QCheckBox()
        self.pen_distance_spin = QDoubleSpinBox()
        self.pen_distance_spin.setRange(0.0, 10000.0) # Can be anywhere along length
        self.pen_distance_spin.setDecimals(1)
        self.pen_distance_spin.setEnabled(False) # Disabled by default
        
        if rod.pen_distance_from_start is not None:
            self.has_pen_checkbox.setChecked(True)
            self.pen_distance_spin.setValue(rod.pen_distance_from_start)
            self.pen_distance_spin.setEnabled(True)
        else:
             self.has_pen_checkbox.setChecked(False)
             self.pen_distance_spin.setValue(0.0) # Default value when no pen
             self.pen_distance_spin.setEnabled(False)

        self.detail_widgets['has_pen'] = self.has_pen_checkbox
        self.detail_widgets['pen_distance_from_start'] = self.pen_distance_spin
        self.details_layout.addRow("Has Pen:", self.has_pen_checkbox)
        self.details_layout.addRow("Pen Distance:", self.pen_distance_spin)

        # Connect signals
        start_x_spin.valueChanged.connect(
            partial(self._handle_value_changed, rod, 'start_x'))
        start_y_spin.valueChanged.connect(
            partial(self._handle_value_changed, rod, 'start_y'))
        end_x_spin.valueChanged.connect(
            partial(self._handle_value_changed, rod, 'end_x'))
        end_y_spin.valueChanged.connect(
            partial(self._handle_value_changed, rod, 'end_y'))
        # Connect pen signals
        self.has_pen_checkbox.toggled.connect(
            partial(self._handle_pen_toggled, rod))
        self.pen_distance_spin.valueChanged.connect(
            partial(self._handle_value_changed, rod, 'pen_distance_from_start'))
        # Connect mid-point distance signal
        self.mid_dist_spin.valueChanged.connect(
            partial(self._handle_value_changed, rod, 'mid_point_distance'))
        # Connect mid-point checkbox signal
        self.has_mid_point_checkbox.toggled.connect(
            partial(self._handle_mid_point_toggled, rod))

        self.details_section.setVisible(True)

    def _handle_value_changed(self, component, param_name, value):
        # Update the component's attribute directly
        if param_name == 'center_x':
            center = component.center
            component.center = QPointF(value, center.y())
        elif param_name == 'center_y':
            center = component.center
            component.center = QPointF(center.x(), value)
        elif param_name == 'start_x':
            start = component.start_pos
            component.start_pos = QPointF(value, start.y())
        elif param_name == 'start_y':
            start = component.start_pos
            component.start_pos = QPointF(start.x(), value)
        elif param_name == 'end_x':
            end = component.end_pos
            component.end_pos = QPointF(value, end.y())
        elif param_name == 'end_y':
            end = component.end_pos
            component.end_pos = QPointF(end.x(), value)
        elif param_name == 'pen_distance_from_start':
            # Explicitly handle pen distance to ensure it's properly updated
            if hasattr(component, 'pen_distance_from_start'):
                component.pen_distance_from_start = float(value)
        else:
            # For simple attributes like mid_point_distance, etc.
            setattr(component, param_name, value)
        
        # Then emit the parameter_changed signal
        self.parameter_changed.emit(component, param_name, value)
        
    def _handle_pen_toggled(self, rod: Rod, checked: bool):
        """Handle the 'Has Pen' checkbox being toggled."""
        print(f"Pen toggled for Rod {rod.id}: {checked}")
        self.pen_distance_spin.setEnabled(checked)
        
        if checked:
            # Assign pen to this rod
            # Set default distance if current is None (or maybe 0?)
            current_dist = rod.pen_distance_from_start
            if current_dist is None:
                default_dist = rod.length / 2.0 # Default to midpoint
                rod.pen_distance_from_start = default_dist
                self.pen_distance_spin.setValue(default_dist)
            else:
                 self.pen_distance_spin.setValue(current_dist) # Ensure spinbox matches
                 
            # Emit signal to notify MainWindow to clear other pens
            self.pen_assigned.emit(rod, True)
            self.parameter_changed.emit(rod, 'pen_distance_from_start', rod.pen_distance_from_start)
        else:
            # Remove pen from this rod
            rod.pen_distance_from_start = None
            # Emit signal to notify the change
            self.pen_assigned.emit(rod, False)
            self.parameter_changed.emit(rod, 'pen_distance_from_start', None)
        
    def _handle_mid_point_toggled(self, rod: Rod, checked: bool):
        """Handle the 'Has Mid-Point' checkbox being toggled."""
        print(f"Mid-point toggled for Rod {rod.id}: {checked}")
        self.mid_dist_spin.setEnabled(checked)
        
        new_distance = None
        if checked:
            # If activating mid-point, set default distance if needed
            current_dist = rod.mid_point_distance
            if current_dist is None:
                default_dist = rod.length / 2.0 # Default to midpoint
                rod.mid_point_distance = default_dist
                self.mid_dist_spin.setValue(default_dist) # Update UI
                new_distance = default_dist
            else:
                # Ensure spinbox matches existing value when enabling
                self.mid_dist_spin.setValue(current_dist)
                new_distance = current_dist
        else:
            # If deactivating, set distance to None
            rod.mid_point_distance = None
            new_distance = None 
            # Optionally reset spinbox value to 0 when disabled
            # self.mid_dist_spin.setValue(0.0) 
            
        # Emit the change (including None)
        self.parameter_changed.emit(rod, 'mid_point_distance', new_distance)

    def _setup_settings(self):
        # Create layout for settings content
        settings_layout = QVBoxLayout()
        
        # Add grid snap settings
        snap_label = QLabel("Grid Snap:")
        settings_layout.addWidget(snap_label) # Add to layout
        
        # Create button group for snap buttons
        self.snap_button_group = QButtonGroup(self)
        self.snap_button_group.setExclusive(True)
        
        # Add snap buttons with their values stored
        snap_values = [1, 5, 10]
        for snap in snap_values:
            btn = QPushButton(f"{snap}mm")
            btn.setCheckable(True)
            btn.setProperty("snap_value", snap)  # Store the actual value
            settings_layout.addWidget(btn) # Add to layout
            self.snap_button_group.addButton(btn)
            
        # Set default selection to 1mm
        first_button = self.snap_button_group.buttons()[0]
        first_button.setChecked(True)
        
        # Connect button group
        self.snap_button_group.buttonClicked.connect(self._on_snap_button_clicked)
        
        # Add master speed control (we'll implement this later)
        speed_label = QLabel("Master Speed:")
        settings_layout.addWidget(speed_label) # Add to layout
        
        # Set the created layout to the settings section
        self.settings_section.setContentLayout(settings_layout)

    def _on_snap_button_clicked(self, button):
        """Handle snap button clicks"""
        snap_value = button.property("snap_value")
        self.snap_changed.emit(snap_value) 

    def _handle_start_simulation(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.start_simulation_requested.emit()

    def _handle_stop_simulation(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.stop_simulation_requested.emit() 