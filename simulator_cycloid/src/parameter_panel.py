from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
                               QPushButton, QFrame, QScrollArea, QButtonGroup, QFormLayout, QSizePolicy, QLayout, QCheckBox, QSpinBox, QHBoxLayout, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QFocusEvent, QPalette, QColor
from components import Wheel, Rod
from typing import Optional, Dict, Tuple, Union
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

class CollapsibleSection(QFrame):
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
        self.content_area.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
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
        
    def setContentWidget(self, widget: QWidget):
        """Sets a widget as the content for the content area."""
        # Check if content_area already has a layout
        # If so, we should set the new widget into that layout?
        # Or assume content_area should hold ONE widget directly?
        # For simplicity, let's assume content_area uses a simple layout (e.g., QVBoxLayout)
        # to hold the provided widget. We'll create this layout if it doesn't exist.
        
        content_layout = self.content_area.layout()
        if content_layout is None:
            content_layout = QVBoxLayout(self.content_area) # Create a layout if none exists
            content_layout.setContentsMargins(0, 0, 0, 0)
            self.content_area.setLayout(content_layout)

        # Clear previous widgets from the layout
        while content_layout.count():
            item = content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Add the new widget
        content_layout.addWidget(widget)
        self.content_area.adjustSize()
        self.content_area.setVisible(self.toggle_button.isChecked())
        
    def _toggle_content(self, checked):
        self.content_area.setVisible(checked)
        # Request layout update (this might still be useful)
        # Let the parent layout know things might have changed size
        if self.parentWidget() and self.parentWidget().layout():
             self.parentWidget().layout().activate()

class ParameterPanel(QFrame):
    # Signal when snap size changes
    snap_changed = pyqtSignal(int)
    # Signal when add rod button is clicked
    add_rod_requested = pyqtSignal()
    # Signal when a rod is assigned/unassigned the pen
    pen_assigned = pyqtSignal(int, bool) # Emits (rod_id, is_pen_now)
    # Signals for simulation control
    start_simulation_requested = pyqtSignal()
    stop_simulation_requested = pyqtSignal()
    
    # Signal when a parameter is changed (placeholder)
    parameter_changed = pyqtSignal(object, str, object) # component, param_name, value
    
    # Signal for image generation
    image_generate_requested = pyqtSignal(str, int, int, str, int) # filename, w, h, color, line_width
    # Signal to add canvas wheel
    add_canvas_requested = pyqtSignal()
    
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
        
        # Add Canvas Button
        self._add_canvas_button = QPushButton("Add Canvas")
        self._add_canvas_button.clicked.connect(self.add_canvas_requested.emit) # Emit signal
        wheels_layout.addWidget(self._add_canvas_button)
        
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

        # --- Add Image Generation Section --- 
        self.image_gen_section = CollapsibleSection("Image Generation")
        image_gen_form_layout = QFormLayout()
        
        self.image_filename_edit = QLineEdit("cycloid_pattern.png")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_filename)
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(self.image_filename_edit)
        filename_layout.addWidget(self.browse_button)
        image_gen_form_layout.addRow("Filename:", filename_layout)
        
        self.image_width_spin = QSpinBox()
        self.image_width_spin.setRange(100, 8000)
        self.image_width_spin.setValue(1920)
        image_gen_form_layout.addRow("Width (px):", self.image_width_spin)
        
        self.image_height_spin = QSpinBox()
        self.image_height_spin.setRange(100, 8000)
        self.image_height_spin.setValue(1080)
        image_gen_form_layout.addRow("Height (px):", self.image_height_spin)
        
        self.image_line_width_spin = QSpinBox()
        self.image_line_width_spin.setRange(1, 20)
        self.image_line_width_spin.setValue(1)
        image_gen_form_layout.addRow("Line Width (px):", self.image_line_width_spin)
        
        self._generate_image_button = QPushButton("Generate Image")
        self._generate_image_button.clicked.connect(self._on_generate_image)
        image_gen_form_layout.addRow(self._generate_image_button) # Add button to form layout
        
        self.image_gen_section.setContentLayout(image_gen_form_layout) # Set the form layout on the section
        self.container_layout.addWidget(self.image_gen_section) # Add section to the main container
        # --- End Image Generation Section ---
        
        # Add container to scroll area
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Connect simulation buttons here, after they are created
        self.start_button.clicked.connect(self._handle_start_simulation)
        self.stop_button.clicked.connect(self._handle_stop_simulation)

        # Add stretch to push everything up
        self.container_layout.addStretch()
        
        # Store references to input widgets
        self.detail_widgets = {}
        self.components_dict: Dict[int, Union[Wheel, Rod]] = {} # Add initialization

    def _setup_details_section(self):
        # This method no longer needs to create the layout itself.
        # The show_..._details methods will create the layout and content widget.
        # We just ensure the content_area exists within the details_section.
        pass # Remove old layout creation
        # self.details_layout = QFormLayout()
        # self.details_section.setContentLayout(self.details_layout)

    def _clear_details_layout(self):
        """Remove the existing content widget from the details section."""
        # Find the current content widget in the details section's content area
        content_layout = self.details_section.content_area.layout()
        if content_layout and content_layout.count() > 0:
            item = content_layout.takeAt(0)
            if item and item.widget():
                widget = item.widget()
                widget.deleteLater()
        # Clear the reference dictionary too
        self.detail_widgets = {}

    def clear_details(self):
        """Hide the details section and clear its content."""
        self._clear_details_layout()
        self.details_section.setVisible(False)
        print("ParameterPanel: Details cleared") # Debug

    def show_wheel_details(self, wheel: Wheel, components_dict: Dict):
        """Display editable details for the selected wheel."""
        try:
            self._clear_details_layout() # Clear old content widget
            self.update_components_dict(components_dict) # Ensure dict is updated
            self.details_section.toggle_button.setText(f"Wheel Details (ID: {wheel.id})")

            # Create a new container widget and layout for the details
            detail_container = QWidget()
            new_layout = QFormLayout(detail_container) # Set layout on container
            self.detail_widgets = {} # Reset detail widgets dict

            # --- Populate new_layout --- 
            diameter_spin = QDoubleSpinBox()
            diameter_spin.setRange(1.0, 10000.0)
            diameter_spin.setDecimals(1)
            diameter_spin.setValue(wheel.diameter)
            self.detail_widgets['diameter'] = diameter_spin
            new_layout.addRow("Diameter:", diameter_spin)

            center_x_spin = QDoubleSpinBox()
            center_x_spin.setRange(-10000.0, 10000.0)
            center_x_spin.setDecimals(1)
            center_x_spin.setValue(wheel.center.x())
            self.detail_widgets['center_x'] = center_x_spin
            new_layout.addRow("Center X:", center_x_spin)
            
            center_y_spin = QDoubleSpinBox()
            center_y_spin.setRange(-10000.0, 10000.0)
            center_y_spin.setDecimals(1)
            center_y_spin.setValue(wheel.center.y())
            self.detail_widgets['center_y'] = center_y_spin
            new_layout.addRow("Center Y:", center_y_spin)

            speed_ratio_spin = QDoubleSpinBox()
            speed_ratio_spin.setRange(-100.0, 100.0)
            speed_ratio_spin.setDecimals(2)
            speed_ratio_spin.setValue(wheel.speed_ratio)
            self.detail_widgets['speed_ratio'] = speed_ratio_spin
            new_layout.addRow("Speed Ratio:", speed_ratio_spin)

            rotation_rate_spin = QDoubleSpinBox()
            rotation_rate_spin.setRange(-1000.0, 1000.0)
            rotation_rate_spin.setDecimals(1)
            rotation_rate_spin.setValue(wheel.rotation_rate)
            self.detail_widgets['rotation_rate'] = rotation_rate_spin
            new_layout.addRow("Rotation Rate (°/s):", rotation_rate_spin)

            # --- Connection Point 'p1' Radius ---
            p1_radius_spin = QDoubleSpinBox()
            p1_radius_spin.setRange(0.0, 10000.0)
            p1_radius_spin.setDecimals(1)
            p1_radius_spin.setEnabled(False)
            p1_radius_spin.setToolTip("Radius for connection point 'p1'")
            if 'p1' in wheel.connection_points:
                p1_radius_spin.setValue(wheel.connection_points['p1'].radius)
                p1_radius_spin.setEnabled(True)
                p1_radius_spin.valueChanged.connect(
                    partial(self._handle_value_changed, wheel, 'p1_radius'))
            else:
                p1_radius_spin.setValue(0.0)
            self.detail_widgets['p1_radius'] = p1_radius_spin
            new_layout.addRow("P1 Radius:", p1_radius_spin)

            # Connect signals 
            diameter_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'diameter'))
            center_x_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'center_x'))
            center_y_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'center_y'))
            speed_ratio_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'speed_ratio'))
            rotation_rate_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'rotation_rate'))
            # --- End Populate --- 

            # Set the new widget as the content for the details section
            self.details_section.setContentWidget(detail_container)
            self.details_section.setVisible(True)
            
        except Exception as e:
            print(f"ERROR building wheel details UI for {wheel.id}: {e}")
            import traceback
            traceback.print_exc()
            # Optionally hide section or show error message in UI
            self.details_section.setVisible(False)
            # Remove previous attempts
            # self.details_layout.activate()
            # self.details_section.adjustSize()
            # Try updating the content_area within the section
            self.details_section.content_area.adjustSize()
            self.details_section.content_area.update()

    def show_rod_details(self, rod: Rod, components_dict: Dict):
        """Display editable details for the selected rod."""
        try:
            self._clear_details_layout() # Clear old content widget
            self.update_components_dict(components_dict) 
            self.details_section.toggle_button.setText(f"Rod Details (ID: {rod.id})")

            # Create a new container widget and layout for the details
            detail_container = QWidget()
            new_layout = QFormLayout(detail_container) # Set layout on container
            self.detail_widgets = {} # Reset detail widgets dict

            # --- Populate new_layout --- 
            length_spin = QDoubleSpinBox()
            length_spin.setRange(0.0, 10000.0)
            length_spin.setDecimals(1)
            length_spin.setValue(rod.length)
            length_spin.setReadOnly(True)
            length_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            self.detail_widgets['length'] = length_spin
            new_layout.addRow("Length:", length_spin)

            start_x_spin = QDoubleSpinBox()
            start_x_spin.setRange(-10000.0, 10000.0)
            start_x_spin.setDecimals(1)
            start_x_spin.setValue(rod.start_pos.x())
            self.detail_widgets['start_x'] = start_x_spin
            new_layout.addRow("Start X:", start_x_spin)
            
            start_y_spin = QDoubleSpinBox()
            start_y_spin.setRange(-10000.0, 10000.0)
            start_y_spin.setDecimals(1)
            start_y_spin.setValue(rod.start_pos.y())
            self.detail_widgets['start_y'] = start_y_spin
            new_layout.addRow("Start Y:", start_y_spin)
            
            end_x_spin = QDoubleSpinBox()
            end_x_spin.setRange(-10000.0, 10000.0)
            end_x_spin.setDecimals(1)
            end_x_spin.setValue(rod.end_pos.x())
            self.detail_widgets['end_x'] = end_x_spin
            new_layout.addRow("End X:", end_x_spin)
            
            end_y_spin = QDoubleSpinBox()
            end_y_spin.setRange(-10000.0, 10000.0)
            end_y_spin.setDecimals(1)
            end_y_spin.setValue(rod.end_pos.y())
            self.detail_widgets['end_y'] = end_y_spin
            new_layout.addRow("End Y:", end_y_spin)

            # Start/End Connection Display 
            start_conn_label = QLabel("<Not Connected>")
            start_conn_label.setWordWrap(True)
            if rod.start_connection:
                formatted_conn = _format_connection_target(rod.start_connection, components_dict)
                start_conn_label.setText(formatted_conn if formatted_conn else "<Error>")
            new_layout.addRow("Start Conn:", start_conn_label)
            self.detail_widgets['start_conn_label'] = start_conn_label

            end_conn_label = QLabel("<Not Connected>")
            end_conn_label.setWordWrap(True)
            if rod.end_connection:
                formatted_conn = _format_connection_target(rod.end_connection, components_dict)
                end_conn_label.setText(formatted_conn if formatted_conn else "<Error>")
            new_layout.addRow("End Conn:", end_conn_label)
            self.detail_widgets['end_conn_label'] = end_conn_label

            # Mid-point Connection 
            has_mid_point_checkbox = QCheckBox()
            mid_dist_spin = QDoubleSpinBox()
            mid_dist_spin.setRange(0.0, 10000.0) 
            mid_dist_spin.setDecimals(1)
            mid_dist_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            mid_conn_label = QLabel("N/A")
            mid_conn_label.setWordWrap(True)
            if rod.mid_point_connection:
                target_comp_id, target_point_id = rod.mid_point_connection
                target_comp = components_dict.get(target_comp_id)
                if target_comp:
                    comp_type_str = "Wheel" if isinstance(target_comp, Wheel) else "Rod"
                    mid_conn_label.setText(f"{comp_type_str} {target_comp_id} :: {target_point_id}")
                else:
                    mid_conn_label.setText(f"Missing Comp {target_comp_id}")
            if rod.mid_point_distance is not None:
                has_mid_point_checkbox.setChecked(True)
                mid_dist_spin.setValue(rod.mid_point_distance)
                mid_dist_spin.setEnabled(True)
            else:
                 has_mid_point_checkbox.setChecked(False)
                 mid_dist_spin.setValue(0.0)
                 mid_dist_spin.setEnabled(False)
                 mid_conn_label.setText("N/A")
            self.detail_widgets['has_mid_point'] = has_mid_point_checkbox
            self.detail_widgets['mid_dist_spin'] = mid_dist_spin 
            self.detail_widgets['mid_conn_label'] = mid_conn_label
            new_layout.addRow("Has Mid-Point:", has_mid_point_checkbox)
            new_layout.addRow("Mid Dist:", mid_dist_spin)
            new_layout.addRow("Mid Conn:", mid_conn_label)
            
            # Pen Position 
            has_pen_checkbox = QCheckBox()
            pen_distance_spin = QDoubleSpinBox()
            pen_distance_spin.setRange(0.0, 10000.0)
            pen_distance_spin.setDecimals(1)
            pen_distance_spin.setEnabled(False)
            if rod.pen_distance_from_start is not None:
                has_pen_checkbox.setChecked(True)
                pen_distance_spin.setValue(rod.pen_distance_from_start)
                pen_distance_spin.setEnabled(True)
            else:
                 has_pen_checkbox.setChecked(False)
                 pen_distance_spin.setValue(0.0)
                 pen_distance_spin.setEnabled(False)
            self.detail_widgets['has_pen'] = has_pen_checkbox
            self.detail_widgets['pen_distance_from_start'] = pen_distance_spin
            new_layout.addRow("Has Pen:", has_pen_checkbox)
            new_layout.addRow("Pen Distance:", pen_distance_spin)

            # Connect signals
            start_x_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'start_x'))
            start_y_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'start_y'))
            end_x_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'end_x'))
            end_y_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'end_y'))
            has_pen_checkbox.toggled.connect(partial(self._handle_pen_toggled, rod))
            pen_distance_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'pen_distance_from_start'))
            mid_dist_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'mid_point_distance'))
            has_mid_point_checkbox.toggled.connect(partial(self._handle_mid_point_toggled, rod))
            # --- End Populate ---

            # Set the new widget as the content for the details section
            self.details_section.setContentWidget(detail_container)
            self.details_section.setVisible(True)

        except Exception as e:
            print(f"ERROR building rod details UI for {rod.id}: {e}")
            import traceback
            traceback.print_exc()
            # Optionally hide section or show error message in UI
            self.details_section.setVisible(False)
            # Remove previous attempts
            # self.details_layout.activate()
            # self.details_section.adjustSize()
            # Try updating the content_area within the section
            self.details_section.content_area.adjustSize()
            self.details_section.content_area.update()

    def _handle_value_changed(self, component, property_name, value):
        """Generic handler for parameter changes in the details panel."""
        # Find the actual component from the stored reference
        actual_component = None
        if hasattr(component, 'id') and component.id in self.components_dict:
            actual_component = self.components_dict[component.id]
        else:
            print(f"Warning: Component {component} not found in dict during update.")
            return # Cannot update if component reference is stale

        # *** REMOVED direct component updates from ParameterPanel ***
        # ParameterPanel should only emit the signal with the new value.
        # MainWindow is responsible for applying the change to the component model.
        
        # Just emit the signal with the component reference, property name, and NEW value from the UI
        if actual_component:
             try:
                 # Special case: emit 'propagate_constraints' if needed
                 propagate_needed = property_name in ('center_x', 'center_y', 'p1_radius', 'start_x', 'start_y', 'end_x', 'end_y') 
                 # Special handling for diameter affecting p1 radius propagation is complex here,
                 # let MainWindow handle that logic after receiving the basic diameter change signal.
                 
                 # Emit the basic parameter change signal
                 self.parameter_changed.emit(actual_component, property_name, value)

                 # If propagation is needed based on the property name, emit that signal too
                 # Note: MainWindow will need the original position to know *what* moved.
                 # This might require rethinking how propagation is triggered.
                 # For now, let's rely on MainWindow handling propagation based on param_name.
                 # if propagate_needed:
                 #     # We don't have original_pos here easily anymore.
                 #     # MainWindow._on_parameter_changed should handle propagation logic.
                 #     # self.parameter_changed.emit(actual_component, 'propagate_constraints', ...) 
                 pass

             except Exception as e:
                 print(f"Error emitting parameter change signal for {property_name}: {e}")
        
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
            self.pen_assigned.emit(rod.id, True)
            self.parameter_changed.emit(rod, 'pen_distance_from_start', rod.pen_distance_from_start)
        else:
            # Remove pen from this rod
            rod.pen_distance_from_start = None
            # Emit signal to notify the change
            self.pen_assigned.emit(rod.id, False)
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

    def update_components_dict(self, components: Dict[int, Union[Wheel, Rod]]):
        """Update the internal reference to the components dictionary."""
        self.components_dict = components
        
    def _browse_filename(self):
        """Open a file dialog to select the image save path."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Image As",
            self.image_filename_edit.text(),
            "PNG Images (*.png);;JPEG Images (*.jpg *.jpeg);;All Files (*)"
        )
        if filename:
            self.image_filename_edit.setText(filename)
            
    def _on_generate_image(self):
        """Emit signal to request image generation."""
        filename = self.image_filename_edit.text()
        width = self.image_width_spin.value()
        height = self.image_height_spin.value()
        line_width = self.image_line_width_spin.value()
        line_color = "black" # Hardcoded for now
        
        if filename:
            self.image_generate_requested.emit(filename, width, height, line_color, line_width)
        else:
            print("Error: Please specify a filename for the image.")
            # Optionally show a message box to the user
        