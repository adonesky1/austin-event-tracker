def test_load_austin_config(austin_config):
    assert austin_config.name == "austin"
    assert austin_config.timezone == "America/Chicago"
    assert "Downtown" in austin_config.neighborhoods
    assert "eventbrite" in austin_config.default_sources


def test_austin_config_coordinates(austin_config):
    assert 30.0 < austin_config.latitude < 31.0
    assert -98.0 < austin_config.longitude < -97.0


def test_austin_config_has_radius(austin_config):
    assert austin_config.radius_miles == 30
