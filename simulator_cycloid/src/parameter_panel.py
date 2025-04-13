from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
                               QPushButton, QFrame, QScrollArea, QButtonGroup, QFormLayout, QSizePolicy, QLayout, QCheckBox, QSpinBox, QHBoxLayout, QFileDialog,
                               QGroupBox, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QFocusEvent, QPalette, QColor
from components import Wheel, Rod
from typing import Optional, Dict, Tuple, Union
from functools import partial
import math # <-- Ensure math is imported

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
    image_generate_requested = pyqtSignal(str, int, int, str, int, float) # filename, w, h, color, line_width, duration_seconds
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
        
        # --- Create Sections as QGroupBoxes --- 
        self.wheels_section = QGroupBox("Wheels")
        self.wheels_section.setCheckable(True)
        self.wheels_section.setChecked(True)
        # self.wheels_section.toggled.connect(self._handle_section_toggled) # Connect later
        
        self.rods_section = QGroupBox("Rods")
        self.rods_section.setCheckable(True)
        self.rods_section.setChecked(True)
        self.rods_section.toggled.connect(self._handle_section_toggled)

        self.details_section = QGroupBox("No Component Selected")
        self.details_section.setCheckable(True)
        self.details_section.setVisible(True)
        # self.details_section.toggled.connect(self._handle_section_toggled)
        
        self.settings_section = QGroupBox("Settings")
        self.settings_section.setCheckable(True)
        self.settings_section.setChecked(True)
        self.settings_section.toggled.connect(self._handle_section_toggled)

        self.simulation_section = QGroupBox("Simulation")
        self.simulation_section.setCheckable(True)
        self.simulation_section.setChecked(True)
        self.simulation_section.toggled.connect(self._handle_section_toggled)
        
        self.image_gen_section = QGroupBox("Image Generation")
        self.image_gen_section.setCheckable(True)
        self.image_gen_section.setChecked(True)
        self.image_gen_section.toggled.connect(self._handle_section_toggled)
        # --- End Create Sections --- 
        
        self.container_layout.addWidget(self.wheels_section)
        self.container_layout.addWidget(self.rods_section)
        self.container_layout.addWidget(self.details_section)
        self.container_layout.addWidget(self.settings_section)
        self.container_layout.addWidget(self.simulation_section)
        self.container_layout.addWidget(self.image_gen_section)

        # --- Add Content to Sections --- 
        # Wheels Section
        wheels_layout = QVBoxLayout()
        self._add_wheel_button = QPushButton("Add Wheel")
        self._add_canvas_button = QPushButton("Add Canvas")
        wheels_layout.addWidget(self._add_wheel_button)
        wheels_layout.addWidget(self._add_canvas_button)
        self.wheels_section.setLayout(wheels_layout) # Set layout on GroupBox
        self._add_canvas_button.clicked.connect(self.add_canvas_requested.emit)

        # Rods Section
        rods_layout = QVBoxLayout()
        self._add_rod_button = QPushButton("Add Rod")
        rods_layout.addWidget(self._add_rod_button)
        self.rods_section.setLayout(rods_layout)
        self._add_rod_button.clicked.connect(self.add_rod_requested.emit)
        
        # Details Section - Setup deferred to show_... methods
        self._setup_details_section() # This will now do nothing
        
        # Settings Section
        self._setup_settings() # This existing method needs adapting slightly
        
        # Simulation Section
        sim_layout = QVBoxLayout()
        self.start_button = QPushButton("Start Simulation")
        self.stop_button = QPushButton("Stop Simulation")
        self.stop_button.setEnabled(False)
        sim_layout.addWidget(self.start_button)
        sim_layout.addWidget(self.stop_button)
        self.simulation_section.setLayout(sim_layout)

        # Image Generation Section
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
        
        # --- Duration Input (Seconds) --- 
        self.simulation_duration_spin = QDoubleSpinBox()
        self.simulation_duration_spin.setRange(0.1, 3600 * 24) # 0.1s to 24 hours
        self.simulation_duration_spin.setDecimals(1)
        self.simulation_duration_spin.setSingleStep(10.0)
        self.simulation_duration_spin.setValue(60.0) # Default to 60 seconds
        self.simulation_duration_label = QLabel("--:--:--") # Placeholder for HH:MM:SS
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(self.simulation_duration_spin)
        duration_layout.addWidget(self.simulation_duration_label)
        image_gen_form_layout.addRow("Duration (s):", duration_layout)
        # Connect valueChanged signal to update the label
        self.simulation_duration_spin.valueChanged.connect(self._update_duration_display)
        self._update_duration_display(self.simulation_duration_spin.value()) # Initial display
        # --- End Duration Input ---
        
        self.image_line_width_spin = QSpinBox()
        self.image_line_width_spin.setRange(1, 20)
        self.image_line_width_spin.setValue(1)
        image_gen_form_layout.addRow("Line Width (px):", self.image_line_width_spin)
        self._generate_image_button = QPushButton("Generate Image")
        self._generate_image_button.clicked.connect(self._on_generate_image)
        image_gen_form_layout.addRow(self._generate_image_button)
        self.image_gen_section.setLayout(image_gen_form_layout)
        # --- End Add Content --- 
        
        # Add container to scroll area
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Connect simulation buttons here, after they are created
        self.start_button.clicked.connect(self._handle_start_simulation)
        self.stop_button.clicked.connect(self._handle_stop_simulation)

        # Add stretch to push everything up
        # self.container_layout.addStretch() # <-- COMMENTED OUT
        
        # Store references to input widgets
        self.detail_widgets = {}
        self.components_dict: Dict[int, Union[Wheel, Rod]] = {} # Add initialization

    def _setup_details_section(self):
        """Create the persistent layout for the details section."""
        # Create the layout ONCE
        self.details_layout = QFormLayout()
        # Set this layout onto the details section GroupBox
        self.details_section.setLayout(self.details_layout)

    def _clear_details_layout(self):
        """Remove all rows from the persistent details layout."""
        if self.details_layout is not None:
            # Remove rows one by one, deleting widgets
            while self.details_layout.count():
                # QFormLayout has labelItem and fieldItem per row
                # We need to remove the row and delete associated widgets
                self.details_layout.removeRow(0) # This should handle deleting widgets? Check Qt docs.
                # Safer alternative: Iterate through items, get widgets, delete, then removeRow.
                # item_label = self.details_layout.itemAt(0, QFormLayout.ItemRole.LabelRole)
                # item_field = self.details_layout.itemAt(0, QFormLayout.ItemRole.FieldRole)
                # if item_label and item_label.widget(): item_label.widget().deleteLater()
                # if item_field and item_field.widget(): item_field.widget().deleteLater()
                # self.details_layout.removeRow(0) 
            
        # Clear the reference dictionary too
        self.detail_widgets = {}

    def clear_details(self):
        """Hide the details section and clear its content."""
        self._clear_details_layout()
        self.details_section.setTitle("No Component Selected") # <-- Set title
        # self.details_section.setVisible(False) # <-- REMOVE
        # Optionally add a placeholder widget/label?
        # placeholder_label = QLabel("Click a component to see details.")
        # placeholder_layout = QVBoxLayout()
        # placeholder_layout.addWidget(placeholder_label)
        # self.details_section.setLayout(placeholder_layout)
        self.details_section.updateGeometry() # Ask it to update size
        print("ParameterPanel: Details cleared, section remains visible") # Debug

    def show_wheel_details(self, wheel: Wheel, components_dict: Dict):
        """Display editable details for the selected wheel."""
        print(f"DEBUG: ParameterPanel.show_wheel_details called for wheel ID: {wheel.id}") # <-- ADD DEBUG PRINT
        try:
            self._clear_details_layout() # Clear old layout from details section
            self.update_components_dict(components_dict) 
            self.details_section.setTitle(f"Wheel Details (ID: {wheel.id})") # Use setTitle

            # Use the persistent layout: self.details_layout
            # new_layout = QFormLayout() # <-- REMOVE
            self.detail_widgets = {} # Reset dict

            # --- Populate self.details_layout --- 
            diameter_spin = QDoubleSpinBox()
            diameter_spin.setRange(1.0, 10000.0)
            diameter_spin.setDecimals(1)
            diameter_spin.setValue(wheel.diameter)
            self.detail_widgets['diameter'] = diameter_spin # Store reference if needed by handlers
            self.details_layout.addRow("Diameter:", diameter_spin)

            center_x_spin = QDoubleSpinBox()
            center_x_spin.setRange(-10000.0, 10000.0)
            center_x_spin.setDecimals(1)
            center_x_spin.setValue(wheel.center.x())
            self.detail_widgets['center_x'] = center_x_spin
            self.details_layout.addRow("Center X:", center_x_spin)
            
            center_y_spin = QDoubleSpinBox()
            center_y_spin.setRange(-10000.0, 10000.0)
            center_y_spin.setDecimals(1)
            center_y_spin.setValue(wheel.center.y())
            self.detail_widgets['center_y'] = center_y_spin
            self.details_layout.addRow("Center Y:", center_y_spin)

            speed_ratio_spin = QDoubleSpinBox()
            speed_ratio_spin.setRange(-100.0, 100.0)
            speed_ratio_spin.setDecimals(2)
            speed_ratio_spin.setValue(wheel.speed_ratio)
            self.detail_widgets['speed_ratio'] = speed_ratio_spin
            self.details_layout.addRow("Speed Ratio:", speed_ratio_spin)

            # Rotation Rate (RPM) - Input as text (QLineEdit), store as rad/s internally
            rpm_edit = QLineEdit()
            # Convert internal rad/s to RPM for display
            rpm_display = wheel.rotation_rate * 60 / (2 * math.pi) 
            rpm_edit.setText(f"{rpm_display:.4f}") # Display with some precision
            self.detail_widgets['rotation_rate'] = rpm_edit
            # Use editingFinished for less frequent updates, or textChanged for instant feedback
            rpm_edit.editingFinished.connect(partial(self._handle_rpm_changed, wheel, rpm_edit))
            self.details_layout.addRow("Rotation Rate (RPM):", rpm_edit)

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
            self.details_layout.addRow("P1 Radius:", p1_radius_spin)

            # Connect signals 
            diameter_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'diameter'))
            center_x_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'center_x'))
            center_y_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'center_y'))
            speed_ratio_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'speed_ratio'))
            rpm_edit.editingFinished.connect(partial(self._handle_rpm_changed, wheel, rpm_edit))
            # --- End Populate --- 

            # No need to set layout again, just update
            # self.details_section.setLayout(new_layout)
            self.details_section.adjustSize() 
            self.details_section.update() 
            
            # --- DIAGNOSTIC PRINTS --- 
            print(f"  Details section visible: {self.details_section.isVisible()}")
            print(f"  Details section title: {self.details_section.title()}")
            print(f"  Details section layout widget count: {self.details_section.layout().count()}")
            print(f"  Details section sizeHint: {self.details_section.sizeHint()}")
            print(f"  Details section minimumSizeHint: {self.details_section.minimumSizeHint()}")
            # --- END DIAGNOSTIC PRINTS ---
            
        except Exception as e:
            print(f"ERROR building wheel details UI for {wheel.id}: {e}")
            import traceback
            traceback.print_exc()
            self.details_section.setVisible(False) # Hide on error
            self.details_section.setTitle("Error Loading Details") # Set error title
            # Remove potentially broken layout?
            old_layout = self.details_section.layout()
            if old_layout is not None:
                QWidget().setLayout(old_layout)
                old_layout.deleteLater()

    def _handle_rpm_changed(self, component: Wheel, line_edit: QLineEdit):
        """Parse RPM input, convert to rad/s, and emit parameter_changed."""
        input_text = line_edit.text().strip()
        try:
            rpm_value = 0.0
            if '/' in input_text:
                # Try parsing as a fraction
                parts = input_text.split('/')
                if len(parts) == 2:
                    num = float(parts[0].strip())
                    den = float(parts[1].strip())
                    if den == 0:
                        raise ValueError("Division by zero in RPM fraction.")
                    rpm_value = num / den
                else:
                    raise ValueError("Invalid fraction format for RPM.")
            else:
                # Try parsing as a float
                rpm_value = float(input_text)
                
            # Convert valid RPM to rad/s
            rad_per_sec = rpm_value * (2 * math.pi) / 60.0
            
            # Emit the change with the value in rad/s
            print(f"RPM input '{input_text}' parsed to {rpm_value:.4f} RPM -> {rad_per_sec:.4f} rad/s")
            self.parameter_changed.emit(component, 'rotation_rate', rad_per_sec)
            
            # Optional: Update the line edit text to the formatted parsed RPM value?
            # line_edit.setText(f"{rpm_value:.4f}") 
            
        except ValueError as e:
            print(f"Error parsing RPM value '{input_text}': {e}")
            # Optionally provide feedback to the user (e.g., red background)
            # Restore previous value? Requires storing it or fetching from component again.
            current_rad_per_sec = component.rotation_rate
            current_rpm = current_rad_per_sec * 60 / (2 * math.pi)
            line_edit.setText(f"{current_rpm:.4f}") # Restore display
            # You might want to flash the background red briefly here

    def show_rod_details(self, rod: Rod, components_dict: Dict):
        """Display editable details for the selected rod."""
        print(f"DEBUG: ParameterPanel.show_rod_details called for rod ID: {rod.id}") # <-- ADD DEBUG PRINT
        try:
            self._clear_details_layout() # Clear old layout from details section
            self.update_components_dict(components_dict) 
            self.details_section.setTitle(f"Rod Details (ID: {rod.id})") # Use setTitle

            # Use the persistent layout: self.details_layout
            # new_layout = QFormLayout() # <-- REMOVE
            self.detail_widgets = {} # Reset dict

            # --- Populate self.details_layout --- 
            length_spin = QDoubleSpinBox()
            length_spin.setRange(0.0, 10000.0)
            length_spin.setDecimals(1)
            length_spin.setValue(rod.length)
            length_spin.setReadOnly(True)
            length_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
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

            # Add Fixed Length checkbox
            fixed_len_check = QCheckBox()
            fixed_len_check.setChecked(rod.fixed_length)
            fixed_len_check.toggled.connect(partial(self._handle_value_changed, rod, 'fixed_length'))
            self.detail_widgets['fixed_length'] = fixed_len_check
            self.details_layout.addRow("Fixed Length:", fixed_len_check)

            # Start/End Connection Display 
            start_conn_label = QLabel("<Not Connected>")
            start_conn_label.setWordWrap(True)
            if rod.start_connection:
                formatted_conn = _format_connection_target(rod.start_connection, components_dict)
                start_conn_label.setText(formatted_conn if formatted_conn else "<Error>")
            self.details_layout.addRow("Start Conn:", start_conn_label)
            self.detail_widgets['start_conn_label'] = start_conn_label

            end_conn_label = QLabel("<Not Connected>")
            end_conn_label.setWordWrap(True)
            if rod.end_connection:
                formatted_conn = _format_connection_target(rod.end_connection, components_dict)
                end_conn_label.setText(formatted_conn if formatted_conn else "<Error>")
            self.details_layout.addRow("End Conn:", end_conn_label)
            self.detail_widgets['end_conn_label'] = end_conn_label

            # Mid-point Connection - Store widgets as attributes (self. ...)
            self.has_mid_point_checkbox = QCheckBox() # <-- Changed to self.
            self.mid_dist_spin = QDoubleSpinBox()      # <-- Changed to self.
            self.mid_dist_spin.setRange(0.0, rod.length) # <-- Set range based on rod length
            self.mid_dist_spin.setDecimals(1)
            self.mid_dist_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
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
                self.has_mid_point_checkbox.setChecked(True)
                self.mid_dist_spin.setValue(rod.mid_point_distance)
                self.mid_dist_spin.setEnabled(True)
            else:
                 self.has_mid_point_checkbox.setChecked(False)
                 self.mid_dist_spin.setValue(0.0)
                 self.mid_dist_spin.setEnabled(False)
                 mid_conn_label.setText("N/A")
            self.detail_widgets['has_mid_point'] = self.has_mid_point_checkbox
            self.detail_widgets['mid_dist_spin'] = self.mid_dist_spin 
            self.detail_widgets['mid_conn_label'] = mid_conn_label
            self.details_layout.addRow("Has Mid-Point:", self.has_mid_point_checkbox)
            self.details_layout.addRow("Mid Dist:", self.mid_dist_spin)
            self.details_layout.addRow("Mid Conn:", mid_conn_label)
            
            # Pen Position - Store widgets as attributes (self. ...)
            self.has_pen_checkbox = QCheckBox()     # <-- Changed to self.
            self.pen_distance_spin = QDoubleSpinBox() # <-- Changed to self.
            self.pen_distance_spin.setRange(0.0, rod.length) # <-- Set range based on rod length
            self.pen_distance_spin.setDecimals(1)
            self.pen_distance_spin.setEnabled(False)
            if rod.pen_distance_from_start is not None:
                self.has_pen_checkbox.setChecked(True)
                self.pen_distance_spin.setValue(rod.pen_distance_from_start)
                self.pen_distance_spin.setEnabled(True)
            else:
                 self.has_pen_checkbox.setChecked(False)
                 self.pen_distance_spin.setValue(0.0)
                 self.pen_distance_spin.setEnabled(False)
            self.detail_widgets['has_pen'] = self.has_pen_checkbox
            self.detail_widgets['pen_distance_from_start'] = self.pen_distance_spin
            self.details_layout.addRow("Has Pen:", self.has_pen_checkbox)
            self.details_layout.addRow("Pen Distance:", self.pen_distance_spin)

            # Connect signals - Ensure signals connect to instance attributes
            start_x_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'start_x'))
            start_y_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'start_y'))
            end_x_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'end_x'))
            end_y_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'end_y'))
            self.has_pen_checkbox.toggled.connect(partial(self._handle_pen_toggled, rod))
            self.pen_distance_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'pen_distance_from_start'))
            self.mid_dist_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'mid_point_distance'))
            self.has_mid_point_checkbox.toggled.connect(partial(self._handle_mid_point_toggled, rod))
            # --- End Populate ---

            # No need to set layout again
            # self.details_section.setLayout(new_layout)
            self.details_section.adjustSize() 
            self.details_section.update() 
            
            # --- DIAGNOSTIC PRINTS --- 
            print(f"  Details section visible: {self.details_section.isVisible()}")
            print(f"  Details section title: {self.details_section.title()}")
            print(f"  Details section layout widget count: {self.details_section.layout().count()}")
            print(f"  Details section sizeHint: {self.details_section.sizeHint()}")
            print(f"  Details section minimumSizeHint: {self.details_section.minimumSizeHint()}")
            # --- END DIAGNOSTIC PRINTS ---
            
        except Exception as e:
            print(f"ERROR building rod details UI for {rod.id}: {e}")
            import traceback
            traceback.print_exc()
            self.details_section.setVisible(False) # Hide on error
            self.details_section.setTitle("Error Loading Details") # Set error title
            # Remove potentially broken layout?
            old_layout = self.details_section.layout()
            if old_layout is not None:
                QWidget().setLayout(old_layout)
                old_layout.deleteLater()

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
        # Set margins if needed
        settings_layout.setContentsMargins(5, 5, 5, 5) 
        
        # Add grid snap settings
        snap_label = QLabel("Grid Snap:")
        settings_layout.addWidget(snap_label) # Add to layout
        
        # Create button group for snap buttons
        self.snap_button_group = QButtonGroup(self)
        self.snap_button_group.setExclusive(True)
        
        # Add snap buttons with their values stored
        snap_values = [1, 5, 10]
        snap_buttons_layout = QHBoxLayout() # Layout for buttons horizontally
        for snap in snap_values:
            btn = QPushButton(f"{snap}mm")
            btn.setCheckable(True)
            btn.setProperty("snap_value", snap)  # Store the actual value
            snap_buttons_layout.addWidget(btn) # Add button to horizontal layout
            self.snap_button_group.addButton(btn)
        settings_layout.addLayout(snap_buttons_layout) # Add horizontal layout to main vertical layout
            
        # Set default selection to 1mm
        first_button = self.snap_button_group.buttons()[0]
        first_button.setChecked(True)
        
        # Connect button group
        self.snap_button_group.buttonClicked.connect(self._on_snap_button_clicked)
        
        # Add master speed control (placeholder)
        speed_label = QLabel("Master Speed: (NYI)")
        settings_layout.addWidget(speed_label) # Add to layout
        
        # Set the created layout to the settings section GroupBox
        self.settings_section.setLayout(settings_layout)

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
        line_color = "#0000FF" # Placeholder Blue
        line_width = self.image_line_width_spin.value()
        duration_seconds = self.simulation_duration_spin.value() # <-- Get duration in seconds
        
        if not filename:
            # TODO: Show error message
            print("Error: Filename cannot be empty.")
            return
            
        self.image_generate_requested.emit(filename, width, height, line_color, line_width, duration_seconds) # <-- Emit with duration_seconds

    # --- Add Method for GroupBox Toggling --- 
    def _handle_section_toggled(self, checked):
        """Handles the toggled signal from checkable QGroupBox sections."""
        # Optional: Adjust visibility or layout based on section state
        sender = self.sender()
        if isinstance(sender, QGroupBox):
            # Example: print(f"Section '{sender.title()}' toggled: {checked}")
            # You might hide/show the content widget or adjust layout spacing
            pass
            
    def _update_duration_display(self, seconds_value: float):
        """Formats seconds into HH:MM:SS and updates the label."""
        total_seconds = int(seconds_value)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        self.simulation_duration_label.setText(f"({hours:02d}:{minutes:02d}:{seconds:02d})")
    # --- End Method --- 
    