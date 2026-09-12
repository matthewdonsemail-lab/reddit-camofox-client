"""Cookie converter tests (fake values only; never real credentials)."""
from reddit_camofox_client.domain_camofox.cookies import from_browser_export, is_logged_in_jar

EXPORT = [
    {
        "domain": ".reddit.com",
        "expirationDate": 1789343131.0,
        "hostOnly": False,
        "httpOnly": True,
        "name": "token_v2",
        "path": "/",
        "sameSite": None,
        "secure": True,
        "session": False,
        "storeId": None,
        "value": "x.eyJzdWIiOiJ1c2VyIn0.y",
    },
    {
        "domain": ".reddit.com",
        "hostOnly": False,
        "httpOnly": False,
        "name": "session_tracker",
        "path": "/",
        "sameSite": None,
        "secure": True,
        "session": True,
        "storeId": None,
        "value": "abc",
    },
    {
        "domain": ".reddit.com",
        "expirationDate": 1804169877.0,
        "hostOnly": False,
        "httpOnly": False,
        "name": "csv",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": True,
        "session": False,
        "storeId": None,
        "value": "2",
    },
]


def test_from_browser_export_shape():
    out = from_browser_export(EXPORT)
    assert len(out) == 3
    token = out[0]
    assert token["name"] == "token_v2"
    assert token["expires"] == 1789343131.0
    assert "sameSite" not in token  # null -> omitted
    assert "hostOnly" not in token and "storeId" not in token
    assert out[1]["expires"] == -1  # session cookie
    assert out[2]["sameSite"] == "None"  # no_restriction


def test_is_logged_in_jar():
    import base64
    import json

    pay = base64.urlsafe_b64encode(json.dumps({"sub": "user"}).encode()).decode().rstrip("=")
    assert is_logged_in_jar([{"name": "token_v2", "value": f"x.{pay}.y"}]) is True
    pay_loid = base64.urlsafe_b64encode(json.dumps({"sub": "loid"}).encode()).decode().rstrip("=")
    assert is_logged_in_jar([{"name": "token_v2", "value": f"x.{pay_loid}.y"}]) is False
    assert is_logged_in_jar([{"name": "reddit_session", "value": "zzz"}]) is True
    assert is_logged_in_jar([{"name": "loid", "value": "zzz"}]) is False
