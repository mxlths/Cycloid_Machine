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
        omega_c_val = canvas_wheel.rotation_rate # Assumed to be rad/s now
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
        omega_w_val = wheel.rotation_rate # Assumed to be rad/s now
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
            
    # --- Rod Bodies and Points (Refined v3 - Explicit Start Coords) --- 
    pen_point_sm = None # Initialize pen point
    # sympy_rod_start_unk_coords: Dict[int, Tuple[sympy.Expr, sympy.Expr]] = {} # No longer needed
    for rod in rods:
        # Define unknown angle AND unknown start coordinates for the rod
        phi_r = dynamicsymbols(f'phi_{rod.id}')
        sx_r, sy_r = dynamicsymbols(f'sx_{rod.id}, sy_{rod.id}')
        rod_angles_sym[rod.id] = phi_r
        # Add all 3 as unknowns
        unknown_generalized_coords.extend([phi_r, sx_r, sy_r]) 
        
        # Define rod frame based on the unknown angle
        rod_frame = ReferenceFrame(f'R_{rod.id}')
        rod_frame.orient_axis(N, N.z, phi_r)
        sympy_frames[rod.id] = rod_frame
        
        # Define START Point using unknown coordinates
        start_pt_sm = O.locatenew(f'P_{rod.id}_start_UNK', sx_r * N.x + sy_r * N.y)
        # Set velocity to zero initially? Or let constraints handle it? Let constraints handle it.
        # start_pt_sm.set_vel(N, 0) 
        sympy_points[(rod.id, 'start')] = start_pt_sm

        # Define END Point relative to START Point using length and angle
        end_pt_sm = start_pt_sm.locatenew(f'P_{rod.id}_end', rod.length * rod_frame.x)
        sympy_points[(rod.id, 'end')] = end_pt_sm

        # Define Body (using the start_pt_sm as masscenter)
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
    # --- 3. Define Constraints (Explicit Start/End/Mid) ---
    # ---------------------------------------------------
    print("  Defining SymPy Joints (Explicit Start/End/Mid)...")
    constraints = [] # We'll store constraint equations here for nsolve
    
    for rod in rods:
        rod_start_pt_sm = sympy_points.get((rod.id, 'start'))
        rod_end_pt_sm = sympy_points.get((rod.id, 'end'))
        rod_mid_pt_sm = sympy_points.get((rod.id, 'mid')) # Might be None
        
        if not rod_start_pt_sm or not rod_end_pt_sm:
            print(f"WARNING: Missing start/end point definition for Rod {rod.id} during constraint setup.")
            continue

        # --- Start Connection Constraint (Add EXPLICITLY if connection exists) ---
        if rod.start_connection:
             target_comp_id, target_point_id_or_type = rod.start_connection
             target_point_sm = sympy_points.get((target_comp_id, target_point_id_or_type))
             if target_point_sm:
                 print(f"  Rod {rod.id}: Adding EXPLICIT start constraint ({rod.start_connection}).")
                 constraint_vector = rod_start_pt_sm.pos_from(O) - target_point_sm.pos_from(O)
                 constraints.append(constraint_vector.dot(N.x))
                 constraints.append(constraint_vector.dot(N.y))
             else:
                 print(f"WARNING: Missing target SymPy Point for Rod {rod.id} start constraint: {rod.start_connection}")
        # If rod.start_connection is None, sx_r/sy_r remain unconstrained by connections.

        # --- End Connection Constraint (Same as before) ---
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
            # --- Attempt with scipy.optimize.root (using lambdify) --- 
            from scipy.optimize import root
            # Define tolerances (reverted from 1e-12)
            solver_options = {'xtol': 1e-9, 'ftol': 1e-9}
            sol = root(constraint_func_at_t, current_guess, method='lm', options=solver_options) # Pass options
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
             
        # Append the absolute point calculated earlier
        path_points.append(pen_pos_abs_qpoint)

    if not solution_successful:
        print("  WARNING: Solver failed. Path data might be incomplete or inaccurate.")

    print(f"SymPy calculation finished. Generated {len(path_points)} points.")
    # Filter out NaN points before returning
    valid_path_points = [p for p in path_points if not (math.isnan(p.x()) or math.isnan(p.y()))]
    print(f"Returning {len(valid_path_points)} valid points.")
    return valid_path_points 