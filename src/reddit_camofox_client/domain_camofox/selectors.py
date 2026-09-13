"""Semantic Reddit selector candidates. Domain actions express intent, not driver details."""

LOGIN_USERNAME = ["input[name='username']", "input[autocomplete='username']"]
LOGIN_PASSWORD = ["input[name='password']", "input[type='password']"]
LOGIN_SUBMIT = ["button[type='submit']", "button:has-text('Log In')"]

POST_TITLE = ["shreddit-post", "div[data-testid='post-container']", "article"]
SEARCH_INPUT = ["input[name='q']", "input[placeholder*='Search']"]
SUBMIT_TITLE = ["textarea[name='title']", "input[name='title']"]
SUBMIT_BODY = ["shreddit-composer", "div[role='textbox']", "textarea[name='text']"]
SUBMIT_BUTTON = ["button:has-text('Post')", "button[type='submit']"]
COMMENT_BOX = ["div[contenteditable='true']", "textarea[placeholder*='comment' i]"]
REPLY_BUTTON = ["button:has-text('Reply')"]
