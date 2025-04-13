import xml.etree.ElementTree as ET
from xml.dom import minidom
from PyQt6.QtCore import QPointF
from typing import List, Tuple, Optional

# Assuming components module is in the same directory or accessible
from components import Wheel, Rod

# Helper to format connection tuples back to strings
def _format_connection_target(connection: Optional[Tuple[int, str]], components_dict) -> Optional[str]:
    if connection is None:
        return None
        
    comp_id, point_id = connection
    
    if comp_id not in components_dict:
        print(f"Warning: Cannot format connection for missing component ID: {comp_id}")
        return None # Or raise error
        
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
             return None
    else:
        print(f"Warning: Unknown component type for connection: {type(component)}")
        return None

# Helper to add sub-elements with text
def _add_sub_element(parent: ET.Element, tag: str, text: Optional[str] = None, attrib: Optional[dict] = None) -> ET.Element:
    element = ET.SubElement(parent, tag, attrib if attrib else {})
    if text is not None:
        element.text = str(text)
    return element

def generate_xml_tree(wheels: List[Wheel], rods: List[Rod], components_dict) -> ET.ElementTree:
    """Generates an XML ElementTree from the current canvas components."""
    root = ET.Element('machine_configuration')

    # --- Global Settings (Defaults for now) ---
    global_settings = _add_sub_element(root, 'global_settings')
    _add_sub_element(global_settings, 'master_speed', '1.0')

    # --- Canvas (Defaults for now) ---
    canvas = _add_sub_element(root, 'canvas')
    _add_sub_element(canvas, 'center_position', attrib={'x': '400', 'y': '300'})
    _add_sub_element(canvas, 'diameter', '600')
    drawing_area = _add_sub_element(canvas, 'drawing_area')
    _add_sub_element(drawing_area, 'width', '800')
    _add_sub_element(drawing_area, 'height', '600')
    speed_control_canvas = _add_sub_element(canvas, 'speed_control')
    _add_sub_element(speed_control_canvas, 'base_ratio', '0.0')
    # Add default modulation if needed
    # modulation_canvas = _add_sub_element(speed_control_canvas, 'modulation')
    # _add_sub_element(modulation_canvas, 'type', 'none')

    # --- Drive Wheels ---
    drive_wheels = _add_sub_element(root, 'drive_wheels')
    for wheel in wheels:
        # Add is_canvas attribute to the wheel element
        wheel_attrs = {'id': str(wheel.id), 'is_canvas': str(wheel.is_canvas).lower()}
        wheel_elem = _add_sub_element(drive_wheels, 'wheel', attrib=wheel_attrs)
        
        _add_sub_element(wheel_elem, 'center_position', attrib={'x': str(wheel.center.x()), 'y': str(wheel.center.y())})
        _add_sub_element(wheel_elem, 'diameter', str(wheel.diameter))
        
        speed_control_wheel = _add_sub_element(wheel_elem, 'speed_control')
        _add_sub_element(speed_control_wheel, 'base_ratio', str(wheel.speed_ratio))
        _add_sub_element(speed_control_wheel, 'rotation_rate', str(wheel.rotation_rate))
        # TODO: Add modulation saving if implemented
        
        if wheel.connection_points:
            connection_points_elem = _add_sub_element(wheel_elem, 'connection_points')
            for point_id, cp in wheel.connection_points.items():
                _add_sub_element(connection_points_elem, 'point', attrib={'id': point_id, 'radius': str(cp.radius)})
                
        # TODO: Add compound wheel saving if implemented

    # --- Linkages (Rods) ---
    if rods: # Only add linkages section if there are rods
        linkages = _add_sub_element(root, 'linkages')
        for rod in rods:
            rod_elem = _add_sub_element(linkages, 'rod', attrib={'id': str(rod.id)})
            _add_sub_element(rod_elem, 'length', str(rod.length))
            # Add fixed_length attribute
            rod_elem.set('fixed_length', str(rod.fixed_length).lower())
            
            # Save actual rod position coordinates
            start_pos_elem = _add_sub_element(rod_elem, 'start_position', attrib={
                'x': str(rod.start_pos.x()),
                'y': str(rod.start_pos.y())
            })
            
            end_pos_elem = _add_sub_element(rod_elem, 'end_position', attrib={
                'x': str(rod.end_pos.x()),
                'y': str(rod.end_pos.y())
            })
            
            connections_elem = _add_sub_element(rod_elem, 'connections')
            
            # Start Connection
            start_target_str = _format_connection_target(rod.start_connection, components_dict)
            if start_target_str:
                _add_sub_element(connections_elem, 'start_point', attrib={'connected_to': start_target_str})
            else:
                 print(f"Warning: Rod {rod.id} has no valid start connection to save.")
                 # Decide: skip rod, save without connection, or add default?
            
            # End Connection
            end_target_str = _format_connection_target(rod.end_connection, components_dict)
            if end_target_str:
                _add_sub_element(connections_elem, 'end_point', attrib={'connected_to': end_target_str})

            # Mid Connection (if exists)
            mid_target_str = _format_connection_target(rod.mid_point_connection, components_dict)
            if rod.mid_point_distance is not None:
                mid_attrs = {'distance_from_start': str(rod.mid_point_distance)}
                if mid_target_str:
                    mid_attrs['connected_to'] = mid_target_str
                _add_sub_element(connections_elem, 'mid_point', attrib=mid_attrs)
                
            # Pen Position
            if rod.pen_distance_from_start is not None:
                _add_sub_element(rod_elem, 'pen_position', attrib={'distance_from_start': str(rod.pen_distance_from_start)})

    # Create and return the ElementTree
    tree = ET.ElementTree(root)
    return tree

def prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")

# --- Example Usage (for testing) ---
if __name__ == '__main__':
    # Create dummy components for testing
    wheel1 = Wheel(id=1, center=QPointF(100,100), diameter=80, speed_ratio=1.0)
    wheel1.add_connection_point("p1", 30)
    wheel2 = Wheel(id=2, center=QPointF(300,100), diameter=60, speed_ratio=-0.5)
    wheel2.add_connection_point("p1", 20)
    
    rod1 = Rod(id=10, length=150, start_pos=QPointF(0,0), end_pos=QPointF(150,0)) # Positions don't matter for saving connections
    rod1.start_connection = (1, "p1") # Connect to wheel 1, point p1
    rod1.end_connection = (2, "p1")   # Connect to wheel 2, point p1
    rod1.pen_distance_from_start = 75
    
    all_wheels = [wheel1, wheel2]
    all_rods = [rod1]
    all_components = {1: wheel1, 2: wheel2, 10: rod1}
    
    # Generate the tree
    xml_tree = generate_xml_tree(all_wheels, all_rods, all_components)
    
    # Get the root element for prettify
    root_element = xml_tree.getroot()
    pretty_xml_string = prettify_xml(root_element)
    
    print("Generated XML:")
    print(pretty_xml_string)
    
    # Optionally save to a test file
    # with open("test_output.xml", "w") as f:
    #     f.write(pretty_xml_string) 