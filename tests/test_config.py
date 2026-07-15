from redcap_mcp.cli import _validated_profile
from redcap_mcp.config import ConfigStore
from redcap_mcp.models import Profile


def test_config_never_contains_token(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.put_profile(Profile("safe", "https://example.test", project_title="Safe"), True)
    assert "token" not in store.path.read_text().lower()
    assert store.get_profile().name == "safe"


def test_setup_normalizes_redcap_api_url_with_trailing_slash():
    profile = _validated_profile("safe", "https://redcap.example.edu/redcap/api", None)
    assert profile.api_url == "https://redcap.example.edu/redcap/api/"
