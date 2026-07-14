from redcap_mcp.config import ConfigStore
from redcap_mcp.models import Profile


def test_config_never_contains_token(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    store.put_profile(Profile("safe", "https://example.test", project_title="Safe"), True)
    assert "token" not in store.path.read_text().lower()
    assert store.get_profile().name == "safe"
