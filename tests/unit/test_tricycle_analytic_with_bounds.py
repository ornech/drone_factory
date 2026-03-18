import math

def test_analytic_respects_fuselage_bounds():
    cg_x = 0.20
    fuselage_length = 1.2
    h = 0.10

    theta = math.radians(20.0)
    d = h / math.tan(theta)
    x_main = cg_x + d

    assert x_main < fuselage_length
