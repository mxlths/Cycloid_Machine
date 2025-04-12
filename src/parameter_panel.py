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
        return f"wheel_{comp_id}_point_{point_id}"
    elif isinstance(component, Rod):
        if point_id in ['start', 'mid', 'end']:
             return f"rod_{comp_id}_{point_id}"
        else:
             print(f"Warning: Invalid point_id '{point_id}' for rod connection {comp_id}")
             return f"<Invalid Pt {point_id}>"
    else:
        print(f"Warning: Unknown component type for connection: {type(component)}")
        return "<Unknown Comp>"

class CollapsibleSection(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.toggle_button = QPushButton(title)
        self.toggle_button.setStyleSheet("text-align: left; padding: 5px;") 
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.clicked.connect(self._toggle_content)
        self.content_area = QWidget()
        self.content_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.content_area.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.content_area.setVisible(self.toggle_button.isChecked())
        main_layout.addWidget(self.toggle_button)
        main_layout.addWidget(self.content_area)
        
    def setContentLayout(self, content_layout: QLayout):
        old_layout = self.content_area.layout()
        if old_layout is not None:
             QWidget().setLayout(old_layout) 
             old_layout.deleteLater()
        self.content_area.setLayout(content_layout)
        self.content_area.adjustSize()
        self.content_area.setVisible(self.toggle_button.isChecked())
        
    def _toggle_content(self, checked):
        self.content_area.setVisible(checked)
        if not checked:
             self.content_area.setMaximumHeight(0)
        else:
             self.content_area.setMaximumHeight(16777215)
        if self.parentWidget() and self.parentWidget().layout():
            self.parentWidget().layout().activate()

class ParameterPanel(QFrame):
    snap_changed = pyqtSignal(int)
    add_rod_requested = pyqtSignal()
    pen_assigned = pyqtSignal(object, bool) 
    start_simulation_requested = pyqtSignal()
    stop_simulation_requested = pyqtSignal()
    parameter_changed = pyqtSignal(object, str, object) 
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        container = QWidget()
        container.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.container_layout = QVBoxLayout(container)
        
        self.wheels_section = CollapsibleSection("Wheels")
        self.rods_section = CollapsibleSection("Rods")
        self.settings_section = CollapsibleSection("Settings")
        self.details_section = CollapsibleSection("Selected Component Details")
        self.details_section.setVisible(False)
        
        self.container_layout.addWidget(self.wheels_section)
        self.container_layout.addWidget(self.rods_section)
        self.container_layout.addWidget(self.details_section)
        self.container_layout.addWidget(self.settings_section)
        
        self._add_wheel_button = QPushButton("Add Wheel")
        wheels_layout = QVBoxLayout()
        wheels_layout.addWidget(self._add_wheel_button)
        self.wheels_section.setContentLayout(wheels_layout)
        
        self._add_rod_button = QPushButton("Add Rod")
        rods_layout = QVBoxLayout()
        rods_layout.addWidget(self._add_rod_button)
        self.rods_section.setContentLayout(rods_layout)
        self._add_rod_button.clicked.connect(self.add_rod_requested.emit)
        
        self._setup_details_section()
        self._setup_settings()
        
        self.simulation_section = CollapsibleSection("Simulation")
        sim_layout = QVBoxLayout()
        self.start_button = QPushButton("Start Simulation")
        self.stop_button = QPushButton("Stop Simulation")
        self.stop_button.setEnabled(False)
        sim_layout.addWidget(self.start_button)
        sim_layout.addWidget(self.stop_button)
        self.simulation_section.setContentLayout(sim_layout)
        self.container_layout.addWidget(self.simulation_section)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        self.container_layout.addStretch()
        
    def _setup_details_section(self):
        self.details_layout = QFormLayout()
        self.details_section.setContentLayout(self.details_layout)
        self.detail_widgets = {}

    def _clear_details_layout(self):
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.detail_widgets = {}

    def clear_details(self):
        self._clear_details_layout()
        self.details_section.setVisible(False)

    def show_wheel_details(self, wheel: Wheel, components_dict: Dict):
        self._clear_details_layout()
        self.details_section.toggle_button.setText(f"Wheel Details (ID: {wheel.id})")

        diameter_spin = QDoubleSpinBox()
        diameter_spin.setRange(1.0, 10000.0)
        diameter_spin.setDecimals(1)
        diameter_spin.setValue(wheel.diameter)
        self.detail_widgets['diameter'] = diameter_spin
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

        diameter_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'diameter'))
        center_x_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'center_x'))
        center_y_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'center_y'))
        speed_ratio_spin.valueChanged.connect(partial(self._handle_value_changed, wheel, 'speed_ratio'))

        self.details_section.setVisible(True)
        
    def show_rod_details(self, rod: Rod, components_dict: Dict):
        self._clear_details_layout()
        self.details_section.toggle_button.setText(f"Rod Details (ID: {rod.id})")

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
        
        self.has_mid_point_checkbox = QCheckBox()
        self.details_layout.addRow("Has Mid-Point:", self.has_mid_point_checkbox)
        
        self.mid_dist_spin = QDoubleSpinBox()
        self.mid_dist_spin.setRange(0.0, 10000.0)
        self.mid_dist_spin.setDecimals(1)
        self.mid_dist_spin.setEnabled(False)
        mid_conn_label = QLabel("N/A")
        if rod.mid_point_distance is not None:
            self.has_mid_point_checkbox.setChecked(True)
            self.mid_dist_spin.setValue(rod.mid_point_distance)
            self.mid_dist_spin.setEnabled(True)
            if rod.mid_point_connection:
                formatted_conn = _format_connection_target(rod.mid_point_connection, components_dict)
                mid_conn_label.setText(formatted_conn if formatted_conn else "Error")
            else:
                mid_conn_label.setText("<Not Connected>")
        else:
             self.has_mid_point_checkbox.setChecked(False)
             self.mid_dist_spin.setValue(0.0)
             self.mid_dist_spin.setEnabled(False)
             mid_conn_label.setText("N/A")
        self.detail_widgets['has_mid_point'] = self.has_mid_point_checkbox
        self.detail_widgets['mid_point_distance'] = self.mid_dist_spin
        self.details_layout.addRow("Mid Dist:", self.mid_dist_spin)
        self.details_layout.addRow("Mid Conn:", mid_conn_label)

        self.has_pen_checkbox = QCheckBox()
        self.pen_distance_spin = QDoubleSpinBox()
        self.pen_distance_spin.setRange(0.0, 10000.0)
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

        start_x_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'start_x'))
        start_y_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'start_y'))
        end_x_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'end_x'))
        end_y_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'end_y'))
        self.has_pen_checkbox.toggled.connect(partial(self._handle_pen_toggled, rod))
        self.pen_distance_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'pen_distance_from_start'))
        self.has_mid_point_checkbox.toggled.connect(partial(self._handle_mid_point_toggled, rod))
        self.mid_dist_spin.valueChanged.connect(partial(self._handle_value_changed, rod, 'mid_point_distance'))

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
        else:
            # For simple attributes like pen_distance_from_start, mid_point_distance, etc.
            setattr(component, param_name, value)
        
        # Then emit the parameter_changed signal
        self.parameter_changed.emit(component, param_name, value)
            
    def _handle_pen_toggled(self, rod: Rod, checked: bool):
        self.pen_distance_spin.setEnabled(checked)
        
        current_dist = rod.pen_distance_from_start
        new_distance = current_dist

        if checked:
            if current_dist is None:
                default_dist = rod.length / 2.0
                rod.pen_distance_from_start = default_dist
                self.pen_distance_spin.setValue(default_dist)
                new_distance = default_dist
            else:
                self.pen_distance_spin.setValue(current_dist)
                 
            self.pen_assigned.emit(rod, True)
            self.parameter_changed.emit(rod, 'pen_distance_from_start', new_distance)
        else:
            rod.pen_distance_from_start = None
            new_distance = None
            self.pen_assigned.emit(rod, False)
            self.parameter_changed.emit(rod, 'pen_distance_from_start', new_distance)
            
    def _handle_mid_point_toggled(self, rod: Rod, checked: bool):
        self.mid_dist_spin.setEnabled(checked)
        
        current_dist = rod.mid_point_distance
        new_distance = current_dist
        
        if checked:
            if current_dist is None:
                default_dist = rod.length / 2.0
                rod.mid_point_distance = default_dist
                self.mid_dist_spin.setValue(default_dist)
                new_distance = default_dist
            else:
                self.mid_dist_spin.setValue(current_dist)
        else:
            new_distance = None 
            
        self.parameter_changed.emit(rod, 'mid_point_distance', new_distance)

    def _setup_settings(self):
        settings_layout = QFormLayout()
        self.snap_group = QButtonGroup(self)
        snap_label = QLabel("Grid Snap (mm):")
        snap_button_layout = QHBoxLayout()
        for size in [1, 2, 5, 10]:
            button = QPushButton(str(size))
            button.setCheckable(True)
            button.setProperty("snap_value", size)
            button.clicked.connect(lambda checked, b=button: self._on_snap_button_clicked(b))
            self.snap_group.addButton(button)
            snap_button_layout.addWidget(button)
            if size == 1:
                button.setChecked(True)
        settings_layout.addRow(snap_label, snap_button_layout)
        self.settings_section.setContentLayout(settings_layout)

    def _on_snap_button_clicked(self, button):
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