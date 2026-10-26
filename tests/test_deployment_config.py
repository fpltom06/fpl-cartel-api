import pytest
from app.config import get_settings

def test_initial_deployment_can_deny_all_browser_origins(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "")
    assert get_settings().allowed_origins == ()

@pytest.mark.parametrize("origin", ["*", "https://*.netlify.app", "https://example.netlify.app/path"])
def test_no_wildcard_or_paths(monkeypatch, origin):
    monkeypatch.setenv("ALLOWED_ORIGINS", origin)
    with pytest.raises(ValueError):
        get_settings()
