# reddit-camofox-client

Camofox-native Reddit client for OpenMagpie: poll subreddits, search posts,
submit posts, discover communities, and reply to threads through an
anti-detect Camofox browser session. Scoped solely to Reddit.

## Basis

Stamped from two reference repos, following their conventions exactly:

- Kennedy — [facebook-camofox-client](https://github.com/PRACE1/facebook-camofox-client)
  (`src/` layout, `api/actions.py` REGISTRY + `dispatch()`, `api/app.py`
  `/api/*` routes + `/healthz`, `ActionEnvelope`, per-action `ACTION_TYPE`,
  `commit`-before-cursor in listen, `posts.new` webhook push).
- John — [upwork-camofox-client](https://github.com/OfforJohn/upwork-camofox-client)
  (domain packages, thin FastAPI transport with generic `POST /actions`
  plus per-action convenience routes, browser ownership stays in
  `domain_camofox`).

Webhook payloads match John's OpenMagpie `reddit_subreddit` connector
(`NewRedditPostPayload`, `PAYLOAD_KIND="new_post"`), so `posts.new`
events hydrate directly into OpenMagpie FeedItems.

## Target Runtime

```text
JSON action envelope -> action runner -> account-scoped Camofox session
  -> normalized records -> commit -> cursor -> posts.new (in-process + HTTP push)
```

Cookies travel per request (no server-side session store). Bearer key
optional via `REDDIT_API_KEY`. Webhook fan-out via `POSTS_WEBHOOK_URL`
(fallback `REDDIT_WEBHOOK_URL`).

> Auth can be confusing here: `REDDIT_API_KEY` guards **our** API, it is
> not Reddit auth. Reddit auth is the per-request **cookie jar**
> (`token_v2` JWT). Full story: [`docs/reddit-auth.md`](docs/reddit-auth.md).

## The 5 actions

| action type | handler | input | output / event |
|---|---|---|---|
| `posts.listen` | `domain_posts.listen` | `{ subreddits: [...], limit: 25 }` | `new_posts` + `cursor_advanced`; emits `posts.new` per record |
| `posts.search` | `domain_posts.search` | `{ query, subreddit, sort }` | list of normalized posts |
| `posts.create` | `domain_posts.submit` | `{ subreddit, title, content }` | created-post receipt |
| `subreddits.search` | `domain_subreddits.search` | `{ query }` | matching communities |
| `comments.reply` | `domain_posts.reply` | `{ post_id, parent_id, text }` | reply confirmation |

Generic surface: `POST /api/actions/{action_type}` (+ `GET /api/actions`
index). Convenience routes: `POST /api/posts/listen`, `/api/posts/search`,
`/api/posts`, `/api/subreddits/search`, `/api/comments/reply`.

## Structure

```text
src/reddit_camofox_client/
├── api/                    # actions.py (REGISTRY + dispatch), app.py (FastAPI /api/*)
├── domain_accounts/        # login, auth_guard, challenges, totp, models
├── domain_actions/         # envelope, registry, runner, actions (runner wiring)
├── domain_api/             # legacy Kennedy server (schemas + /action); canonical is api/app.py
├── domain_camofox/         # session, session_manager, selectors, navigation, interactions
├── domain_connectors/      # RedditCamofoxConnector (kind=reddit_subreddit)
├── domain_contracts/       # RedditPostWebhook + webhooks.dispatch/post_new_event
├── domain_cursors/         # models, repository (records commit before cursor advances)
├── domain_events/          # models, emitter
├── domain_posts/           # listen, search, submit, reply, schemas
├── domain_subreddits/      # search, schemas
├── domain_records/         # models (record_type=reddit_post), normalization, repository
└── domain_runtime/         # shared models + protocols
```

## Run

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
python scripts/smoke_test.py
uvicorn reddit_camofox_client.api.app:app --port 8001
```

Live smoke test posts a <=5-word comment to r/gtmengineering
(dry run by default); agent conventions live in
[`AGENTS.md`](AGENTS.md):

```bash
# .env.local: REDDIT_COOKIES_FILE=state/cookies.json
python scripts/reddit_smoke_comment.py            # dry run
python scripts/reddit_smoke_comment.py --live     # posts for real
```
