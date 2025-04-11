from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
                               QPushButton, QFrame, QScrollArea, QButtonGroup, QFormLayout, QSizePolicy, QLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QFocusEvent
from components import Wheel, Rod
from typing import Optional
from functools import partial

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
        
        # Add container to scroll area
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
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

    def show_wheel_details(self, wheel: Wheel):
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

        # Add connection point inputs
        conn_radius_spin = QDoubleSpinBox()
        conn_radius_spin.setRange(0.0, 10000.0) # Radius >= 0
        conn_radius_spin.setDecimals(1)
        conn_radius_spin.setValue(wheel.connection_radius if wheel.connection_radius is not None else 0)
        conn_radius_spin.setToolTip("Distance from center for connection point")
        self.detail_widgets['connection_radius'] = conn_radius_spin
        self.details_layout.addRow("Conn. Radius:", conn_radius_spin)
        
        conn_phase_spin = QDoubleSpinBox()
        conn_phase_spin.setRange(0.0, 359.9) # Degrees 0-359.9
        conn_phase_spin.setDecimals(1)
        conn_phase_spin.setWrapping(True) # Allow wrap around (359.9 -> 0)
        conn_phase_spin.setValue(wheel.connection_phase_deg if wheel.connection_phase_deg is not None else 0)
        conn_phase_spin.setToolTip("Angle from North (0 deg), clockwise")
        self.detail_widgets['connection_phase_deg'] = conn_phase_spin
        self.details_layout.addRow("Conn. Phase (°):", conn_phase_spin)

        # Connect signals (using valueChanged)
        diameter_spin.valueChanged.connect(
            partial(self._handle_value_changed, wheel, 'diameter'))
        center_x_spin.valueChanged.connect(
            partial(self._handle_value_changed, wheel, 'center_x'))
        center_y_spin.valueChanged.connect(
            partial(self._handle_value_changed, wheel, 'center_y'))
        speed_ratio_spin.valueChanged.connect(
            partial(self._handle_value_changed, wheel, 'speed_ratio'))
        conn_radius_spin.valueChanged.connect(
            partial(self._handle_value_changed, wheel, 'connection_radius'))
        conn_phase_spin.valueChanged.connect(
            partial(self._handle_value_changed, wheel, 'connection_phase_deg'))

        self.details_section.setVisible(True)
        
    def show_rod_details(self, rod: Rod):
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

        # Connect signals
        # No signal needed for read-only length_spin
        start_x_spin.valueChanged.connect(
            partial(self._handle_value_changed, rod, 'start_x'))
        start_y_spin.valueChanged.connect(
            partial(self._handle_value_changed, rod, 'start_y'))
        end_x_spin.valueChanged.connect(
            partial(self._handle_value_changed, rod, 'end_x'))
        end_y_spin.valueChanged.connect(
            partial(self._handle_value_changed, rod, 'end_y'))
            
        self.details_section.setVisible(True)

    def _handle_value_changed(self, component, param_name, value):
        """Handle valueChanged signal from QDoubleSpinBox widgets."""
        self.parameter_changed.emit(component, param_name, value)
        
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