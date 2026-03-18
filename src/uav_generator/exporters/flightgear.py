# uav_generator/exporters/flightgear.py
import shutil
from pathlib import Path

def copy_to_flightgear(package_dir: Path):
    """
    Copies the generated UAV package to the user's FlightGear/Aircraft directory.
    """
    uav_name = package_dir.name
    print(f"INFO: Attempting to copy '{uav_name}' to FlightGear Aircraft directory...")

    # Standard locations for the FlightGear aircraft directory
    possible_fg_paths = [
        Path.home() / ".fgfs" / "Aircraft",
        Path.home() / "Documents" / "FlightGear" / "Aircraft"
    ]

    fg_aircraft_dir = None
    for path in possible_fg_paths:
        if path.is_dir():
            fg_aircraft_dir = path
            break
    
    if not fg_aircraft_dir:
        print("WARNING: Could not automatically locate FlightGear Aircraft directory.")
        print("Please copy the contents of the '{}' directory manually.".format(package_dir))
        return False

    destination_dir = fg_aircraft_dir / uav_name
    
    # Check if the directory already exists
    if destination_dir.exists():
        print(f"INFO: Directory '{destination_dir}' already exists. Overwriting...")
        try:
            shutil.rmtree(destination_dir)
        except OSError as e:
            print(f"ERROR: Could not remove existing directory '{destination_dir}'. {e}")
            print("Please check file permissions.")
            return False

    print(f"INFO: Copying package to '{destination_dir}'...")
    try:
        shutil.copytree(package_dir, destination_dir)
        print("INFO: Copy successful. The aircraft should now be available in FlightGear.")
    except OSError as e:
        print(f"ERROR: Failed to copy package. {e}")
        return False

    return True
