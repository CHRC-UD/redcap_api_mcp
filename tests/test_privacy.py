from redcap_mcp.models import Profile
from redcap_mcp.privacy import assert_safe_inputs, sanitize_rows
from redcap_mcp.errors import PrivacyError


META = {
    "record_id": {"field_name": "record_id", "field_type": "text", "identifier": "y"},
    "age": {"field_name": "age", "field_type": "text", "identifier": ""},
    "symptoms": {"field_name": "symptoms", "field_type": "checkbox", "identifier": ""},
    "email": {"field_name": "email", "field_type": "text", "identifier": "y"},
}


def test_identifiers_are_withheld_and_record_id_is_aliased():
    profile = Profile("one", "https://example.test")
    rows, withheld = sanitize_rows(
        [{"record_id": "42", "email": "a@b.test", "age": "20", "unknown": "no"}],
        profile,
        META,
        False,
        b"secret",
    )
    assert rows[0]["record_alias"].startswith("record_")
    assert rows[0] == {"record_alias": rows[0]["record_alias"], "age": "20"}
    assert set(withheld) == {"record_id", "email", "unknown"}


def test_alias_varies_between_profile_keys():
    one, _ = sanitize_rows([{"record_id": "42"}], Profile("a", "https://a.test"), META, False, b"a")
    two, _ = sanitize_rows([{"record_id": "42"}], Profile("b", "https://b.test"), META, False, b"b")
    assert one[0]["record_alias"] != two[0]["record_alias"]


def test_identifier_input_needs_two_gates():
    profile = Profile("one", "https://example.test")
    try:
        assert_safe_inputs(["email"], None, None, profile, META, False)
    except PrivacyError:
        pass
    else:
        raise AssertionError("protected field was permitted")
    profile.identifiers_enabled = True
    assert_safe_inputs(["email"], None, None, profile, META, True)


def test_checkbox_columns_inherit_policy():
    metadata = {**META, "symptoms": {**META["symptoms"], "identifier": "y"}}
    rows, withheld = sanitize_rows(
        [{"symptoms___1": "1"}], Profile("one", "https://example.test"), metadata, False, b"x"
    )
    assert rows == [{}]
    assert withheld == ["symptoms___1"]
