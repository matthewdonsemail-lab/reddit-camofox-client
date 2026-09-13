# Writing convention (rule)

Everything this client posts to Reddit — comments, replies, submissions —
follows the operator's voice. This is a hard rule, not a suggestion.
Check every outbound string against it before anything goes live.

## The voice

- **all lowercase.** no capital letters anywhere, including `i` and
  sentence starts. product names stay lowercase too (`twenty crm`,
  `webrtc`, `calendly`, `rest api`).
- **no commas.** restructure lists with `and`. use periods to break
  thoughts instead of subordinate clauses.
- **light natural typos, still coherent.** the occasional `teh`,
  `woudl`, `seperate`, missing apostrophe (`theres`, `whats`). never
  so many that a reader struggles. if you have to reread it twice,
  take typos out until it scans on the first pass.
- **short and plain.** comments default to 5 words or fewer unless the
  operator asks for more. posts stay under ~200 words.

## Examples

comment (5 words): `great stuff thanks for sharing`

post title: `building open source gtm tools on twenty crm. cold call dialer and offer funnel builder`

## Enforcement

- `scripts/reddit_smoke_comment.py` caps comments at 5 words and its
  default comment follows this voice.
- `scripts/reddit_smoke_post.py` takes title/body from the operator;
  re-read them against this file before `--live`.
- never "fix" the voice in review. correcting the case, re-adding
  commas, or spellchecking outbound copy is a bug, not a cleanup.
