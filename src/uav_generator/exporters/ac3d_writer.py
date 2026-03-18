# uav_generator/exporters/ac3d_writer.py
import math
from pathlib import Path
from typing import List, Tuple
from ..data_models import ProjectInput, DerivedDesign, VisualGeometry

# --- AC3D Data Structures ---

class Ac3dMaterial:
    def __init__(self, name, rgb=(1,1,1), amb=(0.2,0.2,0.2), emis=(0,0,0), spec=(0.5,0.5,0.5), shi=10, trans=0):
        self.name = name
        self.rgb = rgb
        self.amb = amb
        self.emis = emis
        self.spec = spec
        self.shi = shi
        self.trans = trans

    def to_string(self):
        return (f'MATERIAL "{self.name}" '
                f'rgb {self.rgb[0]} {self.rgb[1]} {self.rgb[2]}  '
                f'amb {self.amb[0]} {self.amb[1]} {self.amb[2]}  '
                f'emis {self.emis[0]} {self.emis[1]} {self.emis[2]}  '
                f'spec {self.spec[0]} {self.spec[1]} {self.spec[2]}  '
                f'shi {self.shi}  trans {self.trans}')

class Ac3dSurface:
    def __init__(self, vertices_indices: List[int], mat_index=0):
        self.vertices_indices = vertices_indices
        self.mat_index = mat_index

    def to_string(self):
        # 0x30 = shaded + two_sided
        surf_type = 0x30
        header = f"SURF 0x{surf_type:02x}\nmat {self.mat_index}\nrefs {len(self.vertices_indices)}"
        
        # Simple planar UV mapping for now
        uv_coords = [(0,0), (1,0), (1,1), (0,1)]
        refs = []
        for i, vert_index in enumerate(self.vertices_indices):
            u, v = uv_coords[i % 4]
            refs.append(f"{vert_index} {u} {v}")
            
        return f"{header}\n" + "\n".join(refs)

class Ac3dObject:
    def __init__(self, name: str, obj_type: str = "poly"):
        self.name = name
        self.obj_type = obj_type
        self.vertices: List[Tuple[float, float, float]] = []
        self.surfaces: List[Ac3dSurface] = []
        self.children: List[Ac3dObject] = []
        self.location = (0, 0, 0)

    def add_child(self, child_obj):
        self.children.append(child_obj)

    def to_string(self, indent=""):
        lines = [
            f'{indent}OBJECT {self.obj_type}',
            f'{indent}name "{self.name}"',
            f'{indent}loc {self.location[0]} {self.location[1]} {self.location[2]}',
        ]
        if self.vertices:
            lines.append(f'{indent}numvert {len(self.vertices)}')
            lines.extend([f"{indent}{v[0]:.4f} {v[1]:.4f} {v[2]:.4f}" for v in self.vertices])
        
        if self.surfaces:
            lines.append(f'{indent}numsurf {len(self.surfaces)}')
            lines.extend([s.to_string() for s in self.surfaces])
        
        lines.append(f'{indent}kids {len(self.children)}')
        for child in self.children:
            lines.append(child.to_string(indent + "  "))
            
        return "\n".join(lines)

# --- Geometry Generation Functions ---

def _create_box(obj: Ac3dObject, dimensions: Tuple[float, float, float]):
    """Creates vertices and surfaces for a simple box.
    Dimensions are (length, width, height) along (X, Y, Z).
    """
    dl, dw, dh = dimensions[0]/2, dimensions[1]/2, dimensions[2]/2
    
    obj.vertices = [
        (-dl, -dw, -dh), (dl, -dw, -dh), (dl, dw, -dh), (-dl, dw, -dh), # bottom
        (-dl, -dw,  dh), (dl, -dw,  dh), (dl, dw,  dh), (-dl, dw,  dh)  # top
    ]
    
    obj.surfaces = [
        Ac3dSurface([0, 1, 2, 3]), # bottom
        Ac3dSurface([7, 6, 5, 4]), # top
        Ac3dSurface([0, 4, 7, 3]), # back (-x)
        Ac3dSurface([1, 2, 6, 5]), # front (+x)
        Ac3dSurface([2, 3, 7, 6]), # right (+y)
        Ac3dSurface([0, 1, 5, 4]), # left (-y)
    ]

def _create_trapezoid(obj: Ac3dObject, span, root_chord, tip_chord, thickness_ratio=0.05):
    """Creates vertices and surfaces for a trapezoidal wing.
    X is chordwise, Y is spanwise.
    """
    half_span = span / 2
    thickness = root_chord * thickness_ratio / 2
    
    # Bottom surface vertices
    v = [
        (-root_chord/2, 0, -thickness), (root_chord/2, 0, -thickness),           # root
        (-tip_chord/2, half_span, -thickness), (tip_chord/2, half_span, -thickness),   # right tip
        (-tip_chord/2, -half_span, -thickness), (tip_chord/2, -half_span, -thickness) # left tip
    ]
    # Top surface
    v.extend([(p[0], p[1], thickness) for p in v[:6]])
    obj.vertices = v

    obj.surfaces = [
        Ac3dSurface([6, 8, 9, 7]),       # Top Right
        Ac3dSurface([6, 7, 11, 10]),     # Top Left
        Ac3dSurface([0, 1, 3, 2]),       # Bottom Right
        Ac3dSurface([0, 5, 4, 1]),       # Bottom Left
        Ac3dSurface([2, 3, 9, 8]),       # Tip Right
        Ac3dSurface([4, 5, 11, 10]),     # Tip Left
    ]

# --- Main Generator ---

def design_to_ac3d(pos: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Convert a position from the project design frame to the AC3D export frame.

    Design frame:
    - origin at nose
    - X backward
    - Y right
    - Z up

    Current AC3D export convention:
    - X inverted
    - Y unchanged
    - Z unchanged
    """
    return (-pos[0], pos[1], pos[2])

def generate_ac3d_model(project: ProjectInput, design: DerivedDesign, output_path: Path):
    """
    Generates a complete .ac file from the derived design.

    Design reference frame (source of truth):
    - origin at nose
    - X backward
    - Y right
    - Z up

    Current AC3D export convention:
    - ac3d_x = -design_x
    - ac3d_y = design_y
    - ac3d_z = design_z
    """
    print("INFO: Generating AC3D model...")

    # --- Root and Materials ---
    root = Ac3dObject("world", obj_type="world")
    materials = [ Ac3dMaterial("DefaultWhite") ]

    # --- Geometry from Design ---
    wg = design.wing_geometry
    gr = design.ground_reactions
    emp = design.empennages
    vg = design.visual_geometry
    
    fuselage_length = vg.fuselage_length_m
    fuselage_width = vg.fuselage_width_m
    fuselage_height = vg.fuselage_height_m
    # Fuselage is centered around its own origin, then moved.
    # Its origin is placed at x=length/2 so the nose is at x=0 in the internal frame.
    fuselage_loc_ac3d = design_to_ac3d((fuselage_length / 2, 0, fuselage_height / 2))
    fuselage = Ac3dObject("fuselage")
    fuselage.location = fuselage_loc_ac3d
    _create_box(fuselage, (fuselage_length, fuselage_width, fuselage_height))
    root.add_child(fuselage)

    # Wing
    wing_loc_ac3d = design_to_ac3d((vg.wing_root_le_x_m, 0, vg.wing_z_m))
    wing = Ac3dObject("main_wing")
    wing.location = wing_loc_ac3d
    _create_trapezoid(wing, wg.envergure_m, wg.corde_racine_m, wg.corde_saumon_m)
    root.add_child(wing)

    htail_loc_ac3d = design_to_ac3d((vg.htail_arm_x_m, 0, vg.htail_z_m))
    h_stab = Ac3dObject("h_stab")
    h_stab.location = htail_loc_ac3d
    _create_trapezoid(h_stab, vg.htail_span_m, vg.htail_chord_root_m, vg.htail_chord_tip_m)
    root.add_child(h_stab)

    # Landing Gear
    # Wheel size must match the physical ground model
    wheel_radius = gr.wheel_radius_m
    wheel_width = vg.wheel_width_m
    for name, pos in [("nose", gr.nose_gear_pos), ("left", gr.main_gear_left_pos), ("right", gr.main_gear_right_pos)]:
        # The visual wheel's bottom should be at Z=0 in the design frame for simplicity.
        # The physics contact point is handled separately in JSBSim with a negative Z offset.
        # The wheel object's location is its center. The Z coordinate is calculated
        # from the physical contact point (pos[2]) plus the wheel's radius to
        # align the visual model with the physics model.
        wheel_loc_ac3d = design_to_ac3d((pos[0], pos[1], pos[2] + wheel_radius))
        wheel = Ac3dObject(f"{name}_wheel")
        wheel.location = wheel_loc_ac3d
        # Box dimensions are (length, width, height). For a wheel, this is (diam, width, diam).
        _create_box(wheel, (wheel_radius*2, wheel_width, wheel_radius*2))
        root.add_child(wheel)

    # --- Write to file ---
    content = ["AC3Db"]
    content.extend([m.to_string() for m in materials])
    content.append(root.to_string())
    
    try:
        output_path.write_text("\n".join(content))
        print(f"  - Wrote AC3D model to {output_path}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to write AC3D model. {e}")
        return False