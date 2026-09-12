"""Camofox runtime constants and supported Reddit surfaces."""

CAMOFOX_HUMANIZE = True
CAMOFOX_GEOIP = True

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
