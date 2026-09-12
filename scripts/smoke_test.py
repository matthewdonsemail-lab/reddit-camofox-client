"""Normalization parity with John's NewRedditPostPayload shape."""
import sys
sys.path.insert(0, "src")

from datetime import UTC, datetime
from reddit_camofox_client.domain_records.normalization import PostNormalizer

n = PostNormalizer()
rec = n.normalize(
    {"post_id": "abc123", "subreddit": "test", "title": "hi", "selftext": "body",
     "author": "u1", "score": 5, "num_comments": 2, "permalink": "/r/test/comments/abc123/hi/",
     "occurred_at": datetime(2026, 5, 27, 12, 0, tzinfo=UTC)},
    account_id="demo", source_action="posts.listen",
)
assert rec.external_id == "abc123", rec.external_id
assert rec.subreddit == "test"
assert rec.record_type == "reddit_post"
print("normalization OK:", rec.record_id)
