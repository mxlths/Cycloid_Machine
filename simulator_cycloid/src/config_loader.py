import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from PyQt6.QtCore import QPointF
import re
import os

# Import component classes (adjust path if necessary)
from components import Wheel, Rod, ConnectionPoint
from drawing_canvas import DrawingCanvas

# Define dataclasses to hold the parsed configuration (optional, but good practice)
@dataclass
class SpeedControlConfig:
    base_ratio: float = 1.0
    modulation_type: str = 'none'
    frequency: float = 0.0
    amplitude: float = 0.0
    phase: float = 0.0

@dataclass
class CanvasConfig:
    center: QPointF
    diameter: float
    drawing_area_width: float
    drawing_area_height: float
    speed_control: SpeedControlConfig

@dataclass
class WheelConfig:
    id: int
    center: QPointF
    diameter: float # Diameter will be needed for visualization, even if connection points define mechanics
    speed_control: SpeedControlConfig
    connection_points: Dict[str, ConnectionPoint]
    # Add compound wheels later if needed

@dataclass
class RodConnectionConfig:
    connected_to_wheel: Optional[int] = None # ID of the wheel
    connected_to_point: Optional[str] = None # ID of the point on the wheel
    connected_to_rod: Optional[int] = None   # ID of the rod
    connected_to_rod_end: Optional[str] = None # 'start', 'mid', or 'end'

@dataclass
class RodConfig:
    id: int
    length: float
    start_connection: RodConnectionConfig
    end_connection: Optional[RodConnectionConfig] = None
    mid_connection: Optional[RodConnectionConfig] = None
    mid_distance_from_start: Optional[float] = None
    pen_distance_from_start: Optional[float] = None


@dataclass
class MachineConfig:
    master_speed: float
    canvas: CanvasConfig
    drive_wheels: Dict[int, WheelConfig]
    rods: Dict[int, RodConfig]
    _source_xml: Optional[ET.Element] = None  # Store the original XML root


def _parse_speed_control(element: ET.Element) -> SpeedControlConfig:
    """Helper to parse speed control elements."""
    base_ratio = float(element.findtext('base_ratio', '1.0'))
    mod_element = element.find('modulation')
    if mod_element is not None:
        mod_type = mod_element.findtext('type', 'none')
        frequency = float(mod_element.findtext('frequency', '0.0'))
        amplitude = float(mod_element.findtext('amplitude', '0.0'))
        phase = float(mod_element.findtext('phase', '0.0'))
        return SpeedControlConfig(base_ratio, mod_type, frequency, amplitude, phase)
    else:
        return SpeedControlConfig(base_ratio=base_ratio)

def _parse_connection_points(element: ET.Element) -> Dict[str, ConnectionPoint]:
    """Helper to parse connection points for a wheel."""
    points = {}
    cp_elements = element.find('connection_points')
    if cp_elements:
        for point_elem in cp_elements.findall('point'):
            point_id = point_elem.get('id')
            radius = float(point_elem.get('radius', '0.0'))
            if point_id:
                points[point_id] = ConnectionPoint(id=point_id, radius=radius)
    return points

def _parse_connection_target(target_string: str) -> RodConnectionConfig:
    """Parses a 'connected_to' string into a RodConnectionConfig."""
    config = RodConnectionConfig()
    
    # Regex to match "wheel_{id}_point_{point_id}"
    wheel_match = re.fullmatch(r"wheel_(\d+)_point_(.+)", target_string)
    if wheel_match:
        config.connected_to_wheel = int(wheel_match.group(1))
        config.connected_to_point = wheel_match.group(2)
        return config

    # Regex to match "rod_{id}_{start|mid|end}"
    rod_match = re.fullmatch(r"rod_(\d+)_(start|mid|end)", target_string)
    if rod_match:
        config.connected_to_rod = int(rod_match.group(1))
        config.connected_to_rod_end = rod_match.group(2)
        return config

    print(f"Warning: Could not parse connection target string: {target_string}")
    return config # Return empty config if no match

# --- Main Loading Function ---

def load_config_from_xml(file_path: str) -> MachineConfig:
    """Loads machine configuration from an XML file."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        raise
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {file_path}")
        raise

    # --- Global Settings ---
    global_settings = root.find('global_settings')
    master_speed = float(global_settings.findtext('master_speed', '1.0')) if global_settings else 1.0

    # --- Canvas ---
    canvas_elem = root.find('canvas')
    if canvas_elem is None:
        raise ValueError("Configuration missing <canvas> element.")
    
    canvas_center_elem = canvas_elem.find('center_position')
    canvas_center = QPointF(float(canvas_center_elem.get('x','0')), float(canvas_center_elem.get('y','0'))) if canvas_center_elem is not None else QPointF(0,0)
    canvas_diameter = float(canvas_elem.findtext('diameter', '100'))
    
    drawing_area_elem = canvas_elem.find('drawing_area')
    drawing_width = float(drawing_area_elem.findtext('width', '200')) if drawing_area_elem is not None else 200
    drawing_height = float(drawing_area_elem.findtext('height', '200')) if drawing_area_elem is not None else 200
    
    canvas_speed_elem = canvas_elem.find('speed_control')
    canvas_speed_config = _parse_speed_control(canvas_speed_elem) if canvas_speed_elem is not None else SpeedControlConfig()
    
    canvas_config = CanvasConfig(
        center=canvas_center, 
        diameter=canvas_diameter, 
        drawing_area_width=drawing_width,
        drawing_area_height=drawing_height,
        speed_control=canvas_speed_config
    )

    # --- Drive Wheels ---
    drive_wheels_elem = root.find('drive_wheels')
    drive_wheels_config: Dict[int, WheelConfig] = {}
    if drive_wheels_elem is not None:
        for wheel_elem in drive_wheels_elem.findall('wheel'):
            wheel_id_str = wheel_elem.get('id')
            if not wheel_id_str or not wheel_id_str.isdigit():
                print(f"Warning: Skipping wheel with invalid or missing id: {wheel_id_str}")
                continue
            wheel_id = int(wheel_id_str)

            center_elem = wheel_elem.find('center_position')
            center = QPointF(float(center_elem.get('x','0')), float(center_elem.get('y','0'))) if center_elem is not None else QPointF(0,0)
            
            # Infer diameter from max connection point radius? Or require diameter tag?
            # For now, let's assume a default or look for a tag (adding diameter tag for clarity)
            diameter = float(wheel_elem.findtext('diameter', '50')) # Added diameter tag

            speed_elem = wheel_elem.find('speed_control')
            speed_config = _parse_speed_control(speed_elem) if speed_elem is not None else SpeedControlConfig()

            connection_points = _parse_connection_points(wheel_elem)
            
            # TODO: Parse compound wheels

            drive_wheels_config[wheel_id] = WheelConfig(
                id=wheel_id,
                center=center,
                diameter=diameter, 
                speed_control=speed_config,
                connection_points=connection_points
            )

    # --- Linkages (Rods) ---
    linkages_elem = root.find('linkages')
    rods_config: Dict[int, RodConfig] = {}
    if linkages_elem is not None:
        for rod_elem in linkages_elem.findall('rod'):
            rod_id_str = rod_elem.get('id')
            if not rod_id_str or not rod_id_str.isdigit():
                 print(f"Warning: Skipping rod with invalid or missing id: {rod_id_str}")
                 continue
            rod_id = int(rod_id_str)
            
            length = float(rod_elem.findtext('length', '100'))
            pen_pos_elem = rod_elem.find('pen_position')
            pen_distance = float(pen_pos_elem.get('distance_from_start')) if pen_pos_elem is not None and pen_pos_elem.get('distance_from_start') is not None else None

            connections_elem = rod_elem.find('connections')
            start_conn_conf = RodConnectionConfig() # Default empty
            end_conn_conf: Optional[RodConnectionConfig] = None
            mid_conn_conf: Optional[RodConnectionConfig] = None
            mid_dist: Optional[float] = None

            if connections_elem:
                start_point_elem = connections_elem.find('start_point')
                if start_point_elem is not None:
                     target_str = start_point_elem.get('connected_to')
                     if target_str:
                         start_conn_conf = _parse_connection_target(target_str)
                     else:
                         print(f"Warning: Rod {rod_id} start_point missing 'connected_to' attribute.")
                     
                mid_point_elem = connections_elem.find('mid_point')
                if mid_point_elem is not None:
                    target_str = mid_point_elem.get('connected_to')
                    dist_str = mid_point_elem.get('distance_from_start')
                    
                    # Process the connection target if present
                    if target_str:
                         mid_conn_conf = _parse_connection_target(target_str)
                    # We don't warn if there's no connected_to attribute, as mid-points can exist without connections
                    
                    # Process the distance
                    if dist_str:
                        try:
                            mid_dist = float(dist_str)
                        except ValueError:
                            print(f"Warning: Rod {rod_id} mid_point has invalid 'distance_from_start': {dist_str}")
                    else:
                        print(f"Warning: Rod {rod_id} mid_point missing 'distance_from_start' attribute.")
                    
                end_point_elem = connections_elem.find('end_point')
                if end_point_elem is not None:
                    target_str = end_point_elem.get('connected_to')
                    if target_str:
                        end_conn_conf = _parse_connection_target(target_str)
                    else:
                        print(f"Warning: Rod {rod_id} end_point missing 'connected_to' attribute.")
            else:
                 print(f"Warning: Rod {rod_id} is missing the <connections> element.")

            # Ensure start connection is always present, even if empty
            if start_conn_conf is None: 
                 print(f"Error: Rod {rod_id} must have a <start_point> connection.")
                 continue # Skip this rod if start point is fundamentally missing

            rods_config[rod_id] = RodConfig(
                id=rod_id,
                length=length,
                start_connection=start_conn_conf, 
                end_connection=end_conn_conf,    
                mid_connection=mid_conn_conf,    
                mid_distance_from_start=mid_dist, 
                pen_distance_from_start=pen_distance
            )


    # --- Construct Final Config ---
    config = MachineConfig(
        master_speed=master_speed,
        canvas=canvas_config,
        drive_wheels=drive_wheels_config,
        rods=rods_config # Add parsed rods
    )
    
    # Store the original XML for additional data access
    config._source_xml = root

    return config

# Example Usage (optional, for testing)
if __name__ == '__main__':
    # Create a dummy XML file for testing
    dummy_xml = """
    <machine_configuration>
        <global_settings>
            <master_speed>1.0</master_speed>
        </global_settings>
        <canvas>
            <center_position x="300" y="300"/>
            <diameter>500</diameter>
            <drawing_area> <width>600</width> <height>600</height> </drawing_area>
            <speed_control> <base_ratio>0.1</base_ratio> </speed_control>
        </canvas>
        <drive_wheels>
            <wheel id="1">
                <center_position x="100" y="100"/>
                <diameter>80</diameter>
                <speed_control> 
                    <base_ratio>1.0</base_ratio> 
                    <modulation>
                        <type>sine</type> <frequency>0.2</frequency> <amplitude>0.5</amplitude> <phase>0.0</phase>
                    </modulation>
                </speed_control>
                <connection_points> <point id="p1" radius="30"/> </connection_points>
            </wheel>
            <wheel id="2">
                <center_position x="500" y="100"/>
                <diameter>60</diameter>
                 <speed_control> <base_ratio>-0.5</base_ratio> </speed_control>
                <connection_points> <point id="p1" radius="20"/> </connection_points>
            </wheel>
        </drive_wheels>
        <linkages>
             <rod id="10">
                 <length>150</length>
                 <connections>
                    <start_point connected_to="wheel_1_point_p1"/>
                    <end_point connected_to="rod_11_start"/> 
                 </connections>
                 <pen_position distance_from_start="75"/>
             </rod>
             <rod id="11">
                 <length>120</length>
                 <connections>
                     <start_point connected_to="rod_10_end"/>
                     <end_point connected_to="wheel_2_point_p1"/>
                 </connections>
             </rod>
        </linkages>
    </machine_configuration>
    """
    with open("dummy_config.xml", "w") as f:
        f.write(dummy_xml)

    try:
        loaded_config = load_config_from_xml("dummy_config.xml")
        print("Configuration loaded successfully:")
        # Pretty print or inspect parts of the config
        import pprint 
        pprint.pprint(loaded_config)
    except Exception as e:
        print(f"Error loading config: {e}")
        raise # Re-raise after printing

    # Clean up dummy file
    os.remove("dummy_config.xml")

# --- Function to Populate Canvas from Config --- 

# Moved from main.py
from drawing_canvas import DrawingCanvas # Need canvas class
from components import Wheel, Rod        # Need component classes
from typing import Dict                  # Need Dict type hint
from PyQt6.QtCore import QPointF         # Need QPointF
import math                            # Need math for rod calcs

def populate_canvas_from_config(canvas: DrawingCanvas, config: MachineConfig):
    """Clears the canvas and populates it with components from a MachineConfig."""
    # Clear existing components
    canvas.wheels.clear()
    canvas.rods.clear()
    canvas.components_by_id.clear()
    canvas.pen_path_points.clear()
    canvas._next_component_id = 1 # Reset ID counter
    max_id = 0

    # Create Wheels
    for wheel_id, wheel_config in config.drive_wheels.items():
        new_wheel = Wheel(
            id=wheel_id,
            center=wheel_config.center, 
            diameter=wheel_config.diameter,
            speed_ratio=wheel_config.speed_control.base_ratio, # Ignoring modulation for now
            # Add connection points directly from config
            connection_points=wheel_config.connection_points.copy() 
        )
        canvas.wheels.append(new_wheel)
        canvas.components_by_id[wheel_id] = new_wheel
        max_id = max(max_id, wheel_id)
        print(f"Created Wheel {wheel_id}")

    # Create Rods (initial positions are placeholders, connections set below)
    for rod_id, rod_config in config.rods.items():
        # Try to read position from the XML source itself for backward compatibility
        # This is needed because our dataclasses don't store the actual positions
        rod_elem = None
        if hasattr(config, '_source_xml') and config._source_xml is not None:
            linkages = config._source_xml.find('linkages')
            if linkages is not None:
                for r in linkages.findall('rod'):
                    if r.get('id') == str(rod_id):
                        rod_elem = r
                        break

        # Default placeholder positions
        start_x, start_y = 0, 0
        end_x, end_y = rod_config.length, 0
        
        # Try to get actual positions from XML if available
        if rod_elem is not None:
            # Get start position if available
            start_pos_elem = rod_elem.find('start_position')
            if start_pos_elem is not None:
                start_x = float(start_pos_elem.get('x', 0))
                start_y = float(start_pos_elem.get('y', 0))
                
            # Get end position if available
            end_pos_elem = rod_elem.find('end_position')
            if end_pos_elem is not None:
                end_x = float(end_pos_elem.get('x', rod_config.length))
                end_y = float(end_pos_elem.get('y', 0))

        # Create the rod with the positions we've determined
        new_rod = Rod(
            id=rod_id,
            length=rod_config.length,
            start_pos=QPointF(start_x, start_y),
            end_pos=QPointF(end_x, end_y),
            pen_distance_from_start=rod_config.pen_distance_from_start,
            mid_point_distance=rod_config.mid_distance_from_start
            # Connections will be set below
        )
        
        # Set the connection targets (Tuples: (component_id, point_id))
        if rod_config.start_connection:
            conn = rod_config.start_connection
            if conn.connected_to_wheel is not None and conn.connected_to_point is not None:
                new_rod.start_connection = (conn.connected_to_wheel, conn.connected_to_point)
            elif conn.connected_to_rod is not None and conn.connected_to_rod_end is not None:
                new_rod.start_connection = (conn.connected_to_rod, conn.connected_to_rod_end)
                
        if rod_config.end_connection:
            conn = rod_config.end_connection
            if conn.connected_to_wheel is not None and conn.connected_to_point is not None:
                new_rod.end_connection = (conn.connected_to_wheel, conn.connected_to_point)
            elif conn.connected_to_rod is not None and conn.connected_to_rod_end is not None:
                new_rod.end_connection = (conn.connected_to_rod, conn.connected_to_rod_end)
                
        if rod_config.mid_connection:
            conn = rod_config.mid_connection
            if conn.connected_to_wheel is not None and conn.connected_to_point is not None:
                new_rod.mid_point_connection = (conn.connected_to_wheel, conn.connected_to_point)
            elif conn.connected_to_rod is not None and conn.connected_to_rod_end is not None:
                new_rod.mid_point_connection = (conn.connected_to_rod, conn.connected_to_rod_end)

        canvas.rods.append(new_rod)
        canvas.components_by_id[rod_id] = new_rod
        max_id = max(max_id, rod_id)
        print(f"Created Rod {rod_id} with connections: S={new_rod.start_connection}, E={new_rod.end_connection}, M={new_rod.mid_point_connection}")

    # Set the next ID based on the highest loaded ID
    canvas._next_component_id = max_id + 1
    
    # Update component lookup (essential before constraint propagation)
    canvas._update_component_lookup()
    
    # Propagate constraints to settle initial positions based on connections
    print("Running initial constraint propagation...")
    # Need to handle potential missing _propagate_constraints if DrawingCanvas not fully imported
    if hasattr(canvas, '_propagate_constraints'):
        canvas._propagate_constraints()
        print("Constraint propagation finished.")
    else:
        print("Warning: canvas._propagate_constraints not found.")

    # Trigger repaint
    canvas.update()
    
    print("Canvas population complete.") 