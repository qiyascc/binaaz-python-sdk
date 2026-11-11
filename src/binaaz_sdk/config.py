from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode, urlsplit

from goodconf import Field, GoodConf, GoodConfConfigDict
from pydantic import BaseModel, SecretStr, field_validator

from ._version import __version__
from .errors import ConfigurationError
from .messages import text

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
SERVICES = ("base_url", "photos_url", "login_url")


class Endpoints(BaseModel):
    graphql: str = "/graphql"
    photo_upload: str = "/pond"
    photo_rotate: str = "/pond/rotate"
    code_send: str = "/auth"
    code_verify: str = "/auth/verify"


class Settings(GoodConf):
    model_config = GoodConfConfigDict(
        env_prefix="BINAAZ_",
        file_env_var="BINAAZ_CONFIG",
        default_files=["binaaz.toml", "binaaz.yaml", "binaaz.yml", "binaaz.json"],
        extra="ignore",
        env_nested_delimiter="__",
    )

    cookie: SecretStr = Field(default=SecretStr(""), description=text("settings.cookie"))
    base_url: str = Field(default="https://bina.az", description=text("settings.base_url"))
    photos_url: str = Field(default="https://photos.bina.az", description=text("settings.photos_url"))
    login_url: str = Field(default="https://api.digit-u.id", description=text("settings.login_url"))
    return_to: str = Field(default="https://bina.az/", description=text("settings.return_to"))
    endpoints: Endpoints = Field(default_factory=Endpoints, description=text("settings.endpoints"))
    language: str = Field(default="az", description=text("settings.language"))
    timeout: float = Field(default=30.0, gt=0, description=text("settings.timeout"))
    connect_timeout: float = Field(default=10.0, gt=0, description=text("settings.connect_timeout"))
    max_retries: int = Field(default=2, ge=0, le=10, description=text("settings.max_retries"))
    code_attempts: int = Field(default=3, ge=1, le=10, description=text("settings.code_attempts"))
    backoff_base: float = Field(default=0.6, ge=0, description=text("settings.backoff_base"))
    backoff_cap: float = Field(default=8.0, ge=0, description=text("settings.backoff_cap"))
    user_agent: str = Field(default="binaaz-python-sdk/{version}", description=text("settings.user_agent"))
    allow_insecure_http: bool = Field(default=False, description=text("settings.allow_insecure_http"))

    @field_validator("base_url", "photos_url", "login_url", "return_to")
    @classmethod
    def _address(cls, value: str, info: Any) -> str:
        parts = urlsplit(value.strip())
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError(text("error.base_url", field=info.field_name, url=value))
        return value.strip() if info.field_name == "return_to" else value.strip().rstrip("/")

    def check_transport(self) -> None:
        for name in SERVICES:
            address = getattr(self, name)
            parts = urlsplit(address)
            if parts.scheme == "https" or self.allow_insecure_http or parts.hostname in LOCAL_HOSTS:
                continue
            raise ConfigurationError(text("error.insecure", url=address))

    def path(self, endpoint: str) -> str:
        return endpoint if endpoint.startswith("/") else str(getattr(self.endpoints, endpoint))

    def url(self, service: str, endpoint: str, query: Optional[dict[str, Any]] = None) -> str:
        address = str(getattr(self, service)) + self.path(endpoint)
        given = {k: v for k, v in (query or {}).items() if v is not None and v != ""}
        return f"{address}?{urlencode(given)}" if given else address

    def resolved_user_agent(self) -> str:
        return self.user_agent.replace("{version}", __version__)


Settings.__doc__ = text("settings.description")


def load_settings(config_file: Optional[str] = None, **overrides: Any) -> Settings:
    given = {key: value for key, value in overrides.items() if value is not None}
    return Settings(load=True, config_file=config_file, **given)
