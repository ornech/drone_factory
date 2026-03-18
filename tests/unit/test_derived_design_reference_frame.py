from uav_generator.data_models import DerivedDesign


def test_derived_design_has_reference_frame():
    d = DerivedDesign()
    assert d.reference_frame == "NOSE_X_AFT_Y_RIGHT_Z_UP"
