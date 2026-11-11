from __future__ import annotations

import httpx
import pytest

from binaaz_sdk import BinaAz, ConfigurationError, Settings, messages

from .conftest import Gateway, data


def test_environment(monkeypatch):
    monkeypatch.setenv("BINAAZ_COOKIE", "_binaaz_session=env")
    monkeypatch.setenv("BINAAZ_TIMEOUT", "12")
    monkeypatch.setenv("BINAAZ_ENDPOINTS__GRAPHQL", "/api/graphql")
    client = BinaAz()
    assert client.cookie == "_binaaz_session=env" and client.settings.timeout == 12
    assert client.settings.url("base_url", "graphql") == "https://bina.az/api/graphql"


def test_config_file(tmp_path):
    path = tmp_path / "binaaz.toml"
    path.write_text('max_retries = 5\nuser_agent = "crm/2 binaaz-python-sdk/{version}"\n')
    client = BinaAz(config_file=str(path))
    assert client.settings.max_retries == 5
    assert client.settings.resolved_user_agent().startswith("crm/2 binaaz-python-sdk/0.")


def test_plain_http_is_refused():
    with pytest.raises(ConfigurationError):
        BinaAz(base_url="http://bina.example")
    assert BinaAz(base_url="http://localhost:8000").settings.base_url == "http://localhost:8000"
    assert BinaAz(base_url="http://bina.example", allow_insecure_http=True)


def test_bad_address():
    with pytest.raises(ValueError):
        Settings(base_url="bina.az")


def test_user_agent_is_sent():
    gw = Gateway().reply(data(cities=[]))
    client = BinaAz(user_agent="crm/1", http_client=httpx.Client(transport=httpx.MockTransport(gw)))
    client.catalog.cities()
    assert gw.header("user-agent") == "crm/1"


def test_messages_can_be_replaced():
    try:
        messages.use({"error": {"session": "Oturum bitti"}})
        assert messages.text("error.session") == "Oturum bitti"
        with pytest.raises(KeyError):
            messages.use({"error": {"nope": "x"}})
    finally:
        messages.reset()


def test_settings_overrides_keep_the_cookie():
    base = Settings(cookie="_binaaz_session=a")
    client = BinaAz(settings=base, timeout=5)
    assert client.cookie == "_binaaz_session=a" and client.settings.timeout == 5
