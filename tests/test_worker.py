"""受付Worker のテスト。先に別のターミナルで `cd worker && npx wrangler dev --port 8787` を起動しておく。"""
import json
import os
import urllib.error
import urllib.request

import pytest

BASE = os.getenv("WORKER_URL", "http://127.0.0.1:8787")
ORIGIN = "http://localhost:8550"
OK = {"name": "山田 太郎", "email": "taro@example.jp", "company": "", "category": "rebuild",
      "message": "フォームの作り直しを相談したいです", "consent": True}


def call(method, path="/api/contact", body=None, headers=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    h = {"Content-Type": "application/json", "Origin": ORIGIN, **(headers or {})}
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, dict(r.headers), json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        txt = e.read()
        return e.code, dict(e.headers), json.loads(txt) if txt else None


def ip(n):  # 連続送信の制限に引っかからないよう、テストごとに送信元を変える
    return {"CF-Connecting-IP": f"10.0.0.{n}"}


def test_accepts_valid():
    code, h, res = call("POST", body=OK, headers=ip(1))
    assert code == 201 and len(res["id"]) == 8
    assert h.get("Access-Control-Allow-Origin") == ORIGIN


def test_accepts_phone():
    code, _, _ = call("POST", body={**OK, "phone": "090-1234-5678"}, headers=ip(13))
    assert code == 201


@pytest.mark.parametrize("n,patch,field", [
    (2, {"email": "not-an-email"}, "email"),
    (3, {"name": "   "}, "name"),
    (4, {"consent": False}, "consent"),
    (5, {"category": "hack"}, "category"),
    (6, {"message": "x" * 2001}, "message"),
    (7, {"name": 123}, "name"),
    (11, {"phone": "090-1234-abcd"}, "phone"),
    (12, {"phone": "0" * 21}, "phone"),
])
def test_rejects_bad_input(n, patch, field):
    code, _, res = call("POST", body={**OK, **patch}, headers=ip(n))
    assert code == 422
    assert field in [d["loc"][-1] for d in res["detail"]]


def test_rejects_other_origin():
    code, h, _ = call("POST", body=OK, headers={**ip(8), "Origin": "https://evil.example"})
    assert code == 403 and "Access-Control-Allow-Origin" not in h


def test_preflight():
    code, h, _ = call("OPTIONS", headers={"Access-Control-Request-Method": "POST"})
    assert code == 204 and h.get("Access-Control-Allow-Origin") == ORIGIN


def test_body_too_large():
    code, _, _ = call("POST", raw=b"{" + b" " * 20000 + b"}", headers=ip(9))
    assert code == 413


def test_broken_json():
    code, _, _ = call("POST", raw=b"{broken", headers=ip(10))
    assert code == 422


def test_nothing_else_exposed():
    assert call("GET")[0] == 405
    assert call("GET", path="/")[0] == 404
    assert call("GET", path="/api/contacts")[0] == 404


def test_rate_limit():
    codes = [call("POST", body=OK, headers=ip(99))[0] for _ in range(7)]
    assert codes[:5] == [201] * 5 and 429 in codes[5:]
