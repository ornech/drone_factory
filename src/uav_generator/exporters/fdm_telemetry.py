#!/usr/bin/env python3
import csv
import socket
import time
import math
from pathlib import Path
from typing import Dict, Any
import argparse

PROPERTY_TREE = [
    # Position
    'position/latitude-deg',
    'position/longitude-deg',
    'position/altitude-ft',
    'position/ground-elev-ft',
    'position/agl-ft',
    # Orientation
    'orientation/roll-deg',
    'orientation/pitch-deg',
    'orientation/heading-deg',
    # Velocities
    'velocities/airspeed-kt',
    'velocities/uBody-fps',
    'velocities/vBody-fps',
    'velocities/wBody-fps',
    # Accelerations
    'accelerations/pilot/x-accel-fps_sec',
    'accelerations/pilot/y-accel-fps_sec',
    'accelerations/pilot/z-accel-fps_sec',
    # JSBSim Forces
    'fdm/jsbsim/forces/fbx-total-lbs',
    'fdm/jsbsim/forces/fby-total-lbs',
    'fdm/jsbsim/forces/fbz-total-lbs',
    # Moments
    'fdm/jsbsim/moments/l-total-lbsft',
    'fdm/jsbsim/moments/m-total-lbsft',
    'fdm/jsbsim/moments/n-total-lbsft',
    # Controls
    'controls/flight/aileron',
    'controls/flight/elevator',
    'controls/flight/rudder',
    'controls/engines/engine/throttle',
    # Gear
    'gear/gear[0]/compression-m',
    'gear/gear[1]/compression-m',
    'gear/gear[2]/compression-m',
    # Mass/CG
    'fdm/jsbsim/inertia/cg-x-in',
    'fdm/jsbsim/inertia/cg-y-in',
    'fdm/jsbsim/inertia/cg-z-in',
    'fdm/jsbsim/inertia/weight-lbs',
    # Trim
    'fdm/jsbsim/trim/status',
    'fdm/jsbsim/trim/iterations',
]

def is_nan_inf(val):
    return math.isnan(val) or math.isinf(val)

def analyze_diagnostic(csv_file: Path) -> Dict[str, Any]:
    issues = []
    forces_null = True
    velocities_null = True
    nan_detected = False

    with open(csv_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            for key in row:
                try:
                    v = float(row[key])
                    if is_nan_inf(v):
                        nan_detected = True
                    if 'fb' in key and abs(v) > 0.1:
                        forces_null = False
                    if 'uBody' in key or 'vBody' in key or 'wBody' in key:
                        if abs(v) > 0.1:
                            velocities_null = False
                except:
                    pass

    if nan_detected:
        issues.append("geometrie_sol_incoherente")
    if forces_null:
        issues.append("aerodynamique_invalide")
    if velocities_null:
        issues.append("moteur_sans_poussee")

    return {"issues": issues, "nan_detected": nan_detected, "forces_null": forces_null}

def main():
    parser = argparse.ArgumentParser(description="JSBSim FDM Telemetry Monitor")
    parser.add_argument("--duration", type=float, default=30.0, help="Duration in seconds")
    parser.add_argument("--output", default="Reports/fdm_telemetry.csv", help="Output CSV")
    parser.add_argument("--port", type=int, default=5505, help="FG Property UDP port")
    args = parser.parse_args()

    output_dir = Path(args.output).parent
    output_dir.mkdir(exist_ok=True, parents=True)

    telemetry_csv = Path(args.output)
    diagnostic_txt = telemetry_csv.with_name('fdm_diagnostic.txt')

    print(f"Listening on UDP {args.port} for {args.duration}s...")
    print("Expected: --native-fdm=socket,out,60,localhost,5505,udp,JSBSim")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('localhost', args.port))
        sock.settimeout(0.1)
        sock.setblocking(False)

        start_time = time.time()
        records = []

        while time.time() - start_time < args.duration:
            try:
                data, addr = sock.recvfrom(4096)
                lines = data.decode('utf-8').splitlines()
                timestamp = time.time()
                for line in lines:
                    if line.strip():
                        prop_path, prop_value = line.split(' ', 1)
                        # Store all (simple)
                        records.append({
                            'time': timestamp,
                            prop_path: prop_value
                        })
            except BlockingIOError:
                time.sleep(0.1)
            except Exception as e:
                print(f"Socket error: {e}")

        # Write CSV
        if records:
            fieldnames = ['time'] + [prop for prop in PROPERTY_TREE if any(prop in r for r in records)]
            with open(telemetry_csv, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for record in records:
                    row = {'time': record['time']}
                    for prop in fieldnames[1:]:
                        row[prop] = record.get(prop, '')
                    writer.writerow(row)

            diag = analyze_diagnostic(telemetry_csv)
            with open(diagnostic_txt, 'w') as f:
                f.write("FDM Diagnostic\n")
                f.write(f"NaN detected: {diag['nan_detected']}\n")
                f.write(f"Forces null: {diag['forces_null']}\n")
                f.write(f"Probable causes: {diag['issues']}\n")

            print(f"Wrote {len(records)} records to {telemetry_csv}")
            print(f"Diagnostic: {diagnostic_txt}")
        else:
            print("No data received")

if __name__ == "__main__":
    main()

