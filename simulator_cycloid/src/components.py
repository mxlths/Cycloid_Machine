from dataclasses import dataclass, field
from typing import List, Optional, Union, Tuple, Dict
from PyQt6.QtCore import QPointF
import math
import uuid

@dataclass
class ConnectionPoint:
    radius: float  # Distance from wheel center
    id: str        # Identifier for this connection point (e.g., "p1", "main")
    # Optional: Add phase angle if needed for initial positioning or rotation
    # initial_phase_deg: float = 0.0 

@dataclass
class RodConnection:
    component: Union['Wheel', 'Rod']  # The connected component
    point_id: str                     # ID of connection point on the component
    distance_from_start: float = 0    # Distance from rod start (for mid-point connections)

@dataclass
class Rod:
    length: float
    start_pos: QPointF  # Current position of start point
    end_pos: QPointF    # Current position of end point
    id: int # ID is now assigned externally
    # Connections FROM this rod's points TO other components
    start_connection: Optional[Tuple[int, str]] = None # (connected_comp_id, point_id_on_comp)
    end_connection: Optional[Tuple[int, str]] = None   # (connected_comp_id, point_id_on_comp)
    mid_point_distance: Optional[float] = None         # Distance from start for the mid connection point
    mid_point_connection: Optional[Tuple[int, str]] = None # What the mid point connects TO (comp_id, point_id_on_comp)

    # Pen position on this rod
    pen_distance_from_start: Optional[float] = None

    selected: bool = False
    # Connections TO this rod FROM other components (keep for future use?)
    # connections: List[RodConnection] = field(default_factory=list)
    
    def contains_point(self, point: QPointF, tolerance: float = 5.0) -> bool:
        """Check if a point is near the rod's line"""
        # Calculate perpendicular distance from point to line segment
        x1, y1 = self.start_pos.x(), self.start_pos.y()
        x2, y2 = self.end_pos.x(), self.end_pos.y()
        x0, y0 = point.x(), point.y()
        
        # Length of the line segment squared
        l2 = (x2 - x1)**2 + (y2 - y1)**2
        
        if l2 == 0:
            # Line segment is actually a point
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2) <= tolerance
            
        # Consider the line extending the segment, parameterized as start + t (end - start)
        # Project point onto the line: t = [(point-start) . (end-start)] / |end-start|^2
        t = ((x0 - x1) * (x2 - x1) + (y0 - y1) * (y2 - y1)) / l2
        
        if t < 0:
            # Point is beyond the start of the segment
            return math.sqrt((x0 - x1)**2 + (y0 - y1)**2) <= tolerance
        elif t > 1:
            # Point is beyond the end of the segment
            return math.sqrt((x0 - x2)**2 + (y0 - y2)**2) <= tolerance
            
        # Projection falls on the segment
        projection_x = x1 + t * (x2 - x1)
        projection_y = y1 + t * (y2 - y1)
        
        return math.sqrt((x0 - projection_x)**2 + (y0 - projection_y)**2) <= tolerance
        
    def get_point_at_distance(self, distance: float) -> QPointF:
        """Get position at specified distance from start"""
        ratio = distance / self.length
        x = self.start_pos.x() + (self.end_pos.x() - self.start_pos.x()) * ratio
        y = self.start_pos.y() + (self.end_pos.y() - self.start_pos.y()) * ratio
        return QPointF(x, y)
        
    def move_start_to(self, new_pos: QPointF):
        """Move the start point, allowing length to change. Keep end_pos fixed."""
        self.start_pos = new_pos
        # Update length
        dx = self.end_pos.x() - self.start_pos.x()
        dy = self.end_pos.y() - self.start_pos.y()
        self.length = math.sqrt(dx * dx + dy * dy)
        
    def move_end_to(self, new_pos: QPointF):
        """Move the end point, allowing length to change. Keep start_pos fixed."""
        self.end_pos = new_pos
        # Update length
        dx = self.end_pos.x() - self.start_pos.x()
        dy = self.end_pos.y() - self.start_pos.y()
        self.length = math.sqrt(dx * dx + dy * dy)

@dataclass
class Wheel:
    center: QPointF
    diameter: float
    id: int # ID is now assigned externally
    speed_ratio: float = 1.0 # TODO: Consider replacing this with rotation_rate
    rotation_rate: float = 0.0 # Degrees per simulation time step
    # Store multiple named connection points
    connection_points: Dict[str, ConnectionPoint] = field(default_factory=dict)
    current_angle_deg: float = 0.0 # Track the wheel's rotation
    selected: bool = False
    
    # --- Connection Point Calculation ---
    def get_connection_point_position(self, point_id: str) -> Optional[QPointF]:
        """Get the absolute position of a specific connection point, considering wheel rotation."""
        if point_id not in self.connection_points:
            return None
            
        cp = self.connection_points[point_id]
        radius = cp.radius
        
        if radius < 0:
            return None # Radius cannot be negative
            
        # Assume 0 degrees rotation corresponds to the point being directly East (positive X)
        # Add the wheel's current rotation angle
        effective_angle_deg = self.current_angle_deg # For now, assume cp phase is 0
        math_angle_rad = math.radians(effective_angle_deg)
        
        # Calculate offset from center
        # Standard math coordinates (X right, Y up)
        offset_x = radius * math.cos(math_angle_rad)
        offset_y = radius * math.sin(math_angle_rad) 
        
        # Adjust for QPointF coordinate system (Y down) if necessary
        # If QPointF has Y increasing downwards, use: offset_y = -radius * math.sin(math_angle_rad)
        # Assuming standard graphics coords for now (Y up)
        
        return QPointF(self.center.x() + offset_x, self.center.y() + offset_y)

    # --- Add/Remove Connection Points ---
    def add_connection_point(self, point_id: str, radius: float):
        if radius >= 0:
            self.connection_points[point_id] = ConnectionPoint(radius=radius, id=point_id)

    def remove_connection_point(self, point_id: str):
        if point_id in self.connection_points:
            del self.connection_points[point_id]

    # --- Previous Methods (keep if needed, remove connection point list related) ---
    # ... (remove or comment out old single connection point logic if present) ...
    
    def contains_point(self, point: QPointF, tolerance: float = 5.0) -> bool:
        """Check if a point is within the wheel's area (with tolerance)"""
        dx = point.x() - self.center.x()
        dy = point.y() - self.center.y()
        distance = (dx * dx + dy * dy) ** 0.5
        return distance <= (self.diameter / 2 + tolerance)
    
    def move_to(self, new_center: QPointF):
        """Move the wheel to a new center position"""
        self.center = new_center
    
    # def get_connection_point_position(self, point_id: str) -> Optional[QPointF]:
    #     """Get the absolute position of a connection point"""
    #     for cp in self.connection_points:
    #         if cp.id == point_id:
    #             # For now, just return point at 0 degrees - we'll add rotation later
    #             return QPointF(self.center.x() + cp.radius, self.center.y())
    #     return None 