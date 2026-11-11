from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Generator, Mapping, Optional, TypeVar, Union
from urllib.parse import urlsplit

import httpx

from .config import Settings, load_settings
from .errors import (
    AuthenticationError,
    BadRequestError,
    BlockedError,
    GraphQLError,
    InvalidRequestError,
    NotSentError,
    OutcomeUnknownError,
    RateLimitError,
    ServerError,
    TransportError,
    for_status,
)
from .messages import text

T = TypeVar("T")

NOT_SENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout, httpx.UnsupportedProtocol)
RETRY_STATUSES = frozenset({500, 502, 503, 504})
CLOUDFLARE_COOKIES = frozenset({"cf_clearance", "__cf_bm", "__cflb", "_cfuvid", "cf_chl_rc_m"})
AUTH_CODES = frozenset({"unauthorized", "unauthenticated", "forbidden"})
AUTH_HINTS = ("unauthorized", "not authorized", "unauthenticated", "sign in", "log in", "login required",
              "daxil olun", "giriş")
CODE_ERRORS = frozenset({"code_requests", "failed_attempts", "phone", "code"})

CookieInput = Union[str, Mapping[str, Any], list, None]


@dataclass
class Op:
    method: str
    service: str
    endpoint: str
    parse: Callable[[Any], Any] = lambda body: body
    query: Optional[dict[str, Any]] = None
    body: Optional[dict[str, Any]] = None
    files: Optional[list[Any]] = None
    safe: bool = False
    flaky: bool = False
    session: bool = True
    action: str = "The request"


@dataclass(frozen=True)
class Pause:
    seconds: float


@dataclass(frozen=True)
class CodeReply:
    status: int
    body: Mapping[str, Any]
    attempts: int


Flow = Generator[Any, Any, T]


@dataclass
class Outcome:
    value: Any = None
    error: Optional[Exception] = None
    wait: Optional[float] = None


def _number(value: Optional[str]) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def cloudflare_blocked(response: httpx.Response) -> bool:
    if response.headers.get("cf-mitigated", "").lower() == "challenge":
        return True
    if response.status_code in (403, 503) and "cloudflare" in response.headers.get("server", "").lower():
        return "text/html" in response.headers.get("content-type", "")
    return False


def parse_cookie(raw: CookieInput) -> dict[str, str]:
    pairs: list[tuple[str, str]] = []
    if isinstance(raw, str):
        value = raw.strip()
        if value[:1] in "[{":
            try:
                return parse_cookie(json.loads(value))
            except json.JSONDecodeError:
                pass
        if value.lower().startswith("cookie:"):
            value = value[7:].strip()
        for part in value.replace("\n", ";").split(";"):
            name, sep, content = part.strip().partition("=")
            if sep and name.strip():
                pairs.append((name.strip(), content.strip()))
    elif isinstance(raw, Mapping):
        pairs = [(str(k), str(v)) for k, v in raw.items()]
    elif isinstance(raw, list):
        pairs = [(str(c["name"]), str(c.get("value", ""))) for c in raw if isinstance(c, Mapping) and "name" in c]
    return {k: v for k, v in pairs if v and k.lower() not in CLOUDFLARE_COOKIES}


def _graphql_detail(errors: list[Any]) -> str:
    parts = []
    for error in errors:
        if isinstance(error, Mapping):
            where = ".".join(str(p) for p in error.get("path") or [])
            parts.append(f"{where}: {error.get('message')}" if where else str(error.get("message")))
    return "; ".join(parts) or "unknown error"


class Engine:
    def __init__(
        self,
        cookie: CookieInput = None,
        *,
        settings: Optional[Settings] = None,
        config_file: Optional[str] = None,
        **overrides: Any,
    ) -> None:
        if settings is None:
            settings = load_settings(config_file, **overrides)
        elif overrides:
            current = settings.model_dump()
            current["cookie"] = settings.cookie.get_secret_value()
            settings = load_settings(None, **{**current, **{k: v for k, v in overrides.items() if v is not None}})
        self.settings = settings
        settings.check_transport()
        self._jar: dict[str, str] = parse_cookie(settings.cookie.get_secret_value())
        if cookie is not None:
            self.set_cookie(cookie)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(base_url={self.settings.base_url!r}, signed_in={bool(self._jar)})"

    @property
    def cookie(self) -> str:
        return "; ".join(f"{k}={v}" for k, v in self._jar.items())

    def set_cookie(self, cookie: CookieInput) -> None:
        jar = parse_cookie(cookie)
        if cookie not in (None, "") and not jar:
            raise InvalidRequestError(text("value.cookie"))
        self._jar = jar

    def clear_session(self) -> None:
        self._jar = {}

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(self.settings.timeout, connect=self.settings.connect_timeout)

    def _url(self, op: Op) -> str:
        return self.settings.url(op.service, op.endpoint, op.query)

    def _headers(self, op: Op) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": self.settings.resolved_user_agent()}
        if op.service == "login_url":
            headers["Accept-Language"] = self.settings.language
            return headers
        origin = self.settings.base_url
        headers["Origin"] = origin
        headers["Referer"] = origin + ("/items/new" if op.service == "photos_url" else "/")
        if op.session and self._jar:
            headers["Cookie"] = self.cookie
        return headers

    def _request_args(self, op: Op) -> dict[str, Any]:
        args: dict[str, Any] = {"headers": self._headers(op)}
        if op.files is not None:
            args["files"] = op.files
        elif op.body is not None:
            args["json"] = op.body
        return args

    def _backoff(self, attempt: int) -> float:
        base = self.settings.backoff_base
        return min(self.settings.backoff_cap, base * (2**attempt)) + random.uniform(0, base / 2)

    def _absorb(self, op: Op, response: httpx.Response) -> None:
        if op.service == "login_url":
            return
        for raw in response.headers.get_list("set-cookie"):
            first, _, rest = raw.partition(";")
            name, sep, value = first.strip().partition("=")
            name = name.strip()
            if not sep or not name or name.lower() in CLOUDFLARE_COOKIES:
                continue
            expired = "01 jan 1970" in rest.lower() or "max-age=0" in rest.lower().replace(" ", "")
            if value.strip() and not expired:
                self._jar[name] = value.strip()
            else:
                self._jar.pop(name, None)

    def _on_exception(self, op: Op, exc: Exception, attempt: int, url: str) -> Outcome:
        host = urlsplit(url).hostname or url
        path = urlsplit(url).path
        can_retry = attempt < self.settings.max_retries
        if isinstance(exc, NOT_SENT):
            if can_retry:
                return Outcome(wait=self._backoff(attempt))
            return Outcome(error=NotSentError(text("error.connect", host=host, error=exc), path=path))
        if op.safe:
            if can_retry:
                return Outcome(wait=self._backoff(attempt))
            return Outcome(error=TransportError(text("error.timeout", host=host, error=exc), path=path))
        return Outcome(error=OutcomeUnknownError(text("error.unknown_outcome", action=op.action,
                                                      reason=type(exc).__name__), path=path))

    def _on_code_reply(self, op: Op, response: httpx.Response, attempt: int, path: str) -> Outcome:
        try:
            data = response.json()
        except ValueError:
            data = None
        if isinstance(data, Mapping):
            if response.status_code < 400 or data.get("error") in CODE_ERRORS:
                return Outcome(value=op.parse(CodeReply(response.status_code, data, attempt + 1)))
        if attempt + 1 < self.settings.code_attempts:
            return Outcome(wait=self._backoff(attempt))
        return Outcome(error=ServerError(text("error.code_service", attempts=attempt + 1,
                                              last=f"HTTP {response.status_code}"),
                                         status_code=response.status_code, body=data, path=path))

    def _on_response(self, op: Op, response: httpx.Response, attempt: int, url: str) -> Outcome:
        host = urlsplit(url).hostname or url
        path = urlsplit(url).path
        status = response.status_code
        can_retry = attempt < self.settings.max_retries
        self._absorb(op, response)
        if cloudflare_blocked(response):
            return Outcome(error=BlockedError(text("error.blocked", host=host), status_code=status, path=path))
        if status == 429:
            hint = _number(response.headers.get("retry-after"))
            if can_retry:
                wait = min(self.settings.backoff_cap, hint) if hint is not None else self._backoff(attempt)
                return Outcome(wait=wait)
            return Outcome(error=RateLimitError(text("error.status", host=host, status=status), status_code=status,
                                                path=path, retry_after=hint))
        if op.flaky:
            return self._on_code_reply(op, response, attempt, path)
        if status in RETRY_STATUSES:
            if op.safe and can_retry:
                return Outcome(wait=self._backoff(attempt))
            if not op.safe:
                return Outcome(error=OutcomeUnknownError(text("error.unknown_outcome", action=op.action,
                                                              reason=f"HTTP {status}"), status_code=status, path=path))
        if status in (401, 419):
            return Outcome(error=AuthenticationError(text("error.session"), status_code=status, path=path))
        if status == 413:
            return Outcome(error=BadRequestError(text("error.photo_size"), status_code=status, path=path))
        try:
            body = response.json()
        except ValueError:
            snippet = response.text[:200]
            if status < 400 and not op.safe:
                return Outcome(error=OutcomeUnknownError(text("error.body", host=host, body=snippet),
                                                         status_code=status, path=path))
            kind = for_status(status) if status >= 400 else ServerError
            return Outcome(error=kind(text("error.body", host=host, body=snippet), status_code=status,
                                      body=snippet, path=path))
        if op.service == "base_url":
            return self._graphql(op, body, status, path, host)
        if status >= 400:
            return Outcome(error=for_status(status)(text("error.status", host=host, status=status),
                                                    status_code=status, body=body, path=path))
        return Outcome(value=op.parse(body))

    def _graphql(self, op: Op, body: Any, status: int, path: str, host: str) -> Outcome:
        if not isinstance(body, Mapping):
            return Outcome(error=ServerError(text("error.body", host=host, body=str(body)[:200]),
                                             status_code=status, body=body, path=path))
        errors = [e for e in body.get("errors") or [] if isinstance(e, Mapping)]
        if errors:
            joined = " ".join(str(e.get("message", "")) for e in errors).lower()
            codes = {str(_ext(e).get("code", "")).lower() for e in errors}
            if codes & AUTH_CODES or any(hint in joined for hint in AUTH_HINTS):
                return Outcome(error=AuthenticationError(text("error.session"), status_code=status, body=body,
                                                         path=path))
            return Outcome(error=GraphQLError(text("error.graphql", detail=_graphql_detail(errors)),
                                              errors=errors, status_code=status, body=body, path=path))
        if status >= 400:
            return Outcome(error=for_status(status)(text("error.status", host=host, status=status),
                                                    status_code=status, body=body, path=path))
        data = body.get("data")
        return Outcome(value=op.parse(data if isinstance(data, Mapping) else {}))


def _ext(error: Mapping[str, Any]) -> Mapping[str, Any]:
    value = error.get("extensions")
    return value if isinstance(value, Mapping) else {}


class SyncEngine(Engine):
    def __init__(self, *args: Any, http_client: Optional[httpx.Client] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(timeout=self._timeout())

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self: T) -> T:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)

    def _run(self, op: Op) -> Any:
        url = self._url(op)
        attempt = 0
        while True:
            try:
                response = self._http.request(op.method, url, **self._request_args(op))
            except httpx.HTTPError as exc:
                outcome = self._on_exception(op, exc, attempt, url)
            else:
                self._http.cookies.clear()
                outcome = self._on_response(op, response, attempt, url)
            if outcome.wait is not None:
                self._sleep(outcome.wait)
                attempt += 1
                continue
            if outcome.error is not None:
                raise outcome.error
            return outcome.value

    def _flow(self, flow: Flow[T]) -> T:
        reply: Any = None
        error: Optional[Exception] = None
        while True:
            try:
                step = flow.throw(error) if error is not None else flow.send(reply)
            except StopIteration as done:
                result: T = done.value
                return result
            error, reply = None, None
            if isinstance(step, Pause):
                self._sleep(step.seconds)
                continue
            try:
                reply = self._run(step)
            except Exception as exc:
                error = exc


class AsyncEngine(Engine):
    def __init__(self, *args: Any, http_client: Optional[httpx.AsyncClient] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=self._timeout())

    async def close(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self: T) -> T:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _sleep(self, seconds: float) -> None:
        if seconds > 0:
            await asyncio.sleep(seconds)

    async def _run(self, op: Op) -> Any:
        url = self._url(op)
        attempt = 0
        while True:
            try:
                response = await self._http.request(op.method, url, **self._request_args(op))
            except httpx.HTTPError as exc:
                outcome = self._on_exception(op, exc, attempt, url)
            else:
                self._http.cookies.clear()
                outcome = self._on_response(op, response, attempt, url)
            if outcome.wait is not None:
                await self._sleep(outcome.wait)
                attempt += 1
                continue
            if outcome.error is not None:
                raise outcome.error
            return outcome.value

    async def _flow(self, flow: Flow[T]) -> T:
        reply: Any = None
        error: Optional[Exception] = None
        while True:
            try:
                step = flow.throw(error) if error is not None else flow.send(reply)
            except StopIteration as done:
                result: T = done.value
                return result
            error, reply = None, None
            if isinstance(step, Pause):
                await self._sleep(step.seconds)
                continue
            try:
                reply = await self._run(step)
            except Exception as exc:
                error = exc
