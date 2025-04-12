from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFocusEvent, QPolygonF
from components import Wheel, Rod, ConnectionPoint
import math
from typing import Optional, Union, List, Tuple, Dict

class DrawingCanvas(QWidget):
    # Signal emitted when a component is selected or deselected
    # Emits the selected component (Wheel or Rod) or None if deselected
    component_selected = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 600)
        
        # Set focus policy to accept focus and retain it
        # Combine StrongFocus (keyboard) and WheelFocus (mouse wheel)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus | Qt.FocusPolicy.WheelFocus)
        
        # Scale settings
        self.pixels_per_mm = 2  # Changed from 1 to 2 for double size
        
        # Grid settings
        self.grid_size = 10  # 10mm
        self.grid_color = QColor(200, 200, 200)
        self.major_grid_color = QColor(150, 150, 150)
        self.major_grid_interval = 5  # Every 5 lines is major
        
        # Components
        self.wheels: List[Wheel] = []
        self.rods: List[Rod] = []
        self.components_by_id: Dict[int, Union[Wheel, Rod]] = {} # ID lookup
        
        # Component ID Counter
        self._next_component_id = 1 # Start IDs from 1
        
        # Selection and interaction
        self.selected_component = None
        self.dragging = False
        self.drag_start = None
        self.hover_component = None
        self.dragging_point = None  # 'start' or 'end' for rod endpoints
        
        # Connection snapping
        self.connection_snap_distance = 10  # pixels
        self.hover_connection = None
        
        # Rod creation state
        self.creating_rod = False
        self.rod_start_pos = None
        
        # Snap settings
        self.snap_size = 1  # Default to 1mm
        
        # --- Simulation State --- 
        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self._update_simulation)
        self.simulation_running = False
        self.simulation_time_step = 1 / 60.0 # Time step for 60 FPS target
        self.current_simulation_angle_deg = 0.0 # Or simulation time
        # Pen Path - Store canvas coordinates
        self.pen_path_points = QPolygonF() # Use QPolygonF for efficient drawing
        self.pen_rod_id: Optional[int] = None # ID of the rod acting as the pen
        self.pen_point_type: Optional[str] = 'end' # Which point on pen_rod_id? 'start' or 'end'
        # --- End Simulation State ---
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
    def focusOutEvent(self, event: QFocusEvent): 
        """Override focus out to prevent losing focus when a component is selected"""
        if self.selected_component:
            # If a component is selected, immediately refocus the canvas
            # This prevents focus from going elsewhere unexpectedly
            # self.setFocus() # <<-- COMMENTED OUT - Likely stealing focus from panel
            pass # Do nothing for now if component is selected
        else:
            # Otherwise, allow focus to leave normally
            super().focusOutEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw grid
        self._draw_grid(painter)
        
        # Draw components
        self._draw_components(painter)
        
        # Draw pen path
        if not self.pen_path_points.isEmpty():
            painter.setPen(QPen(Qt.GlobalColor.darkCyan, 1)) # Pen color
            painter.drawPolyline(self.pen_path_points)
        
    def _screen_to_canvas(self, point: QPointF) -> QPointF:
        """Convert screen coordinates to canvas coordinates"""
        return QPointF(point.x() / self.pixels_per_mm, 
                      point.y() / self.pixels_per_mm)

    def _canvas_to_screen(self, point: QPointF) -> QPointF:
        """Convert canvas coordinates to screen coordinates"""
        return QPointF(point.x() * self.pixels_per_mm, 
                      point.y() * self.pixels_per_mm)

    def _draw_grid(self, painter):
        """Draw the mm grid"""
        width = self.width()
        height = self.height()
        
        # Calculate grid spacing in pixels
        grid_spacing = self.grid_size * self.pixels_per_mm
        
        # Draw vertical lines
        for x in range(0, width, grid_spacing):
            is_major = (x // grid_spacing) % self.major_grid_interval == 0
            color = self.major_grid_color if is_major else self.grid_color
            painter.setPen(QPen(color, 1 if is_major else 0.5))
            painter.drawLine(x, 0, x, height)
            
        # Draw horizontal lines
        for y in range(0, height, grid_spacing):
            is_major = (y // grid_spacing) % self.major_grid_interval == 0
            color = self.major_grid_color if is_major else self.grid_color
            painter.setPen(QPen(color, 1 if is_major else 0.5))
            painter.drawLine(0, y, width, y)
            
    def _draw_components(self, painter):
        """Draw all components (wheels and rods)"""
        # Draw rods first (so they appear under wheels)
        for rod in self.rods:
            self._draw_rod(painter, rod)
            
        # Then draw wheels
        for wheel in self.wheels:
            self._draw_wheel(painter, wheel)
            
        # Draw rod being created
        if self.creating_rod and self.rod_start_pos:
            current_pos = self._snap_to_grid(self._screen_to_canvas(self.mapFromGlobal(self.cursor().pos())))
            self._draw_temp_rod(painter, self.rod_start_pos, current_pos)
    
    def _draw_wheel(self, painter, wheel: Wheel):
        """Draw a single wheel"""
        # Convert wheel position to screen coordinates
        screen_center = self._canvas_to_screen(wheel.center)
        screen_radius = wheel.diameter * self.pixels_per_mm / 2
        
        # Set up colors and pens
        if wheel.selected:
            painter.setPen(QPen(Qt.GlobalColor.blue, 2))
            painter.setBrush(QBrush(QColor(200, 200, 255, 100)))
        elif wheel == self.hover_component:
            painter.setPen(QPen(Qt.GlobalColor.darkGray, 2))
            painter.setBrush(QBrush(QColor(220, 220, 220, 100)))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 1))
            painter.setBrush(QBrush(QColor(240, 240, 240, 100)))
            
        # Draw wheel circle
        painter.drawEllipse(screen_center, screen_radius, screen_radius)
        
        # Draw center point
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(QBrush(Qt.GlobalColor.black))
        painter.drawEllipse(screen_center, 4, 4)  # Made center point larger
        
        # Draw connection points
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.setBrush(QBrush(Qt.GlobalColor.red))
        for point_id in wheel.connection_points: # Iterate through all points
            conn_pos = wheel.get_connection_point_position(point_id)
            if conn_pos:
                screen_conn_pos = self._canvas_to_screen(conn_pos)
                painter.drawEllipse(screen_conn_pos, 6, 6) # Draw connection point marker
        
    def _draw_rod(self, painter, rod: Rod):
        """Draw a single rod"""
        # Convert positions to screen coordinates
        start_screen = self._canvas_to_screen(rod.start_pos)
        end_screen = self._canvas_to_screen(rod.end_pos)
        
        # Set up colors and pens
        if rod.selected:
            painter.setPen(QPen(Qt.GlobalColor.blue, 3))
        elif rod == self.hover_component:
            painter.setPen(QPen(Qt.GlobalColor.darkGray, 3))
        else:
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            
        # Draw the rod line
        painter.drawLine(start_screen, end_screen)
        
        # Draw end points with different colors if being dragged
        start_color = Qt.GlobalColor.red if self.dragging_point == 'start' and rod.selected else Qt.GlobalColor.black
        end_color = Qt.GlobalColor.red if self.dragging_point == 'end' and rod.selected else Qt.GlobalColor.black
        
        painter.setPen(QPen(start_color, 2))
        painter.setBrush(QBrush(start_color))
        painter.drawEllipse(start_screen, 4, 4)
        
        painter.setPen(QPen(end_color, 2))
        painter.setBrush(QBrush(end_color))
        painter.drawEllipse(end_screen, 4, 4)
        
        # --- Draw Mid-point Marker ---
        if rod.mid_point_distance is not None:
            mid_pos_canvas = rod.get_point_at_distance(rod.mid_point_distance)
            mid_pos_screen = self._canvas_to_screen(mid_pos_canvas)
            painter.setPen(QPen(Qt.GlobalColor.darkGreen, 1))
            painter.setBrush(QBrush(Qt.GlobalColor.green))
            painter.drawEllipse(mid_pos_screen, 5, 5) # Slightly larger green circle
            
        # --- Draw Pen Marker ---
        if rod.pen_distance_from_start is not None:
            pen_pos_canvas = rod.get_point_at_distance(rod.pen_distance_from_start)
            pen_pos_screen = self._canvas_to_screen(pen_pos_canvas)
            painter.setPen(QPen(Qt.GlobalColor.magenta, 2))
            # Draw a cross shape
            size = 6
            # Cast coordinates to int for drawLine(x1, y1, x2, y2)
            x, y = int(pen_pos_screen.x()), int(pen_pos_screen.y())
            painter.drawLine(x - size, y, x + size, y)
            painter.drawLine(x, y - size, x, y + size)
        
        # Draw hover connection indicator
        if self.hover_connection and rod.selected:
            painter.setPen(QPen(Qt.GlobalColor.green, 2))
            painter.setBrush(QBrush(Qt.GlobalColor.green))
            screen_pos = self._canvas_to_screen(self.hover_connection[3])
            painter.drawEllipse(screen_pos, 8, 8)
    
    def _draw_temp_rod(self, painter, start: QPointF, end: QPointF):
        """Draw temporary rod while creating"""
        start_screen = self._canvas_to_screen(start)
        end_screen = self._canvas_to_screen(end)
        
        # Draw dashed line
        pen = QPen(Qt.GlobalColor.blue, 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(start_screen, end_screen)
        
        # Draw end points
        painter.setBrush(QBrush(Qt.GlobalColor.blue))
        painter.drawEllipse(start_screen, 4, 4)
        painter.drawEllipse(end_screen, 4, 4)
    
    def add_wheel(self, center: QPointF, diameter: float) -> Wheel:
        """Adds a new wheel to the canvas."""
        new_id = self._next_component_id
        self._next_component_id += 1
        wheel = Wheel(id=new_id, center=center, diameter=diameter)
        # Automatically add a connection point 'p1' at the wheel's radius
        wheel_radius = diameter / 2.0
        wheel.add_connection_point('p1', wheel_radius)
        
        self.wheels.append(wheel)
        self.components_by_id[new_id] = wheel # Add to lookup
        self.update() 
        return wheel
        
    def _snap_to_grid(self, point: QPointF) -> QPointF:
        """Snap a point to the nearest grid position"""
        x = round(point.x() / self.snap_size) * self.snap_size
        y = round(point.y() / self.snap_size) * self.snap_size
        return QPointF(x, y)
        
    def _find_nearest_connection_point(self, canvas_point: QPointF) -> Optional[Tuple]:
        """Find the nearest connection point (wheel or rod endpoint) to a canvas point.
        Returns: Tuple (component_type, component_id, point_id, point_position) or None
        """
        min_dist_sq = (self.connection_snap_distance / self.pixels_per_mm) ** 2
        nearest = None
        
        # Check wheel connection points
        for wheel in self.wheels:
            for point_id, cp in wheel.connection_points.items(): # Iterate through points
                pos = wheel.get_connection_point_position(point_id)
                if pos:
                    dist_sq = (canvas_point.x() - pos.x())**2 + (canvas_point.y() - pos.y())**2
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        # Return component ID, the specific point ID, and position
                        nearest = ('wheel', wheel.id, point_id, pos) 
        
        # Check rod connection points (endpoints only for now)
        for rod in self.rods:
            # Check start point
            pos_start = rod.start_pos
            dist_sq_start = (canvas_point.x() - pos_start.x())**2 + (canvas_point.y() - pos_start.y())**2
            if dist_sq_start < min_dist_sq:
                min_dist_sq = dist_sq_start
                nearest = ('rod_start', rod.id, 'start', pos_start)
                
            # Check end point
            pos_end = rod.end_pos
            dist_sq_end = (canvas_point.x() - pos_end.x())**2 + (canvas_point.y() - pos_end.y())**2
            if dist_sq_end < min_dist_sq:
                min_dist_sq = dist_sq_end
                nearest = ('rod_end', rod.id, 'end', pos_end)

        # --- Remove old rod mid-point connection check ---
        # Check rod mid-point connection points (if any were implemented)
        # Add check for actual mid-points
        for rod in self.rods:
            if rod.mid_point_distance is not None:
                 pos_mid = rod.get_point_at_distance(rod.mid_point_distance)
                 dist_sq_mid = (canvas_point.x() - pos_mid.x())**2 + (canvas_point.y() - pos_mid.y())**2
                 if dist_sq_mid < min_dist_sq:
                    min_dist_sq = dist_sq_mid
                    # Return type, component ID, point ID ('mid'), and position
                    nearest = ('rod_mid', rod.id, 'mid', pos_mid) 
        
        return nearest

    def _is_near_rod_endpoint(self, rod: Rod, point: QPointF, which_end: str) -> bool:
        """Check if a point is near either end of a rod"""
        pos = rod.start_pos if which_end == 'start' else rod.end_pos
        dx = point.x() - pos.x()
        dy = point.y() - pos.y()
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= 5.0 / self.pixels_per_mm  # 5 pixels tolerance

    def mousePressEvent(self, event):
        """Handle component selection and rod creation"""
        canvas_point = self._screen_to_canvas(QPointF(event.position()))
        snapped_point = self._snap_to_grid(canvas_point)
        
        selected_component_changed = False
        previously_selected = self.selected_component
        
        if event.button() == Qt.MouseButton.LeftButton:
            # --- Priority 1: Handle Rod Creation Clicks --- 
            if self.creating_rod:
                if self.rod_start_pos is None:
                    # First click: Set start position
                    self.rod_start_pos = snapped_point
                    self.update() 
                    return # Wait for second click
                else:
                    # Second click: Finish creation
                    self.finish_rod_creation(snapped_point)
                    # finish_rod_creation resets creating_rod and rod_start_pos
                    return # Rod creation finished
            
            # --- Priority 2: Handle Component Selection/Dragging --- 
            newly_selected_component = None
            # Check for rod endpoint selection
            for rod in self.rods:
                if self._is_near_rod_endpoint(rod, canvas_point, 'start'):
                    newly_selected_component = rod # Mark for selection
                    self.dragging = True
                    self.dragging_point = 'start'
                    self.drag_start = canvas_point
                    break # Found component
                elif self._is_near_rod_endpoint(rod, canvas_point, 'end'):
                    newly_selected_component = rod # Mark for selection
                    self.dragging = True
                    self.dragging_point = 'end'
                    self.drag_start = canvas_point
                    break # Found component
            
            # Check for wheel selection (only if rod not selected)
            if not newly_selected_component:
                for wheel in self.wheels:
                    if wheel.contains_point(canvas_point):
                        newly_selected_component = wheel # Mark for selection
                        self.dragging = True
                        self.drag_start = canvas_point
                        self.dragging_point = None
                        break # Found component

            # Process selection change
            if newly_selected_component:
                if self.selected_component != newly_selected_component:
                    if self.selected_component:
                        self.selected_component.selected = False # Deselect previous
                    self.selected_component = newly_selected_component
                    self.selected_component.selected = True
                    selected_component_changed = True
                self.setFocus()
                self.update()
                # Emit signal if selection actually changed
                if selected_component_changed:
                    self.component_selected.emit(self.selected_component)
                return # Component selected or re-selected

            # --- Priority 3: Clicked Empty Space (Not Creating Rod) --- 
            # If we reach here, it means creating_rod is False and no component was clicked
            if self.selected_component:
                self.selected_component.selected = False
                self.selected_component = None
                self.dragging_point = None
                selected_component_changed = True # Selection changed to None
                self.update()

            # Emit signal if selection changed (even if cleared)
            if selected_component_changed:
                 self.component_selected.emit(self.selected_component) # Emits None here
            # Do nothing else - rod creation must be explicitly started
        
    def mouseMoveEvent(self, event):
        """Handle component dragging and hover effects"""
        canvas_point = self._screen_to_canvas(QPointF(event.position()))
        snapped_point = self._snap_to_grid(canvas_point)
        
        if self.creating_rod:
            self.update()
            return
            
        if self.dragging and self.selected_component:
            # Find nearest connection point
            nearest = self._find_nearest_connection_point(canvas_point)
            target_point = nearest[3] if nearest else snapped_point
            
            if isinstance(self.selected_component, Wheel):
                # Remember original position to detect actual movement
                original_pos = QPointF(self.selected_component.center)
                self.selected_component.move_to(target_point)
                
                # Only propagate constraints if the wheel actually moved
                if original_pos != self.selected_component.center:
                    # Get new positions for ALL connection points on the moved wheel
                    initial_targets = {}
                    for point_id in self.selected_component.connection_points:
                        new_pos = self.selected_component.get_connection_point_position(point_id)
                        if new_pos:
                            initial_targets[(self.selected_component.id, point_id)] = new_pos
                    
                    # If the wheel has connection points, propagate constraints
                    if initial_targets:
                        self._propagate_constraints(initial_targets)
                
            elif isinstance(self.selected_component, Rod):
                # Disconnect endpoint if moving a connected one
                if self.dragging_point == 'start' and self.selected_component.start_connection:
                    print(f"Rod {self.selected_component.id} start disconnected by dragging.")
                    self.selected_component.start_connection = None
                elif self.dragging_point == 'end' and self.selected_component.end_connection:
                    print(f"Rod {self.selected_component.id} end disconnected by dragging.")
                    self.selected_component.end_connection = None
                    
                # Move the specific endpoint
                original_start = QPointF(self.selected_component.start_pos)
                original_end = QPointF(self.selected_component.end_pos)
                moved_point_id = None
                
                if self.dragging_point == 'start':
                    self.selected_component.move_start_to(target_point)
                    moved_point_id = 'start'
                elif self.dragging_point == 'end':
                    self.selected_component.move_end_to(target_point)
                    moved_point_id = 'end'
                
                # Only propagate constraints if the rod actually moved
                if moved_point_id and ((moved_point_id == 'start' and original_start != self.selected_component.start_pos) or 
                                      (moved_point_id == 'end' and original_end != self.selected_component.end_pos)):
                    
                    # Prepare initial targets for constraint propagation
                    initial_targets = {}
                    
                    # Add the moved endpoint
                    if moved_point_id == 'start':
                        initial_targets[(self.selected_component.id, 'start')] = self.selected_component.start_pos
                    else:
                        initial_targets[(self.selected_component.id, 'end')] = self.selected_component.end_pos
                    
                    # If this rod has a mid-point, add it to the targets
                    if self.selected_component.mid_point_distance is not None:
                        mid_pos = self.selected_component.get_point_at_distance(self.selected_component.mid_point_distance)
                        initial_targets[(self.selected_component.id, 'mid')] = mid_pos
                    
                    # If this rod has a mid-point connection, mark it as "moved" to prioritize its constraints
                    if self.selected_component.mid_point_connection is not None:
                        moved_rod_ids.add(self.selected_component.id)
                        if self.selected_component.id not in moved_point_types:
                            moved_point_types[self.selected_component.id] = set()
                        moved_point_types[self.selected_component.id].add('mid')
                    
                    # Propagate the constraints
                    self._propagate_constraints(initial_targets)
            
            self.hover_connection = nearest
            self.update()
        else:
            # Update hover state
            old_hover = self.hover_component
            self.hover_component = None
            
            # Check wheels first
            for wheel in self.wheels:
                if wheel.contains_point(canvas_point):
                    self.hover_component = wheel
                    break
            
            # Then check rod endpoints
            if not self.hover_component:
                for rod in self.rods:
                    if (self._is_near_rod_endpoint(rod, canvas_point, 'start') or 
                        self._is_near_rod_endpoint(rod, canvas_point, 'end')):
                        self.hover_component = rod
                        break
            
            if old_hover != self.hover_component:
                self.update()
                
    def mouseReleaseEvent(self, event):
        """Handle end of dragging and establish connections"""
        
        # Establish connection if snapping a rod endpoint on release
        if (self.dragging and 
            self.selected_component and isinstance(self.selected_component, Rod) and 
            self.dragging_point and 
            self.hover_connection):
            
            target_comp_type, target_comp_id, target_point_id, target_pos = self.hover_connection
            connection_details = (target_comp_id, target_point_id)
            
            if self.dragging_point == 'start':
                self.selected_component.start_connection = connection_details
                # Force position to snap exactly
                self.selected_component.start_pos = target_pos 
                # Recalculate length based on potentially changed start pos
                dx = self.selected_component.end_pos.x() - self.selected_component.start_pos.x()
                dy = self.selected_component.end_pos.y() - self.selected_component.start_pos.y()
                self.selected_component.length = math.sqrt(dx*dx + dy*dy)
                print(f"Rod {self.selected_component.id} start connected to {target_comp_type} {target_comp_id}::{target_point_id}")
                
            elif self.dragging_point == 'end':
                self.selected_component.end_connection = connection_details
                # Force position to snap exactly
                self.selected_component.end_pos = target_pos
                 # Recalculate length based on potentially changed end pos
                dx = self.selected_component.end_pos.x() - self.selected_component.start_pos.x()
                dy = self.selected_component.end_pos.y() - self.selected_component.start_pos.y()
                self.selected_component.length = math.sqrt(dx*dx + dy*dy)
                print(f"Rod {self.selected_component.id} end connected to {target_comp_type} {target_comp_id}::{target_point_id}")
                
            # Refresh parameter panel if length changed
            self.component_selected.emit(self.selected_component) 

        # --- Original Cleanup ---
        # Clear hover connection indicator regardless
        self.hover_connection = None
        
        # If not creating a rod, clear dragging state
        # (Rod creation handles its own state reset in finish_rod_creation)
        if not self.creating_rod:
            self.dragging = False
            self.drag_start = None
            self.dragging_point = None
        
        self.update()
        
    def keyPressEvent(self, event):
        """Handle arrow key nudging and deletion of selected components"""
        if not self.selected_component:
            # If no component is selected, ignore key presses
            return
            
        # Handle deletion first
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            self.delete_selected_component()
            return # Component deleted, nothing more to do
            
        # Handle nudging (arrow keys)
        delta = self.snap_size
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            delta *= 10
            
        delta_x = 0
        delta_y = 0
        
        if event.key() == Qt.Key.Key_Left:
            delta_x = -delta
        elif event.key() == Qt.Key.Key_Right:
            delta_x = delta
        elif event.key() == Qt.Key.Key_Up:
            delta_y = -delta
        elif event.key() == Qt.Key.Key_Down:
            delta_y = delta
            
        if delta_x != 0 or delta_y != 0:
            # Apply delta based on component type
            if isinstance(self.selected_component, Wheel):
                current = self.selected_component.center
                new_center = QPointF(current.x() + delta_x, current.y() + delta_y)
                self.selected_component.move_to(new_center)
                # Propagate constraints after moving a wheel
                new_pos = self.selected_component.get_connection_point_position()
                initial_targets = {}
                if new_pos:
                    initial_targets[(self.selected_component.id, self.selected_component.CONNECTION_POINT_ID)] = new_pos
                self._propagate_constraints(initial_targets)
            elif isinstance(self.selected_component, Rod):
                # Move both endpoints
                start = self.selected_component.start_pos
                end = self.selected_component.end_pos
                
                # Disconnect if nudging a connected rod
                if self.selected_component.start_connection or self.selected_component.end_connection:
                    print(f"Rod {self.selected_component.id} disconnected by nudging.")
                    self.selected_component.start_connection = None
                    self.selected_component.end_connection = None
                    
                self.selected_component.start_pos = QPointF(start.x() + delta_x, start.y() + delta_y)
                self.selected_component.end_pos = QPointF(end.x() + delta_x, end.y() + delta_y)
                # Propagate constraints after nudging a rod
                initial_targets = {
                    (self.selected_component.id, 'start'): self.selected_component.start_pos,
                    (self.selected_component.id, 'end'): self.selected_component.end_pos
                }
                self._propagate_constraints(initial_targets)
            
            # Update canvas
            self.update()
            
    def set_snap_size(self, size: int):
        """Set the grid snap size"""
        self.snap_size = size
        self.update()
        
    def wheelEvent(self, event):
        """Handle zooming"""
        # We'll implement zooming later
        pass 

    def start_rod_creation(self, start_pos: Optional[QPointF] = None):
        """Explicitly start creating a new rod. Can be called with a starting point.
           If start_pos is None, it indicates the mode is active, waiting for first click.
        """
        # Ensure canvas has focus when entering this mode
        self.setFocus() 
        # Deselect any existing component when starting rod creation
        if self.selected_component:
            previously_selected = self.selected_component
            self.selected_component.selected = False
            self.selected_component = None
            self.dragging_point = None
            # Emit signal that selection was cleared
            if previously_selected is not None:
                 self.component_selected.emit(None)
            
        self.creating_rod = True
        self.rod_start_pos = start_pos # Usually None when called from button
        self.update()
    
    def finish_rod_creation(self, end_pos: QPointF):
        """Finish creating a new rod and reset creation state"""
        rod = None # Initialize rod to None
        if self.rod_start_pos:
            # Calculate length
            dx = end_pos.x() - self.rod_start_pos.x()
            dy = end_pos.y() - self.rod_start_pos.y()
            length = math.sqrt(dx * dx + dy * dy)
            
            # Only create rod if length is non-zero
            if length > 0:
                # Generate ID before creating
                new_id = self._next_component_id
                self._next_component_id += 1
                # Create new rod with ID
                rod = Rod(id=new_id, # Pass ID
                         length=length, 
                         start_pos=self.rod_start_pos,
                         end_pos=end_pos)
                self.rods.append(rod)
                self.components_by_id[new_id] = rod # Add to lookup
                
            # Reset creation state regardless of whether a rod was created
            self.creating_rod = False
            self.rod_start_pos = None
            self.update()
            
        return rod # Return created rod or None

    def delete_selected_component(self):
        """Deletes the currently selected component."""
        if not self.selected_component:
            return

        component_to_delete = self.selected_component
        component_id = component_to_delete.id # Get ID for message

        # --- Clear Connections Pointing TO the Deleted Component --- 
        for rod in self.rods:
            # Check if this rod is the one being deleted
            if rod.id == component_id:
                continue # Don't modify the rod we are about to delete
                
            # Clear connections if they point to the deleted component ID
            if rod.start_connection and rod.start_connection[0] == component_id:
                print(f"Clearing start connection of Rod {rod.id} (was connected to deleted {component_id})")
                rod.start_connection = None
            if rod.end_connection and rod.end_connection[0] == component_id:
                print(f"Clearing end connection of Rod {rod.id} (was connected to deleted {component_id})")
                rod.end_connection = None
            if rod.mid_point_connection and rod.mid_point_connection[0] == component_id:
                print(f"Clearing mid connection of Rod {rod.id} (was connected to deleted {component_id})")
                rod.mid_point_connection = None
        # --- End Connection Clearing --- 

        # Remove from the correct list FIRST
        if isinstance(component_to_delete, Wheel):
            if component_to_delete in self.wheels:
                 self.wheels.remove(component_to_delete)
                 print(f"Removed Wheel {component_id} from list")
            else: 
                 print(f"Warning: Wheel {component_id} not found in list for removal.")
        elif isinstance(component_to_delete, Rod):
             if component_to_delete in self.rods:
                 self.rods.remove(component_to_delete)
                 print(f"Removed Rod {component_id} from list")
             else:
                 print(f"Warning: Rod {component_id} not found in list for removal.")

        # Clear selection state AFTER removing connections
        self.selected_component = None
        self.dragging = False
        self.dragging_point = None
        self.component_selected.emit(None) # Notify panel to clear
        self.update() 

        # THEN remove from lookup dictionary
        if component_id in self.components_by_id:
             del self.components_by_id[component_id] 
             print(f"Removed component {component_id} from lookup")
        else:
             print(f"Warning: Component {component_id} not found in lookup for deletion.")

    def _update_component_lookup(self):
        """Rebuild the component ID lookup dictionary."""
        self.components_by_id.clear()
        for wheel in self.wheels:
            self.components_by_id[wheel.id] = wheel
        for rod in self.rods:
            self.components_by_id[rod.id] = rod

    # --- Simulation Update Helpers ---
    def _get_current_connection_point_positions(self) -> Dict[Tuple[int, str], QPointF]:
        """Gets the current world positions of all defined connection points.
           Returns a dictionary keyed by (component_id, point_id).
        """
        positions = {}
        for wheel in self.wheels:
            for point_id in wheel.connection_points:
                pos = wheel.get_connection_point_position(point_id)
                if pos:
                    positions[(wheel.id, point_id)] = pos # Use the actual point_id
        # Add rod endpoints as potential connection targets
        for rod in self.rods:
            positions[(rod.id, 'start')] = rod.start_pos
            positions[(rod.id, 'end')] = rod.end_pos
            # Add mid-point if it exists
            if rod.mid_point_distance is not None:
                mid_pos = rod.get_point_at_distance(rod.mid_point_distance)
                positions[(rod.id, 'mid')] = mid_pos
        return positions

    def _propagate_constraints(self, initial_targets: Optional[Dict[Tuple[int, str], QPointF]] = None):
        """Iteratively updates rod positions based on connections.
           Starts with optional initial target positions for moved components.
        """
        num_passes = 30  # Increased passes for potentially complex interactions

        # Get the current state of all connection points
        target_positions = self._get_current_connection_point_positions()
        if initial_targets:
            target_positions.update(initial_targets)  # Update with manually moved points

        for pass_num in range(num_passes):
            something_moved_in_pass = False

            # Process all rods in each pass
            for rod in self.rods:
                original_start = QPointF(rod.start_pos)
                original_end = QPointF(rod.end_pos)
                original_length = rod.length
                # Ensure original_mid_dist is valid before calculations
                original_mid_dist = max(0.0, min(original_length, rod.mid_point_distance if rod.mid_point_distance is not None else 0.0))

                has_mid_connection = rod.mid_point_connection is not None
                has_start_connection = rod.start_connection is not None
                has_end_connection = rod.end_connection is not None

                # Get target positions for THIS rod in THIS pass
                target_start_pos = target_positions.get(rod.start_connection) if has_start_connection else None
                target_end_pos = target_positions.get(rod.end_connection) if has_end_connection else None
                target_mid_pos = target_positions.get(rod.mid_point_connection) if has_mid_connection else None

                moved_this_iteration = False
                # Initialize final positions to current ones
                final_start_pos = QPointF(rod.start_pos)
                final_end_pos = QPointF(rod.end_pos)
                length_changed = False
                mid_dist_changed = False # Track if mid-point distance itself was recalculated

                # --- Determine Movement Logic ---
                process_as_mid_point_constrained = False
                if has_mid_connection and target_mid_pos is not None:
                    # Check if the current mid-point is significantly different from the target
                    current_mid_pos = rod.get_point_at_distance(original_mid_dist) # Use original proportion
                    if (target_mid_pos - current_mid_pos).manhattanLength() > 1e-5:
                        process_as_mid_point_constrained = True

                # --- Apply Logic ---
                if process_as_mid_point_constrained:
                    # --- Priority 1: Handle Mid-point Connection Constraints ---
                    start_is_fixed = target_start_pos is not None
                    end_is_fixed = target_end_pos is not None

                    if start_is_fixed and end_is_fixed:
                        # Case 4: Both ends constrained - Rod MUST deform
                        final_start_pos = target_start_pos
                        final_end_pos = target_end_pos
                        length_changed = True # Length determined by fixed ends

                    elif start_is_fixed:
                        # Case 2: Start fixed, End free - Pivot around start to meet mid-target
                        final_start_pos = target_start_pos
                        vec_S_TM = target_mid_pos - final_start_pos # Vector Start -> Target Mid
                        len_S_TM = math.hypot(vec_S_TM.x(), vec_S_TM.y())

                        # Check for valid original proportions
                        if original_mid_dist > 1e-6 and original_length > 1e-6:
                             # Calculate End position E = S + (M-S) * (L/d_sm)
                             scale_factor = original_length / original_mid_dist
                             final_end_pos = final_start_pos + vec_S_TM * scale_factor
                        else: # Degenerate case (mid at start, or zero length)
                            # Preserve original orientation if possible
                            rod_angle = math.atan2(original_end.y() - original_start.y(), original_end.x() - original_start.x())
                            final_end_pos = final_start_pos + QPointF(original_length * math.cos(rod_angle), original_length * math.sin(rod_angle))

                    elif end_is_fixed:
                        # Case 3: End fixed, Start free - Pivot around end to meet mid-target
                        final_end_pos = target_end_pos
                        vec_E_TM = target_mid_pos - final_end_pos # Vector End -> Target Mid
                        len_E_TM = math.hypot(vec_E_TM.x(), vec_E_TM.y())
                        original_dist_end_mid = original_length - original_mid_dist

                        # Check for valid original proportions
                        if original_dist_end_mid > 1e-6 and original_length > 1e-6:
                            # Calculate Start position S = E + (M-E) * (L/d_em)
                            scale_factor = original_length / original_dist_end_mid
                            final_start_pos = final_end_pos + vec_E_TM * scale_factor
                        else: # Degenerate case (mid at end, or zero length)
                             # Preserve original orientation relative to end
                             rod_angle = math.atan2(original_start.y() - original_end.y(), original_start.x() - original_end.x()) # Angle end->start
                             final_start_pos = final_end_pos + QPointF(original_length * math.cos(rod_angle), original_length * math.sin(rod_angle))

                    else:
                        # Case 1: Only mid-point connected - Preserve length/orientation, translate
                        rod_angle = math.atan2(original_end.y() - original_start.y(), original_end.x() - original_start.x())
                        dist_mid_to_start = original_mid_dist # Use valid original proportion
                        dist_mid_to_end = original_length - dist_mid_to_start
                        final_start_pos = QPointF(target_mid_pos.x() - dist_mid_to_start * math.cos(rod_angle), target_mid_pos.y() - dist_mid_to_start * math.sin(rod_angle))
                        final_end_pos = QPointF(target_mid_pos.x() + dist_mid_to_end * math.cos(rod_angle), target_mid_pos.y() + dist_mid_to_end * math.sin(rod_angle))

                    # --- Apply calculated positions from mid-point logic ---
                    if (final_start_pos - rod.start_pos).manhattanLength() > 1e-5 or \
                       (final_end_pos - rod.end_pos).manhattanLength() > 1e-5:
                        rod.start_pos = final_start_pos
                        rod.end_pos = final_end_pos
                        moved_this_iteration = True

                    # --- Handle necessary deformation (Case 4 primarily) ---
                    if length_changed:
                        dx = rod.end_pos.x() - rod.start_pos.x()
                        dy = rod.end_pos.y() - rod.start_pos.y()
                        new_total_length = math.hypot(dx, dy)
                        if abs(new_total_length - original_length) > 1e-4:
                             rod.length = new_total_length # Update length
                        else:
                            length_changed = False # Mark as unchanged if difference is negligible

                        if new_total_length > 1e-6:
                             # Recalculate mid-point distance based on projection
                             t = ((target_mid_pos.x() - rod.start_pos.x()) * dx +
                                  (target_mid_pos.y() - rod.start_pos.y()) * dy) / (new_total_length**2)
                             t = max(0.0, min(1.0, t)) # Clamp
                             new_mid_dist = t * rod.length
                             if abs(new_mid_dist - original_mid_dist) > 1e-4:
                                 rod.mid_point_distance = new_mid_dist
                                 mid_dist_changed = True
                        else: # Rod collapsed
                            rod.length = 0.0
                            rod.mid_point_distance = 0.0
                            mid_dist_changed = True

                else:
                    # --- Priority 2: Handle End Connections (No mid-point constraint active this iteration) ---
                    local_move = False
                    temp_start = QPointF(rod.start_pos) # Work with temps to avoid partial updates
                    temp_end = QPointF(rod.end_pos)

                    if target_start_pos is not None and target_end_pos is not None:
                        # Both ends have targets - move to targets, length will adjust
                        temp_start = target_start_pos
                        temp_end = target_end_pos
                        local_move = True # Will trigger length recalc below
                        length_changed = True # Mark length as potentially changed

                    elif target_start_pos is not None:
                        # Start constrained, End free - Maintain original length
                        temp_start = target_start_pos
                        vec_start_to_end = temp_end - temp_start # Vector based on potentially moved start
                        current_dist = math.hypot(vec_start_to_end.x(), vec_start_to_end.y())
                        if current_dist > 1e-6 and original_length > 1e-6:
                             scale = original_length / current_dist
                             temp_end = temp_start + vec_start_to_end * scale
                        local_move = True

                    elif target_end_pos is not None:
                         # End constrained, Start free - Maintain original length
                         temp_end = target_end_pos
                         vec_end_to_start = temp_start - temp_end # Vector based on potentially moved end
                         current_dist = math.hypot(vec_end_to_start.x(), vec_end_to_start.y())
                         if current_dist > 1e-6 and original_length > 1e-6:
                             scale = original_length / current_dist
                             temp_start = temp_end + vec_end_to_start * scale
                         local_move = True

                    # Apply changes from this block if any occurred
                    if local_move:
                         if (temp_start - rod.start_pos).manhattanLength() > 1e-5 or \
                            (temp_end - rod.end_pos).manhattanLength() > 1e-5:
                             rod.start_pos = temp_start
                             rod.end_pos = temp_end
                             moved_this_iteration = True


                # --- Update target positions if rod moved AT ALL during this iteration ---
                if moved_this_iteration:
                    something_moved_in_pass = True

                    # Recalculate length if it changed OR if moved by Priority 2 logic
                    dx = rod.end_pos.x() - rod.start_pos.x()
                    dy = rod.end_pos.y() - rod.start_pos.y()
                    new_total_length = math.hypot(dx, dy)
                    if abs(new_total_length - rod.length) > 1e-4:
                         rod.length = new_total_length
                         # If length changed, and mid-dist wasn't explicitly recalc'd (Case 4), update proportionally
                         if not mid_dist_changed and original_length > 1e-6:
                             proportion = original_mid_dist / original_length
                             rod.mid_point_distance = rod.length * proportion
                             mid_dist_changed = True # Mark as changed proportionally

                    # Update target positions dictionary for the next iteration/pass
                    target_positions[(rod.id, 'start')] = rod.start_pos
                    target_positions[(rod.id, 'end')] = rod.end_pos
                    if rod.mid_point_distance is not None:
                        # Final clamp for safety
                        rod.mid_point_distance = max(0.0, min(rod.length, rod.mid_point_distance))
                        mid_pos = rod.get_point_at_distance(rod.mid_point_distance)
                        target_positions[(rod.id, 'mid')] = mid_pos

            # Exit loop early if nothing moved this pass
            if not something_moved_in_pass:
                # print(f"Constraint propagation converged after {pass_num + 1} passes.")
                break
        # else: # If loop finished without break
            # print(f"Constraint propagation reached max passes ({num_passes}).")

    # --- Simulation Control Methods --- 
    def start_simulation(self):
        if not self.simulation_running:
            # Reset path and potentially time when starting
            self.pen_path_points.clear()
            self.current_simulation_angle_deg = 0.0 
            # TODO: Find the pen rod dynamically or allow setting it
            # For now, assume last added rod is the pen, using end point
            if self.rods:
                self.pen_rod_id = self.rods[-1].id
                self.pen_point_type = 'end'
            else:
                self.pen_rod_id = None
                
            interval_ms = int(self.simulation_time_step * 1000)
            self.simulation_timer.start(interval_ms) 
            self.simulation_running = True
            print("Simulation started")
            
    def stop_simulation(self):
        if self.simulation_running:
            self.simulation_timer.stop()
            self.simulation_running = False
            print("Simulation stopped")
            
    def _update_simulation(self):
        """Core simulation update loop called by the timer."""
        if not self.simulation_running:
            return

        # --- 1. Update Driving Components (Wheels) --- 
        master_angular_speed_deg_per_sec = 36.0 # TODO: Use master_speed from config
        angle_increment = master_angular_speed_deg_per_sec * self.simulation_time_step
        self.current_simulation_angle_deg = (self.current_simulation_angle_deg + angle_increment) % 360 # Update global angle for reference

        initial_targets: Dict[Tuple[int, str], QPointF] = {} # Store new wheel positions
        
        for wheel in self.wheels:
            # Update the wheel's internal angle
            wheel_angle_increment = angle_increment * wheel.speed_ratio
            wheel.current_angle_deg = (wheel.current_angle_deg + wheel_angle_increment) % 360
            
            # Calculate and store new positions for ALL connection points
            for point_id in wheel.connection_points:
                new_pos = wheel.get_connection_point_position(point_id)
                if new_pos:
                    initial_targets[(wheel.id, point_id)] = new_pos
        
        # --- 2. Update Constrained Components (Rods) using extracted method --- 
        self._propagate_constraints(initial_targets)

        # --- 3. Record Pen Path --- 
        # Find the actual pen rod
        pen_rod: Optional[Rod] = None
        for rod in self.rods:
            if rod.pen_distance_from_start is not None:
                pen_rod = rod
                break # Found the pen rod
        
        if pen_rod is not None:
            # Calculate the pen position along the rod
            pen_pos_canvas = pen_rod.get_point_at_distance(pen_rod.pen_distance_from_start)
            if pen_pos_canvas: # Ensure position calculation is valid
                pen_pos_screen = self._canvas_to_screen(pen_pos_canvas)
                # Add point if it's different from the last one to avoid duplicates
                if self.pen_path_points.isEmpty() or self.pen_path_points.last() != pen_pos_screen:
                    self.pen_path_points.append(pen_pos_screen)
        
        # --- 4. Trigger Repaint --- 
        self.update()
    # --- End Simulation --- 