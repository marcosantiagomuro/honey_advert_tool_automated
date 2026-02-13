# post from account and using API keys
import os
import sys
import tweepy
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# import utils needs to be after sys.path as need to go up one level/directory
from utils import need, make_leak_post, make_tweet_bash_command


client = tweepy.Client(
    consumer_key=need("X_API_KEY"),
    consumer_secret=need("X_API_SECRET"),
    access_token=need("X_ACCESS_TOKEN"),
    access_token_secret=need("X_ACCESS_TOKEN_SECRET"),
)

# 1 entry only otherwise twitter blocks the post via its own "safe posts" validators
#post = make_leak_post(n_entries=1)
post = make_tweet_bash_command()
custom_outro = "\n #cybersec"
# POST_text = post["text"] + custom_outro
POST_text = post

try:
    # Force user auth so the request is made on behalf of the user
    resp = client.create_tweet(text=POST_text, user_auth=True)
    tweet_id = resp.data["id"]
    me = client.get_me(user_auth=True)
    username = me.data.username
    tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"
    print(f"""
====================================================
Twitter post created successfully.
RESULT_URL: {tweet_url}
====================================================
""")

except tweepy.Forbidden as e:
    # Show the real error body from X so you can see the exact reason/code
    try:
        print("X API error body:", e.response.text)
    except Exception:
        pass
    raise
