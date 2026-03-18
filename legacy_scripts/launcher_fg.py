#!/usr/bin/env python3
import csv
import math
import os
import shlex
import socket
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

import dearpygui.dearpygui as dpg

FG_PRESETS = {
    "Standard": {"airport": "LFBD", "runway": "05"},
    "Debug sol": {"airport": "LFBD", "runway": "05", "freeze": True},
    "Test vol 8000ft": {"airport": "LFBD", "runway": "05", "vc": 100, "heading": 0, "altitude": 8000},
}

class FlightGearLauncher:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.fgfs_appimage = self.base_dir / "fgfs-appimage.sh"
        self.logs_base = self.base_dir / "logs"
        self.telem_port = 5003
        self.fdm_port = 5004
        self.process_fg = None
        self.telem_sock = None
        self.fields = ["roll_deg", "pitch_deg", "heading_deg", "alpha_deg", "slip_deg", 
                       "ias_kt", "vs_fps", "gs_kt", "lat_deg", "lon_deg", "altitude_ft", 
                       "mag_heading_deg", "cd", "cl", "trim_status", "fdm_valid", "agl_ft", "gear_compr"]
        self.status_tag = "status_label"
        self.ensure_logs()

    def ensure_logs(self):
        (self.logs_base / "flightgear").mkdir(parents=True, exist_ok=True)
        (self.logs_base / "telemetry").mkdir(parents=True, exist_ok=True)

    def get_available_aircraft(self):
        dirs = [Path.home() / ".fgfs" / "Aircraft", self.base_dir / "Aircraft"]
        dirs = [p for p in dirs if p.is_dir()]
        found = {}
        for d in dirs:
            for child in d.iterdir():
                if child.is_dir():
                    if any(p.name.endswith("-set.xml") for p in child.iterdir()):
                        found[child.name] = True
        return sorted(found.keys())

    def port_free(self, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0

    def build_command(self):
        cmd = [str(self.fgfs_appimage), "--launcher=0", "--geometry=1280x720", "--no-default-config"]
        try:
            aircraft = dpg.get_value("fg_aircraft")
        except:
            aircraft = "uav_obs_01"
        if aircraft:
            dirs = [Path.home() / ".fgfs" / "Aircraft", self.base_dir / "Aircraft"]
            dirs = [str(p) for p in dirs if p.is_dir()]
            if dirs:
                cmd.append(f"--fg-aircraft={':'.join(dirs)}")
            cmd.append(f"--aircraft={aircraft}")

        try:
            preset_name = dpg.get_value("preset_combo")
        except:
            preset_name = "Standard"
        preset = FG_PRESETS.get(preset_name, {})
        for key, value in preset.items():
            cmd.append(f"--{key}={value}")

        cmd.append(f"--generic=socket,out,60,127.0.0.1,{self.telem_port},udp,drone_link")

        try:
            if dpg.get_value("fg_telemetry_in"):
                cmd.append(f"--generic=socket,in,60,127.0.0.1,{self.fdm_port},udp,drone_link")
        except:
            pass

        return cmd

    def launch(self):
        if self.process_fg and self.process_fg.poll() is None:
            print("FG already running")
            return

        cmd = self.build_command()
        print("FGFS CMD:", ' '.join(cmd))

        if not self.port_free(self.telem_port):
            print("Port 5003 busy")
            return

        try:
            stdout = open(self.logs_base / "flightgear" / "fgfs_console.log", "w")
            self.process_fg = subprocess.Popen(cmd, stdout=stdout, stderr=subprocess.STDOUT)
            print("FGFS launched PID", self.process_fg.pid)
            threading.Thread(target=self.telemetry_loop, daemon=True).start()
        except Exception as e:
            print(f"Launch error: {e}")

    def stop(self):
        if self.process_fg:
            self.process_fg.terminate()
            self.process_fg.wait(timeout=5)
        print("FGFS stopped")
        self.process_fg = None

    def telemetry_loop(self):
        try:
            self.telem_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.telem_sock.bind(('127.0.0.1', self.telem_port))
            self.telem_sock.setblocking(False)
            csv_path = self.logs_base / "telemetry" / "drone_state.csv"
            open(csv_path, 'w').write(','.join(self.fields) + '\n')
            
            f = open(csv_path, 'a')
            writer = csv.writer(f)
            while self.process_fg and self.process_fg.poll() is None:
                try:
                    data, _ = self.telem_sock.recvfrom(1024)
                    line = data.decode('utf-8', errors='replace').strip().split(',')
                    if len(line) >= len(self.fields):
                        writer.writerow(line[:len(self.fields)])
                        f.flush()
                        self.update_tiles(line[:len(self.fields)])
                except BlockingIOError:
                    time.sleep(0.01)
                except Exception as e:
                    print(f"Telem error: {e}")
                    time.sleep(0.1)
            f.close()
        except Exception as e:
            print(f"Telem setup error: {e}")

    def update_tiles(self, line):
        try:
            vals = [float(x) for x in line[:len(self.fields)] if x.strip()]
            values = dict(zip(self.fields, vals[:len(self.fields)]))
            color_ok = [0, 255, 0]
            color_err = [255, 0, 0]
            color_warn = [255, 165, 0]
            
            # IAS color
            ias_color = color_ok if 50 < values['ias_kt'] < 150 else (color_warn if values['ias_kt'] > 0 else color_err)
            dpg.set_value("tile_ias", f"IAS {values['ias_kt']:.1f}")
            dpg.configure_item("tile_ias", color=ias_color)
            
            # ALT
            dpg.set_value("tile_alt", f"ALT {values['altitude_ft']:.0f}")
            
            # Angles
            dpg.set_value("tile_roll", f"ROLL {values['roll_deg']:.1f}°")
            dpg.set_value("tile_pitch", f"PITCH {values['pitch_deg']:.1f}°")
            
            # Trim/FDM/AGL (if available)
            if 'trim_status' in values:
                trim_status = "OK" if values['trim_status'] > 0 else "FAIL"
                dpg.set_value("tile_trim", trim_status)
                dpg.configure_item("tile_trim", color_ok if values['trim_status'] > 0 else color_err)
            if 'fdm_valid' in values:
                dpg.set_value("tile_fdm", "FDM " + ("OK" if values['fdm_valid'] else "FAIL"))
            if 'agl_ft' in values:
                agl_color = color_ok if values['agl_ft'] > 10 else color_warn if values['agl_ft'] > 0 else color_err
                dpg.set_value("tile_ag", f"AGL {values['agl_ft']:.1f}")
                dpg.configure_item("tile_ag", color=agl_color)
                
        except Exception:
            pass

def on_launch():
    launcher.launch()

def on_stop():
    launcher.stop()

def main():
    global launcher
    launcher = FlightGearLauncher()
    
    dpg.create_context()
    
    with dpg.window(label="Drone FG Supervisor - 3 Zones", width=1400, height=900):
        # Status bar
        dpg.add_text("Aircraft | Preset | FDM | UDP | Trim | Anomalies", tag="status_bar")
        dpg.add_separator()
        
        with dpg.group(horizontal=True):
            # Zone 1: Config gauche
            with dpg.child_window(width=380, height=-1):
                dpg.add_text("CONFIG LANCEMENT", color=[255, 255, 0])
                dpg.add_combo(label="Preset", items=list(FG_PRESETS.keys()), tag="preset_combo")
                dpg.add_combo(label="Aéronef", items=launcher.get_available_aircraft(), tag="fg_aircraft")
                dpg.add_input_text(label="Airport", default_value="LFBD", tag="airport")
                dpg.add_input_text(label="Runway", default_value="05", tag="runway")
                dpg.add_checkbox(label="Télémétrie IN", tag="fg_telemetry_in")
                dpg.add_separator()
                dpg.add_button(label="🚀 LANCER", callback=on_launch, width=-1)
                dpg.add_button(label="⏹ ARRÊTER", callback=on_stop, width=-1)
                dpg.add_button(label="📁 LOGS", callback=lambda: os.system("xdg-open logs"), width=-1)
            
            # Zone 2: Live centre
            with dpg.child_window(width=620, height=-1):
                dpg.add_text("SUPERVISION LIVE", color=[0, 255, 255])
                # Tuiles
                with dpg.table(header_row=True, row_background=True, width=-1):
                    dpg.add_table_column(label="IAS")
                    dpg.add_table_column(label="ALT")
                    dpg.add_table_column(label="ROLL")
                    dpg.add_table_column(label="PITCH")
                    dpg.add_table_column(label="HDG")
                    with dpg.table_row():
                        dpg.add_text("0 kt", tag="tile_ias")
                        dpg.add_text("0 ft", tag="tile_alt")
                        dpg.add_text("0°", tag="tile_roll")
                        dpg.add_text("0°", tag="tile_pitch")
                        dpg.add_text("0°", tag="tile_heading")
                
                # Plot
                with dpg.plot(height=120, width=-1):
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label="Temps")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Valeur", tag="y_axis")
                
                # Pilotage
                dpg.add_text("PILOTAGE MANUEL")
                dpg.add_slider_float(label="Throttle", tag="throttle", default_value=0.0)
                dpg.add_slider_float(label="Elevator", tag="elevator", default_value=0.0)
                dpg.add_slider_float(label="Aileron", tag="aileron", default_value=0.0)
                dpg.add_slider_float(label="Rudder", tag="rudder", default_value=0.0)
                dpg.add_button(label="ENVOYER CMD")
            
            # Zone 3: Logs droite
            with dpg.child_window(width=380, height=-1):
                dpg.add_text("LOGS TEMPS RÉEL", color=[255, 165, 0])
                with dpg.tab_bar():
                    with dpg.tab(label="Console"):
                        dpg.add_input_text(tag="console_log", multiline=True, readonly=True, height=350)
                    with dpg.tab(label="Anomalies"):
                        dpg.add_input_text(tag="anomaly_log", multiline=True, readonly=True, height=350)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="CLEAR")
                    dpg.add_button(label="OUVRIR DOSSIER", callback=lambda: os.system("xdg-open logs/telemetry"))

    dpg.create_viewport(title="Drone Supervisor", width=1400, height=900)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    
    while dpg.is_dearpygui_running():
        if launcher.process_fg and launcher.process_fg.poll() is not None:
            print("FG stopped")
        dpg.render_dearpygui_frame()

if __name__ == "__main__":
    main()

