# AGENTS.md

Conventions for AI coding agents and human contributors working in
`reddit-camofox-client`. Stamped from Kennedy's
[facebook-camofox-client](https://github.com/PRACE1/facebook-camofox-client)
(remote `main`) and John's
[upwork-camofox-client](https://github.com/OfforJohn/upwork-camofox-client).

## What this is

A Camofox-native Reddit client for OpenMagpie, scoped solely to Reddit.
JSON action envelope -> account-scoped Camofox session -> normalized
records -> commit -> cursor -> `posts.new` (in-process emit + HTTP push).

## Layout

```text
src/reddit_camofox_client/
  api/               REGISTRY + dispatch() + FastAPI app (/api/*, /healthz)
  domain_accounts/   login, auth_guard (token_v2 first), challenges, totp
  domain_actions/    envelope, registry, runner, actions (runner wiring)
  domain_api/        legacy Kennedy server; canonical HTTP surface is api/app.py
  domain_camofox/    session, session_manager, selectors, navigation,
                     interactions, cookies (browser-export converter)
  domain_connectors/ RedditCamofoxConnector (kind=reddit_subreddit)
  domain_contracts/  RedditPostWebhook + webhooks.dispatch/post_new_event
  domain_cursors/    models, repository (records commit BEFORE cursor saves)
  domain_events/     models, emitter
  domain_posts/      listen, search, submit, reply, schemas
  domain_subreddits/ search, schemas
  domain_records/    models (record_type=reddit_post), normalization, repository
  domain_runtime/    shared models + protocols
scripts/             reddit_smoke_comment.py (dry-run default, --live posts)
docs/                reddit-action-parity.md, reddit-auth.md
tests/               registry, cookies (fake values only)
```

## The 5 actions

`posts.listen` (emits `posts.new`, dedupe `reddit:{sub}:{id}`),
`posts.search`, `posts.create`, `subreddits.search`, `comments.reply`.
Every action class carries an `ACTION_TYPE` classvar. New actions:
builder in `api/actions.py` REGISTRY + convenience route in `api/app.py`.

## Auth model (two doors, never mix)

- `REDDIT_API_KEY`: bearer for OUR api only. Unset = open (localhost OK).
- Reddit auth: per-request cookie jar. Session cookie is `token_v2`
  (JWT, `sub == "user"` = logged in); `reddit_session` is legacy
  fallback. Reads work anonymous; writes need login.
- Full contract: `docs/reddit-auth.md`.

## Local secrets (hard rules)

- Real cookie jars live ONLY in `.env.local` (`REDDIT_COOKIES_FILE`
  pointing at e.g. `state/cookies.json`) or a `CAMOFOX_STORAGE_STATE`
  file. Both are gitignored. NEVER paste cookie values into code,
  tests, docs, or commit messages. Tests use obviously-fake values.
- The server never persists cookies; per-request jars only.

## Smoke test (r/gtmengineering comment)

```bash
# .env.local: REDDIT_COOKIES_FILE=state/cookies.json
python scripts/reddit_smoke_comment.py            # dry run
python scripts/reddit_smoke_comment.py --live     # posts "<=5 words" for real
```

`--live` refuses anonymous jars and comments over 5 words.

## Checks before push

```bash
python -m pytest tests/ -q
python scripts/smoke_test.py
```

No `playwright` import outside `domain_camofox`. No em dashes in
comments/docs. Secret-scan (`reddit_session`, `token_v2` values,
`gho_`/`ghp_`) before every commit.
