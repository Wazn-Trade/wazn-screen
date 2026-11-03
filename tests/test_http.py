import json

import httpx
import pytest

from wazn_screen.sources.http import DEFAULT_HEADERS, HttpClient, HttpError


def _ok_json(payload):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def test_get_json_returns_parsed_body():
    c = HttpClient(transport=_ok_json({"hello": "world"}))
    assert c.get_json("https://example/x") == {"hello": "world"}


def test_default_headers_include_ua_and_egx_origin():
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.headers))
        return httpx.Response(200, json={"ok": True})

    c = HttpClient(transport=httpx.MockTransport(handler))
    c.get_json("https://example/x")
    assert "chrome" in captured["user-agent"].lower()
    assert captured["x-egx-origin"].startswith("https://beta.egx.com.eg")
    # Sanity: the module exports these defaults.
    assert DEFAULT_HEADERS["x-egx-origin"] == "https://beta.egx.com.eg"


def test_validation_failure_raises():
    c = HttpClient(transport=_ok_json({"nope": True}))
    with pytest.raises(HttpError):
        c.get_json("https://example/x", validate=lambda d: "yes" in d)


def test_4xx_raises_immediately_no_retry():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, text="nope")

    c = HttpClient(transport=httpx.MockTransport(handler), max_retries=3)
    with pytest.raises(HttpError):
        c.get_json("https://example/x")
    assert calls["n"] == 1


def test_5xx_retried_then_fails():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, text="try again")

    c = HttpClient(transport=httpx.MockTransport(handler), max_retries=2, backoff=0.0)
    with pytest.raises(HttpError):
        c.get_json("https://example/x")
    assert calls["n"] == 3  # initial + 2 retries


def test_5xx_then_ok_succeeds():
    responses = iter(
        [httpx.Response(502, text="bad"), httpx.Response(200, json={"ok": True})]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    c = HttpClient(transport=httpx.MockTransport(handler), max_retries=2, backoff=0.0)
    assert c.get_json("https://example/x") == {"ok": True}


def test_non_json_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html/>", headers={"content-type": "text/html"})

    c = HttpClient(transport=httpx.MockTransport(handler))
    with pytest.raises(HttpError):
        c.get_json("https://example/x")


def test_context_manager_closes():
    c = HttpClient(transport=_ok_json({"ok": True}))
    with c:
        assert c.get_json("https://example/x") == {"ok": True}
