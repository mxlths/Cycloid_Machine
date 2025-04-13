from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFocusEvent, QPolygonF
from components import Wheel, Rod, ConnectionPoint
import math
from typing import Optional, Union, List, Tuple, Dict

# Add PIL imports
from PIL import Image, ImageDraw

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
        self.pen_path_points: List[QPointF] = [] # Store canvas coordinates
        self.pen_rod_id: Optional[int] = None # ID of the rod acting as the pen
        self.pen_point_type: Optional[str] = 'end' # Which point on pen_rod_id? 'start' or 'end'
        self.reference_wheel_id: Optional[int] = None # ID of wheel defining the view reference frame during simulation
        self.canvas_wheel: Optional[Wheel] = None # The specific wheel designated as the canvas
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
        
        # Draw grid (static view)
        self._draw_grid(painter)
        
        # Draw components (static view)
        self._draw_components(painter)
        
        # Draw pen path (transform points relative to canvas wheel)
        if self.pen_path_points: # Check if list is not empty
            painter.setPen(QPen(Qt.GlobalColor.darkCyan, 1)) # Pen color
            
            transformed_path_points = []
            if self.canvas_wheel:
                # Transform points relative to the current canvas wheel position/angle
                center = self.canvas_wheel.center
                angle_deg = self.canvas_wheel.current_angle_deg
                angle_rad = math.radians(angle_deg)
                cos_a = math.cos(angle_rad)
                sin_a = math.sin(angle_rad)
                
                for rel_point in self.pen_path_points:
                    # Rotate forward
                    abs_x_rotated = rel_point.x() * cos_a - rel_point.y() * sin_a
                    abs_y_rotated = rel_point.x() * sin_a + rel_point.y() * cos_a
                    # Translate to absolute canvas position
                    abs_pos = QPointF(abs_x_rotated + center.x(), abs_y_rotated + center.y())
                    # Convert to screen coordinates
                    transformed_path_points.append(self._canvas_to_screen(abs_pos))
            else:
                # No canvas wheel, path is already absolute
                for abs_pos in self.pen_path_points:
                    transformed_path_points.append(self._canvas_to_screen(abs_pos))
            
            # Convert canvas points to screen points for drawing
            # screen_points = QPolygonF([self._canvas_to_screen(p) for p in self.pen_path_points])
            if transformed_path_points:
                 screen_points = QPolygonF(transformed_path_points)
                 painter.drawPolyline(screen_points)
        
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
            # Skip if this wheel is currently selected and being dragged (avoids self-snapping)
            if self.dragging and self.selected_component == wheel:
                 continue
                 
            for point_id, cp in wheel.connection_points.items(): # Iterate through points
                pos = wheel.get_connection_point_position(point_id)
                if pos:
                    dist_sq = (canvas_point.x() - pos.x())**2 + (canvas_point.y() - pos.y())**2
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        # Return component ID, the specific point ID, and position
                        nearest = ('wheel', wheel.id, point_id, pos) 
        
        # Check rod connection points (endpoints and mid-points)
        for rod in self.rods:
            is_selected_rod = self.dragging and self.selected_component == rod
            
            # Check start point (unless it's the one being dragged)
            if not (is_selected_rod and self.dragging_point == 'start'):
                pos_start = rod.start_pos
                dist_sq_start = (canvas_point.x() - pos_start.x())**2 + (canvas_point.y() - pos_start.y())**2
                if dist_sq_start < min_dist_sq:
                    min_dist_sq = dist_sq_start
                    nearest = ('rod_start', rod.id, 'start', pos_start)
                
            # Check end point (unless it's the one being dragged)
            if not (is_selected_rod and self.dragging_point == 'end'):
                pos_end = rod.end_pos
                dist_sq_end = (canvas_point.x() - pos_end.x())**2 + (canvas_point.y() - pos_end.y())**2
                if dist_sq_end < min_dist_sq:
                    min_dist_sq = dist_sq_end
                    nearest = ('rod_end', rod.id, 'end', pos_end)

            # Check rod mid-point (can always be snapped to, even on the selected rod)
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
            self.dragging_point and # Ensure we were dragging an endpoint ('start' or 'end')
            self.hover_connection):
            
            DEBUG_CONSTRAINTS = True # Define locally for this debug print
            if DEBUG_CONSTRAINTS: print(f"DEBUG mouseReleaseEvent: hover_connection = {self.hover_connection}") # DEBUG PRINT
            
            target_info = self.hover_connection # (component_type, component_id, point_id, point_position)
            target_comp_type = target_info[0]
            target_comp_id = target_info[1]
            target_point_id = target_info[2] # e.g., 'p1', 'start', 'end', 'mid'
            target_pos = target_info[3]
            
            connection_details = (target_comp_id, target_point_id)
            connection_made = False
            
            # Check if the target is valid for connection
            # Allow connecting start/end to wheel points, rod start/end, or rod mid
            if target_comp_type in ['wheel', 'rod_start', 'rod_end', 'rod_mid']:
            
                if self.dragging_point == 'start':
                    self.selected_component.start_connection = connection_details
                    # Force position to snap exactly
                    self.selected_component.start_pos = target_pos 
                    connection_made = True
                    print(f"Rod {self.selected_component.id} start connected to {target_comp_type} {target_comp_id}::{target_point_id}")
                    
                elif self.dragging_point == 'end':
                    self.selected_component.end_connection = connection_details
                    # Force position to snap exactly
                    self.selected_component.end_pos = target_pos
                    connection_made = True
                    print(f"Rod {self.selected_component.id} end connected to {target_comp_type} {target_comp_id}::{target_point_id}")

                # If a connection was made, recalculate length and update constraints
                if connection_made:
                     # Recalculate length based on potentially changed positions
                    dx = self.selected_component.end_pos.x() - self.selected_component.start_pos.x()
                    dy = self.selected_component.end_pos.y() - self.selected_component.start_pos.y()
                    new_length = math.hypot(dx, dy)
                    if abs(new_length - self.selected_component.length) > 1e-4:
                         self.selected_component.length = new_length
                         # Refresh parameter panel if length changed
                         self.component_selected.emit(self.selected_component) 

                    # Propagate constraints immediately after connection
                    # Determine initial targets based on the point that just got connected
                    initial_targets = {}
                    if self.dragging_point == 'start':
                        initial_targets[(self.selected_component.id, 'start')] = self.selected_component.start_pos
                        if self.selected_component.mid_point_distance is not None:
                             initial_targets[(self.selected_component.id, 'mid')] = self.selected_component.get_point_at_distance(self.selected_component.mid_point_distance)
                    elif self.dragging_point == 'end':
                         initial_targets[(self.selected_component.id, 'end')] = self.selected_component.end_pos
                         if self.selected_component.mid_point_distance is not None:
                              initial_targets[(self.selected_component.id, 'mid')] = self.selected_component.get_point_at_distance(self.selected_component.mid_point_distance)
                    
                    # Also include the target point itself in the propagation
                    initial_targets[(target_comp_id, target_point_id)] = target_pos
                    
                    self._propagate_constraints(initial_targets)
            else:
                print(f"Warning: Invalid connection target type: {target_comp_type}")

        # --- Original Cleanup ---
        self.hover_connection = None # Clear hover connection indicator regardless
        
        # Clear dragging state (ensure this happens AFTER connection logic)
        self.dragging = False
        self.drag_start = None
        self.dragging_point = None
        
        self.update() # Trigger repaint
        
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
            initial_targets = {} # Prepare targets for constraint propagation
            
            # Apply delta based on component type
            if isinstance(self.selected_component, Wheel):
                current_center = self.selected_component.center
                new_center = QPointF(current_center.x() + delta_x, current_center.y() + delta_y)
                self.selected_component.move_to(new_center)
                # Propagate constraints after moving a wheel
                # Get new positions for ALL connection points based on the new center
                for point_id in self.selected_component.connection_points:
                    new_pos = self.selected_component.get_connection_point_position(point_id)
                    if new_pos:
                        initial_targets[(self.selected_component.id, point_id)] = new_pos
                        
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
                initial_targets[(self.selected_component.id, 'start')] = self.selected_component.start_pos
                initial_targets[(self.selected_component.id, 'end')] = self.selected_component.end_pos
                # Also update mid-point target if it exists
                if self.selected_component.mid_point_distance is not None:
                     initial_targets[(self.selected_component.id, 'mid')] = self.selected_component.get_point_at_distance(self.selected_component.mid_point_distance)

            # Propagate constraints if any targets were generated
            if initial_targets:
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
             
        # Clear canvas wheel reference if it was deleted
        if self.canvas_wheel and self.canvas_wheel.id == component_id:
            self.canvas_wheel = None
            print(f"Canvas wheel (ID: {component_id}) deleted.")

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
           Refactored: Calculate all targets at start of pass, apply changes at end.
        """
        DEBUG_CONSTRAINTS = True # Set to False to disable prints
        if DEBUG_CONSTRAINTS: print("--- Starting Constraint Propagation (Refactored) ---")
        if DEBUG_CONSTRAINTS and initial_targets: print(f"Initial Targets: {initial_targets}")
        
        num_passes = 100 

        # Store current positions to detect convergence
        last_positions = {} 

        for pass_num in range(num_passes):
            if DEBUG_CONSTRAINTS: print(f"\\n--- Pass {pass_num + 1} ---")

            # --- Step 1: Get current state & targets for this pass ---
            current_positions = self._get_current_connection_point_positions()
            if not last_positions: # First pass
                last_positions = current_positions.copy() # Store initial state
            
            # Use targets derived from the beginning of this pass
            # Apply external initial_targets only on the very first pass
            target_positions_this_pass = current_positions.copy()
            if initial_targets and pass_num == 0:
                target_positions_this_pass.update(initial_targets)

            # Store intended moves calculated during this pass
            intended_rod_positions: Dict[int, Tuple[QPointF, QPointF]] = {}
            for rod in self.rods: # Initialize with current positions
                 intended_rod_positions[rod.id] = (QPointF(rod.start_pos), QPointF(rod.end_pos))

            # --- Step 2: Calculate Endpoint Adjustments (Phase 1 Logic) ---
            if DEBUG_CONSTRAINTS: print("  Calculating Endpoint Adjustments...")
            for rod in self.rods:
                current_start, current_end = intended_rod_positions[rod.id] # Use potentially adjusted pos from previous step in THIS pass? No, use start-of-pass state
                current_start = QPointF(rod.start_pos)
                current_end = QPointF(rod.end_pos)
                original_length = rod.length
                
                has_start_connection = rod.start_connection is not None
                has_end_connection = rod.end_connection is not None

                # Use consistent targets from start of this pass
                target_start = target_positions_this_pass.get(rod.start_connection) if has_start_connection else None
                target_end = target_positions_this_pass.get(rod.end_connection) if has_end_connection else None

                # Calculate intended positions based on constraints
                intended_start = QPointF(current_start)
                intended_end = QPointF(current_end)
                
                if target_start is not None and target_end is not None:
                    # Both ends targeted: Prioritize start, maintain length
                    intended_start = target_start
                    vec_S_TE = target_end - intended_start
                    dist = math.hypot(vec_S_TE.x(), vec_S_TE.y())
                    if dist > 1e-6 and original_length > 1e-6:
                        intended_end = intended_start + vec_S_TE * (original_length / dist)
                    else: intended_end = intended_start
                elif target_start is not None:
                    # Start targeted: Move start, calculate end maintaining length
                    intended_start = target_start
                    vec_S_E = current_end - intended_start
                    dist = math.hypot(vec_S_E.x(), vec_S_E.y())
                    if dist > 1e-6 and original_length > 1e-6:
                        intended_end = intended_start + vec_S_E * (original_length / dist)
                    else: intended_end = intended_start
                elif target_end is not None:
                    # End targeted: Move end, calculate start maintaining length
                    intended_end = target_end
                    vec_E_S = current_start - intended_end
                    dist = math.hypot(vec_E_S.x(), vec_E_S.y())
                    if dist > 1e-6 and original_length > 1e-6:
                        intended_start = intended_end + vec_E_S * (original_length / dist)
                    else: intended_start = intended_end
                
                # Store calculated positions for this rod
                intended_rod_positions[rod.id] = (intended_start, intended_end)

            # --- Step 3: Calculate Mid-Point Adjustments (Phase 2 Logic) ---
            # This phase adjusts positions calculated in Step 2 based on mid-point constraints
            if DEBUG_CONSTRAINTS: print("  Calculating Mid-Point Adjustments...")
            for rod in self.rods:
                if rod.mid_point_connection is None: continue # Skip if no mid-connection

                # Get positions calculated by endpoint logic (Step 2)
                current_start, current_end = intended_rod_positions[rod.id] 
                original_length = rod.length # Use fixed length
                mid_dist = max(0.0, min(original_length, rod.mid_point_distance if rod.mid_point_distance is not None else 0.0))

                target_mid = target_positions_this_pass.get(rod.mid_point_connection) # Target from start of pass
                if target_mid is None: continue # Skip if mid-target doesn't exist

                # Calculate current mid position based on Step 2 results
                current_mid = QPointF()
                vec = current_end - current_start
                current_calc_len = math.hypot(vec.x(),vec.y())
                if current_calc_len > 1e-6:
                     ratio = mid_dist / current_calc_len
                     current_mid = current_start + vec * ratio
                else:
                     current_mid = current_start # Degenerate case

                # If mid-point needs correction
                if (target_mid - current_mid).manhattanLength() > 1e-5:
                    if DEBUG_CONSTRAINTS: print(f"    Rod {rod.id} Needs Mid-Point Correction")
                    
                    # Determine fixed ends based on initial targets for the PASS
                    target_start = target_positions_this_pass.get(rod.start_connection)
                    target_end = target_positions_this_pass.get(rod.end_connection)
                    start_is_fixed = target_start is not None
                    end_is_fixed = target_end is not None
                    
                    intended_start_p2 = QPointF(current_start) # Start with Step 2 results
                    intended_end_p2 = QPointF(current_end)

                    if start_is_fixed and end_is_fixed:
                        # Both fixed: Cannot satisfy mid-point AND endpoints. Prioritize endpoints (already done in Step 2).
                        # No change needed here, rely on Step 2 results.
                         if DEBUG_CONSTRAINTS: print(f"      Mid-Point Case 4 (Both Fixed): No change, using Step 2 results.")
                         pass 
                    elif start_is_fixed:
                        # Start fixed, pivot end
                        intended_start_p2 = target_start # Re-affirm start is fixed
                        vec_S_TM = target_mid - intended_start_p2
                        if mid_dist > 1e-6:
                            intended_end_p2 = intended_start_p2 + vec_S_TM * (original_length / mid_dist)
                        else: # Mid-point is at start, maintain original orientation relative to start
                            angle = math.atan2(current_end.y() - current_start.y(), current_end.x() - current_start.x())
                            intended_end_p2 = intended_start_p2 + QPointF(original_length * math.cos(angle), original_length * math.sin(angle))
                        if DEBUG_CONSTRAINTS: print(f"      Mid-Point Case 2 (Start Fixed): Calculated End = {intended_end_p2}")
                    elif end_is_fixed:
                        # End fixed, pivot start
                        intended_end_p2 = target_end # Re-affirm end is fixed
                        vec_E_TM = target_mid - intended_end_p2
                        dist_end_mid = original_length - mid_dist
                        if dist_end_mid > 1e-6:
                            intended_start_p2 = intended_end_p2 + vec_E_TM * (original_length / dist_end_mid)
                        else: # Mid-point is at end, maintain original orientation relative to end
                            angle = math.atan2(current_start.y() - current_end.y(), current_start.x() - current_end.x())
                            intended_start_p2 = intended_end_p2 + QPointF(original_length * math.cos(angle), original_length * math.sin(angle))
                        if DEBUG_CONSTRAINTS: print(f"      Mid-Point Case 3 (End Fixed): Calculated Start = {intended_start_p2}")
                    else:
                        # Neither fixed: Translate rod to place mid-point
                        angle = math.atan2(current_end.y() - current_start.y(), current_end.x() - current_start.x())
                        intended_start_p2 = QPointF(target_mid.x() - mid_dist * math.cos(angle), target_mid.y() - mid_dist * math.sin(angle))
                        intended_end_p2 = QPointF(target_mid.x() + (original_length - mid_dist) * math.cos(angle), target_mid.y() + (original_length - mid_dist) * math.sin(angle))
                        if DEBUG_CONSTRAINTS: print(f"      Mid-Point Case 1 (Neither Fixed): Calculated Start={intended_start_p2}, End={intended_end_p2}")

                    # Store the adjusted positions from mid-point phase
                    intended_rod_positions[rod.id] = (intended_start_p2, intended_end_p2)

            # --- Step 4: Apply all calculated moves for this pass ---
            if DEBUG_CONSTRAINTS: print("  Applying Calculated Moves...")
            something_moved_in_pass = False
            for rod in self.rods:
                intended_start, intended_end = intended_rod_positions[rod.id]
                
                # Check if positions actually changed significantly
                if (intended_start - rod.start_pos).manhattanLength() > 1e-5 or \
                   (intended_end - rod.end_pos).manhattanLength() > 1e-5:
                    rod.start_pos = intended_start
                    rod.end_pos = intended_end
                    something_moved_in_pass = True
                    if DEBUG_CONSTRAINTS: print(f"    Rod {rod.id} updated.")
            
            # --- Step 5: Check for Convergence ---
            if not something_moved_in_pass:
                 if DEBUG_CONSTRAINTS: print(f"--- Constraint propagation converged after {pass_num + 1} passes. ---")
                 break
            
            # Update last_positions for next pass convergence check (optional)
            last_positions = self._get_current_connection_point_positions()

        else: # If loop finished without break
            if DEBUG_CONSTRAINTS: print(f"--- Constraint propagation reached max passes ({num_passes}). ---")
            
    # --- Simulation Control Methods ---
    def start_simulation(self):
        if not self.simulation_running:
            # Reset path and potentially time when starting
            self.pen_path_points.clear()
            self.current_simulation_angle_deg = 0.0 
            
            # Set reference frame to the canvas wheel (if it exists)
            if self.canvas_wheel:
                self.reference_wheel_id = self.canvas_wheel.id
                print(f"Simulation started. Reference Frame: Canvas Wheel {self.reference_wheel_id}")
            else:
                # Fallback to first wheel if no canvas wheel (optional)
                if self.wheels:
                     self.reference_wheel_id = self.wheels[0].id
                     print(f"Simulation started. No canvas wheel found. Using Wheel {self.reference_wheel_id} as reference.")
                else:
                     self.reference_wheel_id = None
                     print("Simulation started. No wheels to use as reference frame.")
            
            # TODO: Reset component angles to initial state?
            # for wheel in self.wheels:
            #     wheel.current_angle_deg = 0.0 # Or load initial angle from config?
                
            interval_ms = int(self.simulation_time_step * 1000)
            self.simulation_timer.start(interval_ms) 
            self.simulation_running = True
            # print("Simulation started") # Redundant print
            
    def stop_simulation(self):
        if self.simulation_running:
            self.simulation_timer.stop()
            self.simulation_running = False
            self.reference_wheel_id = None # Clear reference frame
            print("Simulation stopped")
            
    def _update_simulation(self):
        """Core simulation update loop called by the timer."""
        if not self.simulation_running:
            return

        # --- 1. Update Driving Components (Wheels) --- 
        # Remove master speed and global angle increment
        # self.current_simulation_angle_deg = (self.current_simulation_angle_deg + angle_increment) % 360 # Update global angle for reference

        initial_targets: Dict[Tuple[int, str], QPointF] = {} # Store new wheel positions
        
        for wheel in self.wheels:
            # Update the wheel's internal angle based on its own rotation rate
            # Assume rotation_rate is degrees per second
            wheel_angle_increment = wheel.rotation_rate * self.simulation_time_step
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
            # Calculate the pen position along the rod (in absolute canvas coordinates)
            pen_pos_canvas = pen_rod.get_point_at_distance(pen_rod.pen_distance_from_start)
            
            if pen_pos_canvas: # Ensure position calculation is valid
                point_to_store = pen_pos_canvas # Default to absolute position
                
                # If we have a canvas wheel, transform to its relative coordinate system
                if self.canvas_wheel:
                    center = self.canvas_wheel.center
                    angle_deg = self.canvas_wheel.current_angle_deg
                    angle_rad = -math.radians(angle_deg) # Use negative angle for reverse rotation
                    
                    relative_pos = pen_pos_canvas - center
                    
                    # Rotate relative position backwards
                    rotated_relative_x = relative_pos.x() * math.cos(angle_rad) - relative_pos.y() * math.sin(angle_rad)
                    rotated_relative_y = relative_pos.x() * math.sin(angle_rad) + relative_pos.y() * math.cos(angle_rad)
                    
                    point_to_store = QPointF(rotated_relative_x, rotated_relative_y)
                    
                # Store the calculated point (either absolute or relative)
                # Add point if it's different from the last one (using the stored coordinate system)
                if not self.pen_path_points or self.pen_path_points[-1] != point_to_store:
                    self.pen_path_points.append(point_to_store)
        
        # --- 4. Trigger Repaint --- 
        self.update()
    # --- End Simulation --- 
    
    def generate_image(self, filename: str, width_px: int, height_px: int, line_color: str = "black", line_width: int = 1):
        """Generates an image of the pen path using Pillow."""
        if not self.pen_path_points or len(self.pen_path_points) < 2:
            print("No pen path recorded (or path too short) to generate image.")
            return

        # 1. Calculate bounds of self.pen_path_points (List[QPointF])
        min_x = min(p.x() for p in self.pen_path_points)
        max_x = max(p.x() for p in self.pen_path_points)
        min_y = min(p.y() for p in self.pen_path_points)
        max_y = max(p.y() for p in self.pen_path_points)

        path_width = max_x - min_x
        path_height = max_y - min_y

        # 2. Determine scale and offset to fit path in width_px/height_px
        padding = 0.05 # 5% padding
        draw_area_width = width_px * (1 - 2 * padding)
        draw_area_height = height_px * (1 - 2 * padding)
        padding_x_px = width_px * padding
        padding_y_px = height_px * padding

        # Handle zero dimensions (single point or straight line)
        if path_width == 0 and path_height == 0:
             scale = 1 # Arbitrary scale, will just be a point
        elif path_width == 0:
             scale = draw_area_height / path_height
        elif path_height == 0:
             scale = draw_area_width / path_width
        else:
             scale = min(draw_area_width / path_width, draw_area_height / path_height)
        
        scaled_path_width = path_width * scale
        scaled_path_height = path_height * scale
        
        # Calculate offset to center the scaled path within the drawing area
        offset_x = padding_x_px + (draw_area_width - scaled_path_width) / 2 - (min_x * scale)
        offset_y = padding_y_px + (draw_area_height - scaled_path_height) / 2 - (min_y * scale)
        
        # Helper function to transform canvas coords to image pixel coords
        def transform(canvas_point: QPointF) -> Tuple[int, int]:
            px = int(canvas_point.x() * scale + offset_x)
            py = int(canvas_point.y() * scale + offset_y)
            return px, py

        # 3. Create PIL Image (RGB, white background)
        image = Image.new("RGB", (width_px, height_px), "white")
        # 4. Create ImageDraw object
        draw = ImageDraw.Draw(image)

        # 5. Iterate through path points, transform to image coords, draw lines
        transformed_points = [transform(p) for p in self.pen_path_points]
        
        # Draw lines between consecutive points
        draw.line(transformed_points, fill=line_color, width=line_width, joint="curve")
        
        # Optional: Draw a small circle at the start point? 
        # if transformed_points:
        #     start_px, start_py = transformed_points[0]
        #     radius = 3
        #     draw.ellipse((start_px-radius, start_py-radius, start_px+radius, start_py+radius), fill='green')

        # 6. Save image
        try:
            image.save(filename)
            print(f"Image successfully saved to {filename}")
        except Exception as e:
            print(f"Error saving image to {filename}: {e}")

    def add_canvas_wheel(self, center: QPointF = QPointF(0,0), diameter: float = 500.0):
        """Adds a special wheel representing the canvas. Only one allowed."""
        if self.canvas_wheel is not None:
            print("Canvas wheel already exists. Only one allowed.")
            # Optionally, could select the existing canvas wheel here
            return

        new_id = self._next_component_id
        self._next_component_id += 1
        
        # Create the canvas wheel
        canvas_wheel_obj = Wheel(id=new_id, center=center, diameter=diameter)
        # Maybe add a default connection point at center? Or none?
        # canvas_wheel_obj.add_connection_point('center', 0.0) 
        
        # Assign and add to lists/dicts
        self.canvas_wheel = canvas_wheel_obj
        self.wheels.append(canvas_wheel_obj)
        self.components_by_id[new_id] = canvas_wheel_obj
        print(f"Added Canvas Wheel (ID: {new_id})")
        self.update() 
        # return canvas_wheel_obj # Return if needed elsewhere