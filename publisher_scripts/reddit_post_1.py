# post from account and using API keys and account credentials

import praw
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import need, make_leak_post, make_seeded_demo_script


# --- fill in your credentials ---
reddit = praw.Reddit(
    client_id=need("REDDIT_CLIENT_ID"),
    client_secret=need("REDDIT_CLIENT_SECRET"),
    username=need("REDDIT_USERNAME"),
    password=need("REDDIT_PASSWORD"),
    user_agent="python:myredditbot:v1.0 (by u/YOUR_USERNAME)"
)

# --- choose the subreddit ---
subreddit = reddit.subreddit("test")  # try in /r/test first!

post = make_seeded_demo_script()

post = (
    "trying to make ssh execution script, does this look okay?\n\n"
    + f"*{post['filename']}*\n\n"
    + "```bash\n"
    + post["content"]
    + "\n```"
)

# --- make a text post ---
post = subreddit.submit(
    title="info",
    selftext=post
)

print(f"""
====================================================
Reddit post created successfully.
RESULT_URL: {post.url}
====================================================
""")
