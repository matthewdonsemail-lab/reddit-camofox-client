# Reddit action parity

Ports John's `reddit_subreddit` connector behavior onto Kennedy's Camofox-native
domain architecture.

## Architecture

```text
ActionEnvelope
  -> ActionRunner / ActionRegistry (domain_actions/actions.py)
  -> domain action (domain_posts/*, domain_subreddits/*)
  -> CamofoxSessionManager
  -> CamofoxSession
  -> CamofoxInteractions
  -> Reddit surface
  -> normalized result / event / cursor
```

No `playwright` import. Browser mechanics stay behind `domain_camofox`.

## Domain layout

```text
src/reddit_camofox_client/
├── api/actions.py              # compat shim -> domain_actions/actions.py
├── domain_accounts/
├── domain_actions/             # envelope, registry, runner, actions (5-action registry)
├── domain_api/                 # server, schemas, __main__
├── domain_camofox/
├── domain_connectors/          # RedditCamofoxConnector (kind=reddit_subreddit)
├── domain_contracts/           # RedditPostWebhook / PostsNewEvent (John parity)
├── domain_cursors/
├── domain_events/
├── domain_posts/               # listen, search, submit, reply, schemas
├── domain_subreddits/          # search, schemas
├── domain_records/
└── domain_runtime/
```

## Action names

- `posts.listen` -> emits `posts.new` webhook per record (dedupe `reddit:{sub}:{id}`)
- `posts.search`
- `posts.create`
- `subreddits.search`
- `comments.reply`

## Webhook contract (John parity)

`posts.new` payload fields match `NewRedditPostPayload`:
`external_id, kind=new_post, source=reddit_subreddit, occurred_at,
title, content, url, permalink, subreddit, author`.
