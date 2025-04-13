from sympy import symbols, sin, cos, lambdify, nsolve, Matrix, pi
from sympy.physics.mechanics import (
    dynamicsymbols,
    ReferenceFrame,
    Point,
    RigidBody,
    PinJoint,
    mechanics_printing, # For better visualization
)
import numpy as np
import math

# Import our component types (adjust path if needed)
from components import Wheel, Rod
from PyQt6.QtCore import QPointF
from typing import List, Tuple, Optional, Dict, Union
import sympy

mechanics_printing()

def calculate_path_sympy(
    wheels: List[Wheel],
    rods: List[Rod],
    canvas_wheel: Optional[Wheel],
    pen_rod_id: int,
    pen_distance_from_start: float,
    duration: float, # Simulation duration (e.g., in seconds)
    steps: int,      # Number of steps to calculate
    components_dict: Dict[int, Union[Wheel, Rod]]
) -> List[QPointF]:
    """Calculates the pen path using SymPy kinematics (Body/Joint approach)."""
    print("Starting SymPy path calculation (Body/Joint approach)...")
    path_points = []
    dt = duration / steps
    time_values = np.linspace(0, duration, steps)

    # ---------------------------------------------------
    # --- 1. Define Base Frame and Time ---------------
    # ---------------------------------------------------
    t = symbols('t') # Time
    N = ReferenceFrame('N') # Inertial Frame
    O = Point('O')      # Origin
    O.set_vel(N, 0)

    # ---------------------------------------------------
    # --- 2. Create Bodies and Points -----------------
    # ---------------------------------------------------
    print("  Creating SymPy Bodies and Points...")
    sympy_bodies: Dict[int, RigidBody] = {}
    sympy_points: Dict[Tuple[int, Optional[str]], Point] = {} # (compId, pointId|'origin'): Point
    sympy_frames: Dict[int, ReferenceFrame] = {} # Store frames if needed later
    known_ang_vels_sym: Dict[sympy.Expr, float] = {} # Map symbolic omega to numeric value
    known_angles_func: Dict[sympy.Expr, sympy.Expr] = {} # Map symbolic theta to function of time
    
    # Store the unknown generalized coordinates (rod angles)
    unknown_generalized_coords = [] 
    rod_angles_sym: Dict[int, sympy.Expr] = {}

    # --- Canvas Wheel Body (if exists) ---
    canvas_frame = N
    canvas_origin = O
    if canvas_wheel:
        # Define angular velocity and angle symbols
        theta_c = dynamicsymbols(f'theta_{canvas_wheel.id}')
        omega_c = dynamicsymbols(f'omega_{canvas_wheel.id}')
        omega_c_val = math.radians(canvas_wheel.rotation_rate) # rad/s
        known_ang_vels_sym[omega_c] = omega_c_val
        known_angles_func[theta_c] = omega_c_val * t
        
        # Define frame and orientation
        canvas_frame = ReferenceFrame(f'C_{canvas_wheel.id}')
        canvas_frame.orient_axis(N, N.z, theta_c)
        canvas_frame.set_ang_vel(N, omega_c * N.z)
        sympy_frames[canvas_wheel.id] = canvas_frame
        
        # Define origin point
        canvas_origin = O.locatenew(f'O_{canvas_wheel.id}', 
                                    canvas_wheel.center.x() * N.x + canvas_wheel.center.y() * N.y)
        canvas_origin.set_vel(N, 0) # Assume canvas center is fixed in world
        sympy_points[(canvas_wheel.id, 'origin')] = canvas_origin

        # Define Body
        # Mass/Inertia not needed for kinematics, can use Body or just Frame/Point
        # Using Body might be helpful for joint definitions later
        # body_c = Body(f'Body_{canvas_wheel.id}', masscenter=canvas_origin, frame=canvas_frame)
        # sympy_bodies[canvas_wheel.id] = body_c
        rigidbody_c = RigidBody(f'Body_{canvas_wheel.id}', masscenter=canvas_origin, frame=canvas_frame)
        sympy_bodies[canvas_wheel.id] = rigidbody_c # Still store in sympy_bodies for consistency
        
        # Define connection points on the canvas wheel body
        for cp_id, cp_data in canvas_wheel.connection_points.items():
            p_pos = cp_data.radius * canvas_frame.x # Position relative to origin in wheel frame
            p_sm = canvas_origin.locatenew(f'P_{canvas_wheel.id}_{cp_id}', p_pos)
            p_sm.v2pt_theory(canvas_origin, N, canvas_frame)
            sympy_points[(canvas_wheel.id, cp_id)] = p_sm
            
    # --- Driving Wheel Bodies ---
    for wheel in wheels:
        if wheel == canvas_wheel: continue

        theta_w = dynamicsymbols(f'theta_{wheel.id}')
        omega_w = dynamicsymbols(f'omega_{wheel.id}')
        omega_w_val = math.radians(wheel.rotation_rate) # rad/s relative to CANVAS frame
        known_ang_vels_sym[omega_w] = omega_w_val
        known_angles_func[theta_w] = omega_w_val * t
        
        # Define frame and orientation RELATIVE TO CANVAS frame
        wheel_frame = ReferenceFrame(f'W_{wheel.id}')
        wheel_frame.orient_axis(canvas_frame, canvas_frame.z, theta_w)
        wheel_frame.set_ang_vel(canvas_frame, omega_w * canvas_frame.z)
        sympy_frames[wheel.id] = wheel_frame
        
        # Define origin point RELATIVE TO CANVAS origin
        relative_pos = wheel.center - (canvas_wheel.center if canvas_wheel else QPointF(0,0))
        wheel_origin = canvas_origin.locatenew(f'O_{wheel.id}', 
                                            relative_pos.x() * canvas_frame.x + relative_pos.y() * canvas_frame.y)
        wheel_origin.v2pt_theory(canvas_origin, N, canvas_frame) # Velocity based on canvas frame motion
        sympy_points[(wheel.id, 'origin')] = wheel_origin

        # Define Body
        # body_w = Body(f'Body_{wheel.id}', masscenter=wheel_origin, frame=wheel_frame)
        # sympy_bodies[wheel.id] = body_w
        rigidbody_w = RigidBody(f'Body_{wheel.id}', masscenter=wheel_origin, frame=wheel_frame)
        sympy_bodies[wheel.id] = rigidbody_w
        
        # Define connection points on this wheel body
        for cp_id, cp_data in wheel.connection_points.items():
            p_pos = cp_data.radius * wheel_frame.x
            p_sm = wheel_origin.locatenew(f'P_{wheel.id}_{cp_id}', p_pos)
            p_sm.v2pt_theory(wheel_origin, N, wheel_frame)
            sympy_points[(wheel.id, cp_id)] = p_sm
            
    # --- Rod Bodies and Points (Refined v2) --- 
    pen_point_sm = None # Initialize pen point
    sympy_rod_start_unk_coords: Dict[int, Tuple[sympy.Expr, sympy.Expr]] = {}
    for rod in rods:
        # Define unknown angle for the rod relative to the world N.x
        phi_r = dynamicsymbols(f'phi_{rod.id}')
        rod_angles_sym[rod.id] = phi_r
        unknown_generalized_coords.append(phi_r) # Angle is always an unknown coord for rods
        
        # Define rod frame based on this angle
        rod_frame = ReferenceFrame(f'R_{rod.id}')
        rod_frame.orient_axis(N, N.z, phi_r)
        sympy_frames[rod.id] = rod_frame
        
        # Define START Point:
        start_pt_sm = None
        start_point_defined_by_unknowns = False
        if rod.start_connection:
            target_comp_id, target_point_id_or_type = rod.start_connection
            target_point_sm = sympy_points.get((target_comp_id, target_point_id_or_type))
            if target_point_sm:
                # If connected to a known point, use that point as the start point!
                start_pt_sm = target_point_sm 
                print(f"  Rod {rod.id}: Start point set directly to known point {target_comp_id}.{target_point_id_or_type}")
            else:
                print(f"ERROR: Cannot find target point {rod.start_connection} for Rod {rod.id} start. Defining with unknown coordinates.")
                sx_r, sy_r = dynamicsymbols(f'sx_{rod.id}, sy_{rod.id}')
                unknown_generalized_coords.extend([sx_r, sy_r])
                start_pt_sm = O.locatenew(f'P_{rod.id}_start_UNK', sx_r * N.x + sy_r * N.y)
                sympy_rod_start_unk_coords[rod.id] = (sx_r, sy_r)
                start_point_defined_by_unknowns = True
        else:
            # If no start connection, it MUST be defined by unknown coordinates
            print(f"  Rod {rod.id}: Start point defined with unknown coordinates as it's unconnected.")
            sx_r, sy_r = dynamicsymbols(f'sx_{rod.id}, sy_{rod.id}')
            unknown_generalized_coords.extend([sx_r, sy_r])
            start_pt_sm = O.locatenew(f'P_{rod.id}_start_UNK', sx_r * N.x + sy_r * N.y)
            sympy_rod_start_unk_coords[rod.id] = (sx_r, sy_r)
            start_point_defined_by_unknowns = True
            
        if start_pt_sm is None:
            print(f"CRITICAL ERROR: Could not define start point for Rod {rod.id}. Skipping rod.")
            # Potentially raise an exception here instead of continuing
            continue 

        sympy_points[(rod.id, 'start')] = start_pt_sm

        # Define END Point relative to START Point using length and angle
        end_pt_sm = start_pt_sm.locatenew(f'P_{rod.id}_end', rod.length * rod_frame.x)
        sympy_points[(rod.id, 'end')] = end_pt_sm

        # Define Body (using the now defined start_pt_sm as masscenter)
        # Using start point as mass center might not be physically accurate, but okay for kinematics
        # body_r = Body(f'Body_{rod.id}', masscenter=start_pt_sm, frame=rod_frame)
        # sympy_bodies[rod.id] = body_r
        rigidbody_r = RigidBody(f'Body_{rod.id}', masscenter=start_pt_sm, frame=rod_frame)
        sympy_bodies[rod.id] = rigidbody_r
        
        # Define Mid Point if it exists (relative to START point)
        if rod.mid_point_distance is not None:
            mid_pt_sm = start_pt_sm.locatenew(f'P_{rod.id}_mid', rod.mid_point_distance * rod_frame.x)
            sympy_points[(rod.id, 'mid')] = mid_pt_sm
            
        # Define Pen Point if it exists (relative to START point)
        if rod.id == pen_rod_id:
            pen_point_sm = start_pt_sm.locatenew(f'P_pen', pen_distance_from_start * rod_frame.x)
            # We will need to extract the position of this point later

    # ---------------------------------------------------
    # --- 3. Define Joints (Constraints) --------------
    # ---------------------------------------------------
    print("  Defining SymPy Joints...")
    constraints = [] # We'll store constraint equations here for nsolve
    
    for rod in rods:
        rod_start_pt_sm = sympy_points.get((rod.id, 'start'))
        rod_end_pt_sm = sympy_points.get((rod.id, 'end'))
        rod_mid_pt_sm = sympy_points.get((rod.id, 'mid')) # Might be None
        
        if not rod_start_pt_sm or not rod_end_pt_sm:
            print(f"WARNING: Missing start/end point for Rod {rod.id} during constraint setup.")
            continue

        # Start Connection Constraint
        # Only needed if start point was defined using unknown coordinates (sx_r, sy_r)
        if rod.id in sympy_rod_start_unk_coords:
            if rod.start_connection:
                 target_comp_id, target_point_id_or_type = rod.start_connection
                 target_point_sm = sympy_points.get((target_comp_id, target_point_id_or_type))
                 if target_point_sm:
                     print(f"  Rod {rod.id}: Adding start constraint for unknown coords ({rod.start_connection}).")
                     constraint_vector = rod_start_pt_sm.pos_from(O) - target_point_sm.pos_from(O)
                     constraints.append(constraint_vector.dot(N.x))
                     constraints.append(constraint_vector.dot(N.y))
                 else:
                     print(f"WARNING: Missing target SymPy Point for Rod {rod.id} start constraint (with unk coords): {rod.start_connection}")
            # else: If start had unk coords but NO connection, it's a free start point?
            #      This case might need more thought - is it physically valid in this simulator?

        # End Connection Constraint
        if rod.end_connection:
            target_comp_id, target_point_id_or_type = rod.end_connection
            target_point_sm = sympy_points.get((target_comp_id, target_point_id_or_type))
            if target_point_sm:
                print(f"  Rod {rod.id}: Adding end constraint ({rod.end_connection}).")
                constraint_vector = rod_end_pt_sm.pos_from(O) - target_point_sm.pos_from(O)
                constraints.append(constraint_vector.dot(N.x))
                constraints.append(constraint_vector.dot(N.y))
            else: 
                print(f"WARNING: Missing target SymPy Point for Rod {rod.id} end constraint: {rod.end_connection}")
            
        # Mid-Point Connection Constraint
        if rod.mid_point_connection and rod.mid_point_distance is not None:
             target_comp_id, target_point_id_or_type = rod.mid_point_connection
             target_point_sm = sympy_points.get((target_comp_id, target_point_id_or_type))
             if target_point_sm and rod_mid_pt_sm:
                 print(f"  Rod {rod.id}: Adding mid constraint ({rod.mid_point_connection}).")
                 constraint_vector = rod_mid_pt_sm.pos_from(O) - target_point_sm.pos_from(O)
                 constraints.append(constraint_vector.dot(N.x))
                 constraints.append(constraint_vector.dot(N.y))
             elif not rod_mid_pt_sm:
                 print(f"WARNING: Rod {rod.id} missing mid-point for mid constraint.")
             else: # target_point_sm is missing
                 print(f"WARNING: Missing target SymPy Point for Rod {rod.id} mid constraint: {rod.mid_point_connection}")

    # ---------------------------------------------------
    # --- 4. Assemble Mechanism & Solve ---------------
    # ---------------------------------------------------
    print("  Setting up solver...")
    
    # System of constraint equations
    if not constraints:
         print("ERROR: No constraints defined for the mechanism.")
         # Return dummy data
         print("  WARNING: Using dummy path data.") ; radius = 100; omega = 2 * sympy.pi / 5.0 ; path_points = [QPointF(radius*math.cos(omega*t_val), radius*math.sin(omega*t_val)) for t_val in time_values] ; return path_points
         
    constraint_eqs = Matrix(constraints)
    
    # Define all symbols: unknowns (rod angles) and knowns (time, wheel angles)
    unknown_symbols = Matrix(unknown_generalized_coords)
    known_symbols = [t] + list(known_angles_func.keys())
    all_dep_symbols = list(unknown_symbols) + known_symbols
    
    # Create numerical functions
    try:
        print("  Lambdifying constraint equations...")
        # Function signature: f(unknown_vals, known_vals)
        lambdify_constraints = lambdify([unknown_symbols, known_symbols], constraint_eqs, 'numpy')
        
        print("  Lambdifying pen position...")
        if not pen_point_sm:
            raise ValueError("Pen point was not successfully defined in SymPy model.")
        pen_pos_vec = pen_point_sm.pos_from(O)
        lambdify_pen_pos = lambdify(all_dep_symbols, [pen_pos_vec.dot(N.x), pen_pos_vec.dot(N.y)], 'numpy')
        
    except Exception as e:
        print(f"ERROR during lambdify: {e}")
        print("  WARNING: Using dummy path data due to lambdify error.") ; radius = 100; omega = 2 * sympy.pi / 5.0 ; path_points = [QPointF(radius*math.cos(omega*t_val), radius*math.sin(omega*t_val)) for t_val in time_values] ; return path_points
        
    # --- Numerical Loop using nsolve --- 
    print("  Starting numerical solution loop (nsolve)...")
    # Initial guess for rod angles (e.g., 0)
    current_guess = np.zeros(len(unknown_symbols))
    
    solution_successful = True
    for i, current_t_val in enumerate(time_values):
        if i % (steps // 10) == 0: print(f"    Solving step {i}/{steps}...")
        
        # Evaluate known angles at current time
        known_vals = [current_t_val] + [func.subs(t, current_t_val) for func in known_angles_func.values()]
        known_vals_np = np.array(known_vals, dtype=float)
        
        # Define function for the solver: constraint_func(unknowns) = 0
        def constraint_func_at_t(unknown_vals_np):
             # Need to handle potential shape issues for lambdify
             res_vector = lambdify_constraints(unknown_vals_np.reshape(-1,1), known_vals_np.reshape(-1,1))
             return res_vector.flatten()

        # Solve for unknown rod angles at this time step
        try:
            # Using nsolve requires symbolic substitution first, which is slow.
            # Using scipy.optimize.root might be better with the lambdified function.
            
            # --- Attempt with nsolve (might be slow) --- 
            # subst = {sym: val for sym, val in zip(known_symbols, known_vals)}
            # solution = nsolve(constraint_eqs.subs(subst), unknown_symbols, current_guess, verify=False)
            # solved_unknowns = np.array(solution, dtype=float).flatten()
            
            # --- Attempt with scipy.optimize.root (using lambdify) --- 
            from scipy.optimize import root
            sol = root(constraint_func_at_t, current_guess, method='lm') # Levenberg-Marquardt often good for this
            if not sol.success:
                 print(f"WARNING: Solver failed at step {i}, t={current_t_val:.2f}. Message: {sol.message}")
                 # Use previous solution or guess? Could lead to errors.
                 # For now, stop calculation if solver fails significantly
                 if i > 10: # Allow some initial steps to fail potentially
                     solution_successful = False
                     break 
                 solved_unknowns = current_guess # Fallback to guess
            else:
                 solved_unknowns = sol.x
                 current_guess = solved_unknowns # Use solution as guess for next step

        except Exception as e:
            print(f"ERROR during numerical solve at step {i}, t={current_t_val:.2f}: {e}")
            solution_successful = False
            break
            
        # Calculate pen position using solved unknowns
        try:
            all_vals_np = np.concatenate((solved_unknowns, known_vals_np))
            pen_pos_abs_np = lambdify_pen_pos(*all_vals_np) # Returns numpy array [x, y]
            # Always convert the absolute position numpy array to QPointF first
            pen_pos_abs_qpoint = QPointF(float(pen_pos_abs_np[0]), float(pen_pos_abs_np[1]))
        except Exception as e:
             print(f"ERROR evaluating pen position at step {i}, t={current_t_val:.2f}: {e}")
             solution_successful = False
             break
             
        # Transform to canvas relative frame and store
        point_to_store = pen_pos_abs_qpoint # Default to absolute QPointF
        if canvas_wheel:
            # --- DEBUG PRINTS --- 
            if i < 5 or i % (steps // 10) == 0: # Print for first few steps and occasionally
                print(f"    [t={current_t_val:.2f}] Canvas Transform: Rate={canvas_wheel.rotation_rate:.2f}, Center=({canvas_wheel.center.x():.1f}, {canvas_wheel.center.y():.1f})")
            # --- END DEBUG --- 
            center = canvas_wheel.center
            # Calculate canvas angle based on direct time integration
            angle_deg = canvas_wheel.rotation_rate * current_t_val 
            angle_rad = -math.radians(angle_deg)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            # Use the QPointF version for calculations with center
            relative_pos = pen_pos_abs_qpoint - center 
            rot_rel_x = relative_pos.x() * cos_a - relative_pos.y() * sin_a
            rot_rel_y = relative_pos.x() * sin_a + relative_pos.y() * cos_a
            # Overwrite point_to_store with the rotated QPointF
            point_to_store = QPointF(rot_rel_x, rot_rel_y)
            # --- DEBUG PRINTS --- 
            if i < 5 or i % (steps // 10) == 0:
                # Use the QPointF version for printing absolute position
                print(f"        Abs=({pen_pos_abs_qpoint.x():.2f}, {pen_pos_abs_qpoint.y():.2f}), AngleDeg={angle_deg:.2f}, Rel=({relative_pos.x():.2f}, {relative_pos.y():.2f}), Rot=({point_to_store.x():.2f}, {point_to_store.y():.2f})")
            # --- END DEBUG --- 
        else:
             # --- DEBUG PRINTS --- 
             if i < 5 or i % (steps // 10) == 0:
                 print(f"    [t={current_t_val:.2f}] No canvas wheel detected for transformation.")
             # --- END DEBUG --- 
                    
        # Now point_to_store is guaranteed to be a QPointF
        path_points.append(point_to_store)

    if not solution_successful:
        print("  WARNING: Solver failed. Path data might be incomplete or inaccurate.")

    print(f"SymPy calculation finished. Generated {len(path_points)} points.")
    return path_points 