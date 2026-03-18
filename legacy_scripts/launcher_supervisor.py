#!/usr/bin/env python3
import subprocess
import threading
import time
import random

import dearpygui.dearpygui as dpg

supervisor = None

class XXLSupervisor:
    def __init__(self):
        self.fg_running = False
        self.ias = 0
        self.alt = 0
        self.roll = 0

    def launch(self):
        self.fg_running = True
        threading.Thread(target=self.sim_data, daemon=True).start()

    def sim_data(self):
        t = 0
        while self.fg_running:
            self.ias = 40 + 40 * random.random()
            self.alt = 1000 + 7000 * random.random()
            self.roll = (random.random() - 0.5) * 20
            self.update_ui()
            time.sleep(0.1)
            t += 0.1

    def update_ui(self):
        dpg.set_value('ias_display', f'{self.ias:.0f}')
        dpg.set_value('alt_display', f'{self.alt:.0f}')
        dpg.set_value('roll_display', f'{self.roll:.1f}')
        dpg.configure_item('ias_bar', default_value=self.ias/200)
        dpg.configure_item('alt_bar', default_value=self.alt/12000)

def mega_ui():
    global supervisor
    supervisor = XXLSupervisor()
    
    dpg.create_context()
    
    with dpg.font_registry():
        font = dpg.add_font('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 72)
        dpg.bind_font(font)
    
    dpg.create_viewport(title='🚀 XXL DRONE SUPERVISION 🚀', width=1920, height=1080)
    
    with dpg.window(no_title_bar=True, width=1920, height=1080, tag="main"):
        
        # MEGA TITRE
        dpg.add_text("🚀 POSTE SUPERVISION XXL 🚀", color=[255,255,0])
        
        # STATUS
        dpg.add_text("STATUS: STOPPED", tag='status_text', color=[255,0,0])
        
        # BUTTON MEGA
        dpg.add_button(label='🚀 LANCER', width=500, height=150, callback=supervisor.launch)
        
        # BIG TILES
        dpg.add_text("IAS XXL")
        dpg.add_progress_bar(tag='ias_bar', width=1400, height=100)
        dpg.add_text('0', tag='ias_display', color=[0,255,0])
        
        dpg.add_text("ALT XXL")
        dpg.add_progress_bar(tag='alt_bar', width=1400, height=100)
        dpg.add_text('0', tag='alt_display', color=[0,255,0])
        
        dpg.add_text("ROLL XXL")
        dpg.add_text('0', tag='roll_display', color=[255,255,0])
        
        # GRAPHS SIMPLE - FIXED
        plot = dpg.add_plot(width=1600, height=400, label='Trends')
        dpg.add_plot_legend(parent=plot)
        x_axis = dpg.add_plot_axis(dpg.mvXAxis, parent=plot)
        y_axis = dpg.add_plot_axis(dpg.mvYAxis, label='IAS', parent=plot)
        dpg.add_line_series([0], [0], label='IAS', tag='ias_line', parent=y_axis)
    
    dpg.setup_dearpygui()
    dpg.show_viewport()
    
    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()
        if supervisor.fg_running:
            dpg.set_value('status_text', "STATUS: RUNNING", color=[0,255,0])

if __name__ == '__main__':
    mega_ui()

