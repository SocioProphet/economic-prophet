from open_ep_framework.validation import validate_json_file


def test_associated_surplus_measurement_fixture_validates():
    assert validate_json_file(
        "examples/associated_surplus_measurement.json",
        "schemas/associated_surplus.schema.json",
    )
