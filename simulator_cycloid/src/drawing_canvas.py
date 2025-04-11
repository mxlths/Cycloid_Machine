from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFocusEvent
from components import Wheel, Rod, ConnectionPoint
import math
from typing import Optional, Union, List, Tuple

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
        
        # Draw connection point if defined
        conn_pos = wheel.get_connection_point_position()
        if conn_pos:
            screen_conn_pos = self._canvas_to_screen(conn_pos)
            painter.setPen(QPen(Qt.GlobalColor.red, 2))
            painter.setBrush(QBrush(Qt.GlobalColor.red))
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
        
        # Draw connection points
        painter.setPen(QPen(Qt.GlobalColor.red, 2))
        painter.setBrush(QBrush(Qt.GlobalColor.red))
        for conn in rod.connections:
            if isinstance(conn.distance_from_start, (int, float)):
                pos = rod.get_point_at_distance(conn.distance_from_start)
                screen_pos = self._canvas_to_screen(pos)
                painter.drawEllipse(screen_pos, 6, 6)
        
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
        self.wheels.append(wheel)
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
            pos = wheel.get_connection_point_position()
            if pos:
                dist_sq = (canvas_point.x() - pos.x())**2 + (canvas_point.y() - pos.y())**2
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    # Return component ID, the standard point ID, and position
                    nearest = ('wheel', wheel.id, wheel.CONNECTION_POINT_ID, pos) 
        
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
        # for rod in self.rods:
        #     for conn in rod.connections:
        #         if isinstance(conn.distance_from_start, (int, float)):
        #             pos = rod.get_point_at_distance(conn.distance_from_start)
        #             dist_sq = (canvas_point.x() - pos.x())**2 + (canvas_point.y() - pos.y())**2
        #             if dist_sq < min_dist_sq:
        #                 min_dist_sq = dist_sq
        #                 # TODO: Define how to identify these points (e.g., index?)
        #                 # nearest = ('rod', rod, conn.distance_from_start, pos)
        
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
                self.selected_component.move_to(target_point)
            elif isinstance(self.selected_component, Rod):
                # Disconnect endpoint if moving a connected one
                if self.dragging_point == 'start' and self.selected_component.start_connection:
                    print(f"Rod {self.selected_component.id} start disconnected by dragging.")
                    self.selected_component.start_connection = None
                elif self.dragging_point == 'end' and self.selected_component.end_connection:
                    print(f"Rod {self.selected_component.id} end disconnected by dragging.")
                    self.selected_component.end_connection = None
                    
                # Move the specific endpoint
                if self.dragging_point == 'start':
                    self.selected_component.move_start_to(target_point)
                elif self.dragging_point == 'end':
                    self.selected_component.move_end_to(target_point)
            
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

        # TODO: Handle breaking connections when deleting components

        if isinstance(component_to_delete, Wheel):
            self.wheels.remove(component_to_delete)
            print(f"Deleted Wheel {component_id}")
        elif isinstance(component_to_delete, Rod):
            self.rods.remove(component_to_delete)
            print(f"Deleted Rod {component_id}")

        # Clear selection state
        self.selected_component = None
        self.dragging = False
        self.dragging_point = None
        self.component_selected.emit(None) # Notify panel to clear
        self.update() 