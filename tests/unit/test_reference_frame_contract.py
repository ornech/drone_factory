from uav_generator.reference_frame import frame_metadata, REFERENCE_FRAME_NAME


def test_reference_frame_contract():
    meta = frame_metadata()

    assert REFERENCE_FRAME_NAME == "NOSE_X_AFT_Y_RIGHT_Z_UP"
    assert meta["origin"] == "nose"
    assert meta["x_axis"] == "aft"
    assert meta["y_axis"] == "right"
    assert meta["z_axis"] == "up"
