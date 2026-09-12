# Reddit auth: what this client expects

Two different doors. Do not mix them up.

## Door 1: our API (`REDDIT_API_KEY`, optional)

`REDDIT_API_KEY` is a bearer password for **our own FastAPI service**
(`api/app.py`), copied from Kennedy's `FB_API_KEY` pattern. It keeps
random callers off your scraper. It has nothing to do with Reddit.

- Unset = open API (fine on localhost).
- Set = every `/api/*` call needs `Authorization: Bearer <key>`.

## Door 2: Reddit itself (cookie jar, per request)

Reddit is scraped as a **browser client** (Camofox), not via an API key.
Every action accepts a cookie jar that is loaded into a fresh browser
context, used once, then discarded. Nothing persists server-side.

### Exact cookie shape

One JSON list, Playwright cookie records:

```json
[
  {
    "name": "token_v2",
    "value": "<jwt>",
    "domain": ".reddit.com",
    "path": "/",
    "expires": 1780000000.0,
    "httpOnly": true,
    "secure": true,
    "sameSite": "None"
  }
]
```

| field | required | notes |
|---|---|---|
| `name` | yes | see cookie table below |
| `value` | yes | the cookie value verbatim |
| `domain` | yes | `.reddit.com` (leading dot) |
| `path` | no | defaults to `/` |
| `expires` | no | float unix time; `-1` = session cookie |
| `httpOnly` | no | `true` for auth cookies |
| `secure` | no | `true` |
| `sameSite` | no | `"None"`, `"Lax"`, or `"Strict"` |

Pass it as `cookies` on any `ActionBody`, or as `_cookies` inside a raw
envelope `input`. The server echoes the refreshed jar back on every
response, so forward the latest jar on the next call.

### Which cookies matter

A logged-out visit to reddit.com sets anonymous/machine cookies
(`loid`, `loidcreated`, `edgebucket`, `session_tracker`, `pc`, `csv`).
Only these authenticate you:

| cookie | role | how to check |
|---|---|---|
| `token_v2` | **the session** (JWT) | decode payload: `sub == "user"` = logged in (plus `lid: t2_...`); `sub == "loid"` = anonymous |
| `reddit_session` | legacy session | present only on some accounts; accepted as fallback |

Everything else (`loid`, `edgebucket`, `session_tracker`, `USER`, …)
is tracking/preferences, not auth. Forwarding the whole jar is fine and
recommended; the guard reads `token_v2` first.

### What works without login

| action | anonymous | logged in (`sub == "user"`) |
|---|---|---|
| `posts.listen` | yes | yes |
| `posts.search` | yes | yes |
| `subreddits.search` | yes | yes |
| `posts.create` | no | yes |
| `comments.reply` | no | yes |

### How to get the jar (with the Camoufox you already have)

1. `POST /api/actions/posts.listen` with no cookies once, or run the
   login flow: drive `https://www.reddit.com/login` in a headed Camofox
   window and sign in as the account.
2. Export the context cookies (`context.cookies()` / storage state) —
   that JSON list **is** the jar.
3. Send it as `cookies` on subsequent calls. Rotate by re-exporting;
   `token_v2` JWTs expire.

Alternative: set `CAMOFOX_STORAGE_STATE` to a saved Playwright
`storage_state` file and omit `cookies`; the server loads it as the
default jar. Per-request cookies always override it.

### Security

- Never commit a jar, a storage-state file, or a `.env` containing
  `REDDIT_API_KEY`. All three are gitignored.
- The server never writes cookies to disk; they live in the ephemeral
  browser context only.
