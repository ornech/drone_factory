# uav_generator/constants.py

# This file holds shared constants used across different calculator modules
# to ensure consistency in physical and empirical values.

# --- Physical Constants ---
G = 9.81  # Gravitational acceleration (m/s^2)
RHO = 1.225 # Air density at sea level (kg/m^3)

# --- Performance & Material Heuristics ---

# Wh/kg - Energy density for modern Li-Ion/LiPo battery packs
BATTERY_ENERGY_DENSITY_WH_KG = 180.0

# Assumed overall propulsive efficiency (motor * ESC * propeller) for cruise
ETA_PROPULSIVE_CRUISE = 0.65

# Assumed overall propulsive efficiency for static thrust conditions
ETA_PROPULSIVE_STATIC = 0.50

# Assumed usable depth of discharge of the battery to preserve its lifespan
BATTERY_USABLE_CAPACITY_FRACTION = 0.8

# g/W - Mass estimation for motor and ESC based on max power
PROPULSION_SYSTEM_MASS_FACTOR_G_PER_W = 1.6

# Oswald efficiency number (e), accounts for non-ideal lift distribution
OSWALD_EFFICIENCY_E = 0.8

# Estimated zero-lift drag coefficient for a clean UAV airframe
CD0_CLEAN_AIRFRAME = 0.025

# Target static thrust-to-weight ratio for acceptable takeoff performance
MIN_TWR_STATIC = 0.5
