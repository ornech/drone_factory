from uav_generator.data_models import DerivedDesign

def test_derived_design_inventory_contains_visual_geometry():
    expected = {
        "mass_budget",
        "wing_geometry",
        "stability",
        "empennages",
        "gouvernes",
        "fuselage",
        "power_and_battery",
        "ground_reactions",
        "control_system",
        "vertical_geometry",
        "visual_geometry",
        "blocking_issues",
    }
    actual = set(DerivedDesign.model_fields.keys())
    assert actual == expected
