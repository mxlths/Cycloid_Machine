from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFocusEvent, QPolygonF
from components import Wheel, Rod, ConnectionPoint
import math
from typing import Optional, Union, List, Tuple, Dict

# Add PIL imports
from PIL import Image, ImageDraw

# Import the sympy solver function (use absolute import)
# from .sympy_solver import calculate_path_sympy 
from sympy_solver import calculate_path_sympy

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
        
        # Add flag for rod endpoint drag state
        self.dragging_endpoint_was_connected = False
        
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
        self.component_drag_origin_screen = None
        self.hover_component = None
        self.dragging_point = None  # 'start', 'end', or 'mid' for rod points
        self.dragging_midpoint_was_connected = False # Track if mid-point was connected at drag start
        
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
            painter.setPen(QPen(Qt.GlobalColor.black, 1)) # Pen color
            
            # Convert absolute canvas points to screen points for drawing
            screen_points_list = [self._canvas_to_screen(p) for p in self.pen_path_points if not (math.isnan(p.x()) or math.isnan(p.y()))] 
            
            if screen_points_list:
                 screen_points_poly = QPolygonF(screen_points_list)
                 painter.drawPolyline(screen_points_poly)
        
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
        
    def _find_nearest_connection_point(self, canvas_point: QPointF, 
                                         dragged_component: Optional[Union[Wheel, Rod]] = None, 
                                         dragged_point_type: Optional[str] = None) -> Optional[Tuple]:
        """Find the NEAREST connection point (wheel, rod start/end/mid) to a canvas point.
           Corrected logic to find the overall minimum distance.
           Now accepts dragged component info to correctly ignore the dragged point.
        Returns: Tuple (component_type, component_id, point_id, point_position) or None
        """
        min_dist_sq = (self.connection_snap_distance / self.pixels_per_mm) ** 2
        nearest_point_info = None

        # Check wheel connection points (Wheels currently cannot be dragged by connection points)
        for wheel in self.wheels:
            # Optimization: skip check if point is way outside wheel bounds (optional)
            # ... 
            for point_id, cp in wheel.connection_points.items():
                pos = wheel.get_connection_point_position(point_id)
                if pos:
                    dist_sq = (canvas_point.x() - pos.x())**2 + (canvas_point.y() - pos.y())**2
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        # Use specific type 'wheel'
                        nearest_point_info = ('wheel', wheel.id, point_id, pos)

        # Check rod connection points (endpoints and mid-points)
        for rod in self.rods:
            # Determine if this rod is the one being dragged, using passed arguments
            is_dragged_rod = dragged_component == rod
            point_being_dragged_on_this_rod = dragged_point_type if is_dragged_rod else None

            # Check start point (only if it's NOT the point being dragged)
            if point_being_dragged_on_this_rod != 'start':
                pos_start = rod.start_pos
                dist_sq_start = (canvas_point.x() - pos_start.x())**2 + (canvas_point.y() - pos_start.y())**2
                if dist_sq_start < min_dist_sq:
                    min_dist_sq = dist_sq_start # Update min distance found so far
                    nearest_point_info = ('rod_start', rod.id, 'start', pos_start)

            # Check end point (only if it's NOT the point being dragged)
            if point_being_dragged_on_this_rod != 'end':
                pos_end = rod.end_pos
                dist_sq_end = (canvas_point.x() - pos_end.x())**2 + (canvas_point.y() - pos_end.y())**2
                if dist_sq_end < min_dist_sq:
                    min_dist_sq = dist_sq_end # Update min distance found so far
                    nearest_point_info = ('rod_end', rod.id, 'end', pos_end)

            # Check rod mid-point (only if it exists and it's NOT the point being dragged)
            if rod.mid_point_distance is not None and point_being_dragged_on_this_rod != 'mid':
                 pos_mid = rod.get_point_at_distance(rod.mid_point_distance)
                 dist_sq_mid = (canvas_point.x() - pos_mid.x())**2 + (canvas_point.y() - pos_mid.y())**2
                 if dist_sq_mid < min_dist_sq:
                    min_dist_sq = dist_sq_mid # Update min distance found so far
                    nearest_point_info = ('rod_mid', rod.id, 'mid', pos_mid)

        return nearest_point_info

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
                    # Store initial connection state for the dragged endpoint
                    self.dragging_endpoint_was_connected = rod.start_connection is not None 
                    break # Found component
                elif self._is_near_rod_endpoint(rod, canvas_point, 'end'):
                    newly_selected_component = rod # Mark for selection
                    self.dragging = True
                    self.dragging_point = 'end'
                    self.drag_start = canvas_point
                    # Store initial connection state for the dragged endpoint
                    self.dragging_endpoint_was_connected = rod.end_connection is not None 
                    break # Found component
            
            # Check if clicking on a rod mid-point
            if not newly_selected_component:
                for rod in self.rods:
                    if rod.mid_point_distance is not None:
                        mid_canvas = rod.get_point_at_distance(rod.mid_point_distance)
                        mid_screen = self._canvas_to_screen(mid_canvas)
                        # --- MODIFIED: Convert event.pos() to QPointF before comparison ---
                        screen_pos_qpoint = event.pos() # Get QPoint
                        screen_pos_qpointf = QPointF(screen_pos_qpoint) # Convert to QPointF
                        
                        # Use a slightly larger tolerance for clicking the mid-point marker
                        click_tolerance = self.connection_snap_distance # Use snap distance for clicking
                        # Now compare using QPointF's tuple
                        if math.dist((screen_pos_qpointf.x(), screen_pos_qpointf.y()), 
                                     (mid_screen.x(), mid_screen.y())) < click_tolerance:
                            newly_selected_component = rod
                            self.dragging = True
                            self.dragging_point = 'mid'
                            self.drag_start = canvas_point
                            self.dragging_midpoint_was_connected = rod.mid_point_connection is not None
                            # Prevent the whole rod from moving when dragging mid-point for connection
                            # self.dragging = False # Maybe not needed if move logic checks dragging_point
                            break # Found component

            # Check for wheel selection (only if rod not selected)
            if not newly_selected_component:
                for wheel in self.wheels:
                    if wheel.contains_point(canvas_point):
                        newly_selected_component = wheel # Mark for selection
                        self.dragging = True
                        # --- MODIFIED: Store both canvas and screen start positions ---
                        self.drag_start = canvas_point # Needed for component position update logic
                        self.component_drag_origin_screen = event.pos() # SCREEN position for delta calculation
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
            
        if self.dragging and self.selected_component and self.drag_start:
            # --- MODIFIED: Convert event.pos() to QPointF --- 
            current_pos_qpoint = event.pos()
            current_pos = QPointF(current_pos_qpoint) # Convert QPoint to QPointF
            
            # Calculate delta using consistent QPointF types
            delta = current_pos - QPointF(self.drag_start) # Ensure drag_start is also QPointF (should be, but explicit)
            canvas_delta = self._screen_to_canvas(current_pos) - self._screen_to_canvas(QPointF(self.drag_start))
            
            # Dragging the entire component (Wheel or Rod Body)
            # --- MODIFIED: Don't move component if dragging a connection point --- 
            if isinstance(self.selected_component, Wheel) and not self.dragging_point:
                # --- MODIFIED: Wheel Drag Logic using Screen Coordinates --- 
                if self.component_drag_origin_screen:
                    current_pos_screen = event.pos() # Current SCREEN pos
                    delta_screen = current_pos_screen - self.component_drag_origin_screen
                    new_center_screen = self.component_drag_origin_screen + delta_screen
                    # Convert final screen pos to canvas, snap, and set
                    new_center_canvas = self._screen_to_canvas(QPointF(new_center_screen))
                    snapped_new_center_canvas = self._snap_to_grid(new_center_canvas)
                    self.selected_component.center = snapped_new_center_canvas
                    # --- ADDED: Propagate after wheel drag --- 
                    wheel_targets = {}
                    for point_id in self.selected_component.connection_points:
                        new_pos = self.selected_component.get_connection_point_position(point_id)
                        if new_pos:
                            wheel_targets[(self.selected_component.id, point_id)] = new_pos
                    if wheel_targets:
                        self._propagate_constraints(wheel_targets)
                    # --- End added propagation ---
                # --- End Wheel Drag Logic ---
            elif isinstance(self.selected_component, Rod) and not self.dragging_point:
                # Rod dragging uses canvas coordinates and original positions (seems okay)
                snapped_new_start = self._snap_to_grid(self.selected_component.original_pos_during_drag + canvas_delta)
                actual_canvas_delta = snapped_new_start - self.selected_component.original_pos_during_drag
                self.selected_component.start_pos = self.selected_component.original_pos_during_drag + actual_canvas_delta
                self.selected_component.end_pos = self.selected_component.original_end_during_drag + actual_canvas_delta
                # --- ADDED: Propagate after rod body drag --- 
                rod_targets = {
                    (self.selected_component.id, 'start'): self.selected_component.start_pos,
                    (self.selected_component.id, 'end'): self.selected_component.end_pos
                }
                self._propagate_constraints(rod_targets)
                # --- End added propagation ---
                
            # Dragging a rod connection point ('start', 'end', or 'mid')
            elif isinstance(self.selected_component, Rod) and self.dragging_point:
                # --- MODIFIED: Update rod position only for start/end drags using correct methods --- 
                snapped_canvas_pos = self._snap_to_grid(canvas_point)
                initial_targets_for_drag = {} # Prepare targets for propagation
                
                if self.dragging_point == 'start':
                    # Call the method to move the start point
                    self.selected_component.move_start_to(snapped_canvas_pos)
                    # Set target for propagation
                    initial_targets_for_drag[(self.selected_component.id, 'start')] = self.selected_component.start_pos
                elif self.dragging_point == 'end':
                    # Call the method to move the end point
                    self.selected_component.move_end_to(snapped_canvas_pos)
                    # Set target for propagation
                    initial_targets_for_drag[(self.selected_component.id, 'end')] = self.selected_component.end_pos
                    
                # (No position update needed if dragging_point == 'mid')

                # --- ADDED: Propagate constraints after dragging an endpoint --- 
                # Also include mid-point target if it exists, based on the NEW positions
                if self.dragging_point in ['start', 'end'] and self.selected_component.mid_point_distance is not None:
                    mid_pos = self.selected_component.get_point_at_distance(self.selected_component.mid_point_distance)
                    initial_targets_for_drag[(self.selected_component.id, 'mid')] = mid_pos
                    
                # Call propagation if we moved an endpoint
                if self.dragging_point in ['start', 'end']:
                    self._propagate_constraints(initial_targets_for_drag)
                # --- End added propagation ---
                
                # Find potential connection target for hover effect (for all point types)
                self.hover_connection = self._find_nearest_connection_point(canvas_point, 
                                                                            dragged_component=self.selected_component, 
                                                                            dragged_point_type=self.dragging_point)
                
                # Filter out snapping to the point being dragged (This check is now done inside _find_nearest)
                # if self.hover_connection and \
                #    self.hover_connection[0].startswith('rod') and \
                #    self.hover_connection[1] == self.selected_component.id and \
                #    self.hover_connection[2] == self.dragging_point:
                #      self.hover_connection = None
                    
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
        
        if self.dragging:
            # --- Store drag state BEFORE clearing self.dragging --- 
            final_selected_component = self.selected_component
            final_dragging_point = self.dragging_point
            
            self.dragging = False
            canvas_pos = self._screen_to_canvas(event.pos())
            # --- MODIFIED: Pass final drag state to find nearest --- 
            dropped_on_point = self._find_nearest_connection_point(canvas_pos, 
                                                                   dragged_component=final_selected_component,
                                                                   dragged_point_type=final_dragging_point)

            # Filter out dropping onto the exact point being dragged (This check is now redundant as _find_nearest handles it)
            # if dropped_on_point and \
            #    self.selected_component and \
            #    dropped_on_point[0].startswith('rod') and \
            #    dropped_on_point[1] == self.selected_component.id and \
            #    dropped_on_point[2] == self.dragging_point:
            #      dropped_on_point = None # Treat as dropping in empty space
            
            # Handle dropping a rod endpoint ('start' or 'end')
            if isinstance(final_selected_component, Rod) and (final_dragging_point == 'start' or final_dragging_point == 'end'):
                connection_made = False # Flag to check if connection happened
                if dropped_on_point:
                    target_type, target_id, target_point_type, target_pos = dropped_on_point
                    connection_tuple = (target_id, target_point_type)
                    
                    if final_dragging_point == 'start':
                        final_selected_component.start_connection = connection_tuple
                        # --- REINSTATED: Snap position --- 
                        final_selected_component.start_pos = QPointF(target_pos)
                        print(f"Rod {final_selected_component.id} start connected to {target_type} {target_id} point {target_point_type}")
                        connection_made = True
                    else: # dragging_point == 'end'
                        final_selected_component.end_connection = connection_tuple
                        # --- REINSTATED: Snap position --- 
                        final_selected_component.end_pos = QPointF(target_pos)
                        print(f"Rod {final_selected_component.id} end connected to {target_type} {target_id} point {target_point_type}")
                        connection_made = True
                        
                    # Endpoint is now connected, reset the flag
                    self.dragging_endpoint_was_connected = False 
                    
                    # --- REINSTATED: Recalculate length and propagate if connected ---
                    if connection_made:
                        # Recalculate length based on potentially changed positions
                        dx = final_selected_component.end_pos.x() - final_selected_component.start_pos.x()
                        dy = final_selected_component.end_pos.y() - final_selected_component.start_pos.y()
                        new_length = math.hypot(dx, dy)
                        if abs(new_length - final_selected_component.length) > 1e-4:
                             final_selected_component.length = new_length
                             # Refresh parameter panel if length changed
                             self.component_selected.emit(final_selected_component) 

                        # Propagate constraints immediately after connection
                        # Determine initial targets based on the point that just got connected
                        initial_targets = {}
                        target_pos_qpointf = QPointF(target_pos) # Ensure QPointF
                        
                        if final_dragging_point == 'start':
                            # Target is the moved start point
                            initial_targets[(final_selected_component.id, 'start')] = final_selected_component.start_pos 
                        elif final_dragging_point == 'end':
                             # Target is the moved end point
                             initial_targets[(final_selected_component.id, 'end')] = final_selected_component.end_pos
                        
                        # Also include the target point itself in the propagation
                        if target_type != 'grid': # Check if target is a component point
                            initial_targets[(target_id, target_point_type)] = target_pos_qpointf
                            
                        # --- ADDED: Include connecting rod's mid-point if exists --- 
                        if final_selected_component.mid_point_distance is not None:
                             # Calculate mid-point based on potentially updated start/end
                             mid_pos = final_selected_component.get_point_at_distance(final_selected_component.mid_point_distance)
                             initial_targets[(final_selected_component.id, 'mid')] = mid_pos
                        # --- End Added --- 
                        
                        # Call propagation if there are targets
                        if initial_targets:
                             print(f"DEBUG mouseReleaseEvent: Propagating constraints after connecting {final_dragging_point} of Rod {final_selected_component.id}. Initial targets: {initial_targets}")
                             self._propagate_constraints(initial_targets)
                        else:
                             print(f"DEBUG mouseReleaseEvent: No initial targets to propagate for Rod {final_selected_component.id} connection.")

                else:
                    # No connection point found, potentially break existing connection
                    if self.dragging_endpoint_was_connected:
                        if final_dragging_point == 'start':
                            final_selected_component.start_connection = None
                            print(f"Rod {final_selected_component.id} start disconnected by dropping.")
                        else: # dragging_point == 'end'
                            final_selected_component.end_connection = None
                            print(f"Rod {final_selected_component.id} end disconnected by dropping.")
                    # Also reset flag if dropped in empty space
                    self.dragging_endpoint_was_connected = False 

            # --- NEW: Handle dropping a rod mid-point ('mid') ---
            elif isinstance(final_selected_component, Rod) and final_dragging_point == 'mid':
                if dropped_on_point:
                    target_type, target_id, target_point_type, _ = dropped_on_point # Don't need target_pos for mid
                    # Create connection tuple
                    connection_tuple = (target_id, target_point_type)
                    # Set the mid-point connection
                    final_selected_component.mid_point_connection = connection_tuple
                    print(f"Rod {final_selected_component.id} mid-point connected to {target_type} {target_id} point {target_point_type}")
                    # Mid-point is now connected, reset the flag
                    self.dragging_midpoint_was_connected = False
                    
                    # --- Propagate constraints after mid-point connection --- 
                    initial_targets = {}
                    # Include the mid-point itself
                    mid_pos = final_selected_component.get_point_at_distance(final_selected_component.mid_point_distance)
                    initial_targets[(final_selected_component.id, 'mid')] = mid_pos
                    # Also include the target point 
                    if target_type != 'grid':
                        # Need the target pos here! Let's get it again (inefficient but simple)
                        target_pos = self._get_current_connection_point_positions().get((target_id, target_point_type))
                        if target_pos:
                             initial_targets[(target_id, target_point_type)] = target_pos
                             
                    if initial_targets:
                         print(f"DEBUG mouseReleaseEvent: Propagating constraints after connecting mid-point of Rod {final_selected_component.id}. Initial targets: {initial_targets}")
                         self._propagate_constraints(initial_targets)
                    # --- End mid-point propagation ---
                    
                else:
                    # No connection point found, potentially break existing mid-point connection
                    if self.dragging_midpoint_was_connected:
                        final_selected_component.mid_point_connection = None
                        print(f"Rod {final_selected_component.id} mid-point disconnected by dropping.")
                    # Also reset flag if dropped in empty space
                    self.dragging_midpoint_was_connected = False
            
            # Reset dragging state regardless of what happened
            self.dragging_point = None
            self.hover_connection = None
            # --- MODIFIED: Clear screen drag origin --- 
            self.component_drag_origin_screen = None 
            # Don't deselect component on release, keep it selected
            # self.selected_component = None 
            # self.component_selected.emit(None)
            self.update() # Redraw to remove hover effects etc.
        
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
        """Iteratively adjust rod positions based on endpoint and mid-point connections.
           Uses a two-phase approach within each pass.
        """
        DEBUG_CONSTRAINTS = True
        if DEBUG_CONSTRAINTS: print(f"\\n--- Propagating Constraints (Two-Phase: Endpoint + Midpoint) ---")
        if DEBUG_CONSTRAINTS: print(f"Initial Targets: {initial_targets}")

        # Store intended positions, initialized with current rod positions
        intended_rod_positions: Dict[int, Tuple[QPointF, QPointF]] = {
            rod.id: (QPointF(rod.start_pos), QPointF(rod.end_pos)) for rod in self.rods
        }

        # --- MODIFIED: Increase number of passes --- 
        num_passes = 500 # Increased from 100
        max_correction_threshold_sq = (0.1 / self.pixels_per_mm)**2

        for pass_num in range(num_passes):
            max_correction_this_pass_sq = 0.0
            # Get ALL current positions at the START of the pass (Wheels, Rod Ends)
            # We calculate mid-points dynamically within the pass
            current_positions = {}
            for wheel in self.wheels:
                for point_id in wheel.connection_points:
                    pos = wheel.get_connection_point_position(point_id)
                    if pos: current_positions[(wheel.id, point_id)] = pos
            for r_id, (r_start, r_end) in intended_rod_positions.items():
                 current_positions[(r_id, 'start')] = r_start
                 current_positions[(r_id, 'end')] = r_end

            # Apply initial external targets (these override current positions for this pass)
            pass_targets = current_positions.copy()
            if pass_num == 0 and initial_targets:
                 pass_targets.update(initial_targets)

            # --- PHASE 1: Calculate positions based on ENDPOINT constraints --- 
            phase1_intended_positions = intended_rod_positions.copy() # Start with previous pass results
            endpoint_fixed_flags: Dict[int, Tuple[bool, bool]] = {} # Store (start_fixed, end_fixed) flags for phase 2

            for rod in self.rods:
                rod_id = rod.id
                current_start, current_end = intended_rod_positions[rod_id]
                start_conn = rod.start_connection
                end_conn = rod.end_connection
                original_length = rod.length

                # Get endpoint targets from pass_targets (start-of-pass state + initial)
                target_start = None
                if start_conn and start_conn[1] != 'mid': # Ignore mid targets in phase 1
                    target_start = pass_targets.get(start_conn)

                target_end = None
                if end_conn and end_conn[1] != 'mid': # Ignore mid targets in phase 1
                    target_end = pass_targets.get(end_conn)

                intended_start = QPointF(current_start)
                intended_end = QPointF(current_end)
                start_fixed = False
                end_fixed = False

                if rod.fixed_length:
                    if target_start and target_end:
                        intended_start = target_start
                        vec = target_end - intended_start
                        dist = math.hypot(vec.x(), vec.y())
                        if dist > 1e-6: intended_end = intended_start + vec * (original_length / dist)
                        else: intended_end = intended_start
                        start_fixed = True
                        end_fixed = True # Both were targeted
                    elif target_start:
                        intended_start = target_start
                        vec = current_end - intended_start
                        dist = math.hypot(vec.x(), vec.y())
                        if dist > 1e-6: intended_end = intended_start + vec * (original_length / dist)
                        else: intended_end = intended_start
                        start_fixed = True
                    elif target_end:
                        intended_end = target_end
                        vec = current_start - intended_end
                        dist = math.hypot(vec.x(), vec.y())
                        if dist > 1e-6: intended_start = intended_end + vec * (original_length / dist)
                        else: intended_start = intended_end
                        end_fixed = True
                else: # Non-fixed length
                    if target_start and target_end:
                        intended_start = target_start
                        intended_end = target_end
                        start_fixed = True
                        end_fixed = True
                    elif target_start:
                        intended_start = target_start
                        start_fixed = True
                    elif target_end:
                        intended_end = target_end
                        end_fixed = True
                
                phase1_intended_positions[rod_id] = (intended_start, intended_end)
                endpoint_fixed_flags[rod_id] = (start_fixed, end_fixed)

            # --- Update positions dictionary AFTER Phase 1 calculations --- 
            positions_after_phase1 = pass_targets.copy() # Start with pass targets
            for r_id, (r_start, r_end) in phase1_intended_positions.items():
                 positions_after_phase1[(r_id, 'start')] = r_start
                 positions_after_phase1[(r_id, 'end')] = r_end
                 # Calculate and add mid-points based on Phase 1 results
                 rod = self.components_by_id.get(r_id) 
                 if rod and isinstance(rod, Rod) and rod.mid_point_distance is not None:
                     vec = r_end - r_start
                     current_len = math.hypot(vec.x(), vec.y())
                     if current_len > 1e-6:
                         ratio = max(0.0, min(1.0, rod.mid_point_distance / current_len))
                         mid_pos = r_start + vec * ratio
                         positions_after_phase1[(r_id, 'mid')] = mid_pos
                     else:
                         positions_after_phase1[(r_id, 'mid')] = r_start

            # --- PHASE 2: Adjust positions based on MIDPOINT constraints --- 
            phase2_intended_positions = phase1_intended_positions.copy() # Start with Phase 1 results

            for rod in self.rods:
                if rod.mid_point_connection is None: continue # Skip if no mid-connection
                
                rod_id = rod.id
                current_start, current_end = phase1_intended_positions[rod_id]
                start_fixed_p1, end_fixed_p1 = endpoint_fixed_flags[rod_id]
                mid_conn = rod.mid_point_connection
                original_length = rod.length # Needed for pivoting
                mid_dist = max(0.0, min(original_length, rod.mid_point_distance if rod.mid_point_distance is not None else 0.0))

                # Get the target position for the mid-point from the dictionary updated after Phase 1
                target_mid = positions_after_phase1.get(mid_conn)
                if target_mid is None: continue # Skip if mid-target doesn't exist or wasn't calculated

                # Calculate current mid position based on Phase 1 results
                mid_phase1 = QPointF()
                vec_p1 = current_end - current_start
                len_p1 = math.hypot(vec_p1.x(), vec_p1.y())
                if len_p1 > 1e-6:
                     ratio = mid_dist / len_p1
                     mid_phase1 = current_start + vec_p1 * ratio
                else:
                     mid_phase1 = current_start 

                # If mid-point needs correction (more than tolerance)
                if QPointF.dotProduct(target_mid - mid_phase1, target_mid - mid_phase1) > max_correction_threshold_sq:
                    
                    intended_start_p2 = QPointF(current_start)
                    intended_end_p2 = QPointF(current_end)

                    if start_fixed_p1 and end_fixed_p1:
                        # Case 4: Both ends fixed by endpoints. Cannot satisfy mid-point. Do nothing.
                        pass 
                    elif start_fixed_p1:
                        # Case 2: Start fixed, pivot end (Requires fixed length)
                        if rod.fixed_length:
                            intended_start_p2 = current_start # Keep start fixed
                            vec_S_TM = target_mid - intended_start_p2
                            dist_S_TM = math.hypot(vec_S_TM.x(), vec_S_TM.y())
                            if mid_dist > 1e-6 and dist_S_TM > 1e-6:
                                # Use triangle similarity or vector rotation
                                intended_end_p2 = intended_start_p2 + vec_S_TM * (original_length / mid_dist)
                            else: # Degenerate case, mid is at start, try to maintain angle
                                angle = math.atan2(vec_p1.y(), vec_p1.x())
                                intended_end_p2 = intended_start_p2 + QPointF(original_length * math.cos(angle), original_length * math.sin(angle))
                        else: 
                            # Non-fixed length - cannot pivot end. Prioritize fixed start.
                            pass # Do not apply mid-point correction in this case
                    elif end_fixed_p1:
                        # Case 3: End fixed, pivot start (Requires fixed length)
                         if rod.fixed_length:
                            intended_end_p2 = current_end # Keep end fixed
                            vec_E_TM = target_mid - intended_end_p2
                            dist_E_TM = math.hypot(vec_E_TM.x(), vec_E_TM.y())
                            dist_end_mid = original_length - mid_dist
                            if dist_end_mid > 1e-6 and dist_E_TM > 1e-6:
                                intended_start_p2 = intended_end_p2 + vec_E_TM * (original_length / dist_end_mid)
                            else: # Degenerate case, mid is at end
                                angle = math.atan2(vec_p1.y(), vec_p1.x()) # Original angle
                                intended_start_p2 = intended_end_p2 - QPointF(original_length * math.cos(angle), original_length * math.sin(angle))
                         else:
                            # Non-fixed length - cannot pivot start. Prioritize fixed end.
                            pass # Do not apply mid-point correction in this case
                    else:
                        # Case 1: Neither end fixed by endpoints. Translate rod.
                        translation = target_mid - mid_phase1
                        intended_start_p2 = current_start + translation
                        intended_end_p2 = current_end + translation

                    # Store the adjusted positions from phase 2
                    phase2_intended_positions[rod_id] = (intended_start_p2, intended_end_p2)

            # --- Update intended positions for next pass and calculate max correction --- 
            max_correction_this_pass_sq = 0.0 # Recalculate based on final phase 2 results
            for rod_id in intended_rod_positions:
                prev_start, prev_end = intended_rod_positions[rod_id]
                final_start, final_end = phase2_intended_positions[rod_id]
                correction_sq = max(QPointF.dotProduct(final_start - prev_start, final_start - prev_start),
                                     QPointF.dotProduct(final_end - prev_end, final_end - prev_end))
                max_correction_this_pass_sq = max(max_correction_this_pass_sq, correction_sq)

            intended_rod_positions = phase2_intended_positions # Update for next pass

            if DEBUG_CONSTRAINTS and pass_num < 5: print(f"  Pass {pass_num + 1} Max Correction Sq (End of Pass): {max_correction_this_pass_sq:.6f}")

            if max_correction_this_pass_sq < max_correction_threshold_sq:
                if DEBUG_CONSTRAINTS: print(f"\\n  -> Converged after {pass_num + 1} passes.")
                break
        else:
            if DEBUG_CONSTRAINTS: print(f"\\n  -> Reached max {num_passes} passes.")

        # Apply final positions
        if DEBUG_CONSTRAINTS: print("  -> Applying final positions...")
        for rod in self.rods:
            if rod.id in intended_rod_positions: # Check if rod was processed
                final_start, final_end = intended_rod_positions[rod.id]
                rod.start_pos = final_start
                rod.end_pos = final_end
            # else: Rod might not have been in the initial dictionary if list changed during propagation? (Shouldn't happen here)

        self.update()
        if DEBUG_CONSTRAINTS:
            print("--- Propagation Finished ---")

    # --- Simulation Control Methods ---
    def start_simulation(self):
        if not self.simulation_running:
            # self.pen_path_points.clear() # Path now generated offline
            self.current_simulation_angle_deg = 0.0 
            
            # Set reference frame (still useful for potential future viz)
            if self.canvas_wheel:
                self.reference_wheel_id = self.canvas_wheel.id
                # print(f"Simulation started. Reference Frame: Canvas Wheel {self.reference_wheel_id}")
            else:
                # ... (fallback logic) ...
                pass
            
            # interval_ms = int(self.simulation_time_step * 1000)
            # self.simulation_timer.start(interval_ms) # <<< DISABLE old timer
            self.simulation_running = True # Keep flag for potential viz state
            print("Simulation state set to RUNNING (timer disabled, path generation offline).")
            self.update() # Update button states potentially
            
    def stop_simulation(self):
        if self.simulation_running:
            # self.simulation_timer.stop() # <<< DISABLE old timer
            self.simulation_running = False
            self.reference_wheel_id = None 
            print("Simulation state set to STOPPED.")
            self.update() # Update button states potentially

    def _update_simulation(self):
        # This method is now effectively disabled as the timer doesn't run
        # We can leave it or comment it out fully.
        pass
        # """Core simulation update loop called by the timer."""
        # if not self.simulation_running: return
        # ... (old logic) ...

    def generate_image(self, filename: str, width_px: int, height_px: int, 
                       line_color: str = "black", line_width: int = 1, 
                       path_points: Optional[List[QPointF]] = None):
        """Generates a PNG image of the calculated pen path.
        
        Args:
            filename (str): Path to save the PNG file.
            width_px (int): Width of the output image in pixels.
            height_px (int): Height of the output image in pixels.
            line_color (str): Color of the path lines (e.g., '#FF0000', 'blue').
            line_width (int): Width of the path lines in pixels.
            path_points (Optional[List[QPointF]]): The list of path points to draw.
                                                   If None, uses self.pen_path_points (for backwards compatibility or testing).
                                                   Assumed to be relative to the canvas center if transformed, or absolute otherwise.
        """
        
        points_to_draw = path_points if path_points is not None else self.pen_path_points
        
        if not points_to_draw:
            print("generate_image: No path points to draw.")
            return False

        try:
            # Create a new blank image with white background
            img = Image.new('RGB', (width_px, height_px), color = 'white')
            draw = ImageDraw.Draw(img)

            # --- Calculate bounding box and transform for the points_to_draw --- 
            if not points_to_draw: # Should be caught above, but double check
                return False
                
            # Find min/max coordinates IN THE PROVIDED LIST (relative or absolute)
            min_x = min(p.x() for p in points_to_draw)
            max_x = max(p.x() for p in points_to_draw)
            min_y = min(p.y() for p in points_to_draw)
            max_y = max(p.y() for p in points_to_draw)
            
            path_width = max_x - min_x
            path_height = max_y - min_y
            
            # Handle zero size path (single point)
            if path_width == 0 and path_height == 0:
                center_x_img = width_px / 2
                center_y_img = height_px / 2
                draw.ellipse((center_x_img-2, center_y_img-2, center_x_img+2, center_y_img+2), fill=line_color)
                img.save(filename)
                return True
            elif path_width == 0: path_width = 1 # Avoid division by zero
            elif path_height == 0: path_height = 1
                
            # Determine scale factor to fit path within image (with padding)
            padding_factor = 0.9 # Use 90% of the image dimension
            scale_x = (width_px * padding_factor) / path_width
            scale_y = (height_px * padding_factor) / path_height
            scale_factor = min(scale_x, scale_y)
            
            # Calculate offset to center the scaled path in the image
            # Center of the path data (using its own min/max)
            center_x_data = (min_x + max_x) / 2.0
            center_y_data = (min_y + max_y) / 2.0
            # Target center in the image
            center_x_img = width_px / 2.0
            center_y_img = height_px / 2.0
            
            # Offset = ImageCenter - ScaledDataCenter
            offset_x = center_x_img - (center_x_data * scale_factor)
            offset_y = center_y_img - (center_y_data * scale_factor)
            # --- End BBox and Transform Calc --- 

            # --- Define Transform Function (closure) --- 
            # This function now transforms the points from the input list's coordinate system
            # (relative or absolute, depending on what was passed) to image pixel coordinates.
            def transform(point: QPointF) -> Tuple[int, int]:
                img_x = int((point.x() * scale_factor) + offset_x)
                img_y = int((point.y() * scale_factor) + offset_y)
                return img_x, img_y
            # --- End Transform Function --- 

            # Draw the path segments
            if len(points_to_draw) > 1:
                transformed_points = [transform(p) for p in points_to_draw]
                draw.line(transformed_points, fill=line_color, width=line_width, joint="curve")
                
            # Save the image
            img.save(filename)
            return True

        except Exception as e:
            print(f"Error generating image file {filename}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def add_canvas_wheel(self, center: QPointF = QPointF(0,0), diameter: float = 500.0):
        """Adds a special wheel representing the canvas. Only one allowed."""
        if self.canvas_wheel is not None:
            print("Canvas wheel already exists. Only one allowed.")
            # Optionally, could select the existing canvas wheel here
            return

        new_id = self._next_component_id
        self._next_component_id += 1
        
        # Create the canvas wheel, explicitly setting the flag
        canvas_wheel_obj = Wheel(
            id=new_id, 
            center=center, 
            diameter=diameter, 
            is_canvas=True # <-- ADDED: Explicitly set the flag
        )
        # Maybe add a default connection point at center? Or none?
        # canvas_wheel_obj.add_connection_point('center', 0.0) 
        
        # Assign and add to lists/dicts
        self.canvas_wheel = canvas_wheel_obj
        self.wheels.append(canvas_wheel_obj)
        self.components_by_id[new_id] = canvas_wheel_obj
        print(f"Added Canvas Wheel (ID: {new_id})")
        self.update() 
        # return canvas_wheel_obj # Return if needed elsewhere