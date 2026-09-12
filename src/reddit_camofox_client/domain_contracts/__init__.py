"""Domain contracts package."""
from reddit_camofox_client.domain_contracts.reddit import PostsNewEvent, RedditPostWebhook
from reddit_camofox_client.domain_contracts.webhooks import dispatch, post_new_event

__all__ = ["PostsNewEvent", "RedditPostWebhook", "dispatch", "post_new_event"]
