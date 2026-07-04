from open_ep_framework.validation import validate_json_file


def test_vdt_profile_fixture_validates():
    assert validate_json_file(
        "examples/vdt_software_platforms.json",
        "schemas/vdt_profile.schema.json",
    )
