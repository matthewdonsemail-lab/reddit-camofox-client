"""Camofox runtime constants and supported Reddit surfaces."""

# NOTE (video-agent fault): humanize MUST be a float, never boolean True.
# boolean True hangs mouse.move on current Camofox builds
# ("humanize:maxTime is not a double"). Float = max seconds per cursor move.
CAMOFOX_HUMANIZE: float = 1.5
CAMOFOX_HUMANIZE_FALLBACK = False  # retry launch with humanize off on humanize errors
CAMOFOX_GEOIP = True

# Every Camoufox-native mouse.move is wrapped in this guard: a broken
# bezier-curve generator hangs for minutes instead of failing fast.
MOUSE_MOVE_TIMEOUT_SECONDS = 5.0

# Default scroll nudge: 65% of viewport height (video-agent convention).
SCROLL_VIEWPORT_FRACTION = 0.65

REDDIT_BASE_URL = "https://www.reddit.com"
REDDIT_LOGIN_URL = f"{REDDIT_BASE_URL}/login"
REDDIT_SEARCH_URL = f"{REDDIT_BASE_URL}/search"
REDDIT_SUBMIT_URL = f"{REDDIT_BASE_URL}/submit"

SURFACE_SUBREDDIT = "reddit_subreddit"
SURFACE_SEARCH = "reddit_search"
SURFACE_POST = "reddit_post"
SURFACE_SUBMIT = "reddit_submit"

SUPPORTED_SURFACES = {
    SURFACE_SUBREDDIT,
    SURFACE_SEARCH,
    SURFACE_POST,
    SURFACE_SUBMIT,
}
